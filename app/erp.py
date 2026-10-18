"""ERP (Enterprise Resource Planning) Modul - Geschäftsprozesse."""
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import CommercialDocument, ErpCustomer, ErpItem, ErpPayment
from app.security import require_permission, require_user

router = APIRouter(prefix="/erp", tags=["ERP"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def erp_overview(request: Request, db: Session = Depends(get_db)):
    """ERP-Übersicht mit Rechnungen, Angeboten, Kunden und Artikeln."""
    if not get_settings().erp_enabled:
        raise HTTPException(404, "Das ERP-Modul ist deaktiviert.")

    user = require_user(request, db)
    require_permission(user, "ERP_VIEW")

    # Statistiken
    total_customers = db.scalar(select(func.count(ErpCustomer.id)))
    total_items = db.scalar(select(func.count(ErpItem.id)).where(ErpItem.active))

    # Offene Rechnungen
    open_invoices = db.scalars(
        select(CommercialDocument)
        .where(CommercialDocument.kind == "invoice")
        .where(CommercialDocument.status == "issued")
        .order_by(CommercialDocument.due_date)
        .limit(10)
    ).all()

    # Überfällige Rechnungen
    today = date.today().isoformat()
    overdue_invoices = db.scalars(
        select(CommercialDocument)
        .where(CommercialDocument.kind == "invoice")
        .where(CommercialDocument.status == "issued")
        .where(CommercialDocument.due_date < today)
        .where(CommercialDocument.due_date != "")
        .order_by(CommercialDocument.due_date)
    ).all()

    # Aktuelle Angebote
    recent_quotes = db.scalars(
        select(CommercialDocument)
        .where(CommercialDocument.kind == "quote")
        .where(CommercialDocument.status != "cancelled")
        .order_by(CommercialDocument.created_at.desc())
        .limit(10)
    ).all()

    # Entwürfe
    drafts = db.scalars(
        select(CommercialDocument)
        .where(CommercialDocument.status == "draft")
        .order_by(CommercialDocument.created_at.desc())
        .limit(10)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="erp.html",
        context={
            "user": user,
            "total_customers": total_customers or 0,
            "total_items": total_items or 0,
            "open_invoices": open_invoices,
            "overdue_invoices": overdue_invoices,
            "recent_quotes": recent_quotes,
            "drafts": drafts,
        }
    )
