"""ERP (Enterprise Resource Planning) Modul - Geschäftsprozesse."""
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AuditLog, CommercialDocument, ErpCustomer, ErpItem, ErpPayment, PayPalConfig, PayPalTransaction
from app.security import decrypt_secret, encrypt_secret, require_permission, require_user

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


@router.get("/items", response_class=HTMLResponse)
def erp_items(request: Request, db: Session = Depends(get_db)):
    """Artikelverwaltung - Produkte und Dienstleistungen."""
    if not get_settings().erp_enabled:
        raise HTTPException(404, "Das ERP-Modul ist deaktiviert.")

    user = require_user(request, db)
    require_permission(user, "ERP_VIEW")

    items = db.scalars(select(ErpItem).order_by(ErpItem.active.desc(), ErpItem.name)).all()

    return templates.TemplateResponse(
        request=request,
        name="erp_items.html",
        context={
            "user": user,
            "items": items,
            "message": request.query_params.get("message"),
        }
    )


@router.post("/items")
def create_erp_item(
    request: Request,
    sku: str = Form(...),
    name: str = Form(...),
    unit: str = Form("Stück"),
    price_euros: float = Form(0.0),
    tax_percent: float = Form(19.0),
    db: Session = Depends(get_db),
):
    """Neuen Artikel anlegen."""
    user = require_user(request, db)
    require_permission(user, "ERP_MANAGE")

    # Prüfe ob SKU bereits existiert
    existing = db.scalar(select(ErpItem).where(ErpItem.sku == sku.strip()))
    if existing:
        return RedirectResponse(f"/erp/items?message={quote('SKU bereits vergeben')}", status_code=303)

    item = ErpItem(
        sku=sku.strip(),
        name=name.strip(),
        unit=unit.strip(),
        price_cents=int(price_euros * 100),
        tax_basis_points=int(tax_percent * 100),
        active=True,
    )
    db.add(item)
    db.add(AuditLog(action="ERP_ITEM_CREATED", actor_user_id=user.id, details=f'{{"sku": "{item.sku}", "name": "{item.name}"}}'))
    db.commit()

    return RedirectResponse(f"/erp/items?message={quote(f'Artikel {item.name} wurde angelegt')}", status_code=303)


@router.post("/items/{item_id}")
def update_erp_item(
    item_id: int,
    request: Request,
    sku: str = Form(...),
    name: str = Form(...),
    unit: str = Form("Stück"),
    price_euros: float = Form(0.0),
    tax_percent: float = Form(19.0),
    db: Session = Depends(get_db),
):
    """Artikel bearbeiten."""
    user = require_user(request, db)
    require_permission(user, "ERP_MANAGE")

    item = db.get(ErpItem, item_id)
    if not item:
        return RedirectResponse("/erp/items?message=Artikel+nicht+gefunden", status_code=303)

    # Prüfe ob neue SKU bereits von anderem Artikel verwendet wird
    if sku.strip() != item.sku:
        existing = db.scalar(select(ErpItem).where(ErpItem.sku == sku.strip()))
        if existing:
            return RedirectResponse(f"/erp/items?message={quote('SKU bereits vergeben')}", status_code=303)

    item.sku = sku.strip()
    item.name = name.strip()
    item.unit = unit.strip()
    item.price_cents = int(price_euros * 100)
    item.tax_basis_points = int(tax_percent * 100)

    db.add(AuditLog(action="ERP_ITEM_UPDATED", actor_user_id=user.id, details=f'{{"sku": "{item.sku}", "name": "{item.name}"}}'))
    db.commit()

    return RedirectResponse(f"/erp/items?message={quote(f'Artikel {item.name} wurde aktualisiert')}", status_code=303)


@router.post("/items/{item_id}/toggle")
def toggle_erp_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    """Artikel aktivieren/deaktivieren."""
    user = require_user(request, db)
    require_permission(user, "ERP_MANAGE")

    item = db.get(ErpItem, item_id)
    if not item:
        return RedirectResponse("/erp/items?message=Artikel+nicht+gefunden", status_code=303)

    item.active = not item.active
    status = "aktiviert" if item.active else "deaktiviert"

    db.add(AuditLog(action="ERP_ITEM_TOGGLED", actor_user_id=user.id, details=f'{{"sku": "{item.sku}", "active": {str(item.active).lower()}}}'))
    db.commit()

    return RedirectResponse(f"/erp/items?message={quote(f'Artikel {item.name} wurde {status}')}", status_code=303)


@router.get("/paypal", response_class=HTMLResponse)
def paypal_overview(request: Request, db: Session = Depends(get_db)):
    """PayPal-Transaktionsübersicht und Konfiguration."""
    if not get_settings().erp_enabled:
        raise HTTPException(404, "Das ERP-Modul ist deaktiviert.")

    user = require_user(request, db)
    require_permission(user, "ERP_VIEW")

    config = db.scalar(select(PayPalConfig).limit(1))
    if not config:
        config = PayPalConfig()
        db.add(config)
        db.commit()

    transactions = db.scalars(
        select(PayPalTransaction)
        .order_by(PayPalTransaction.transaction_date.desc())
        .limit(50)
    ).all()

    # Statistiken
    total_received = db.scalar(
        select(func.sum(PayPalTransaction.net_amount_cents))
        .where(PayPalTransaction.net_amount_cents > 0)
    ) or 0

    total_sent = db.scalar(
        select(func.sum(PayPalTransaction.net_amount_cents))
        .where(PayPalTransaction.net_amount_cents < 0)
    ) or 0

    unprocessed_count = db.scalar(
        select(func.count(PayPalTransaction.id))
        .where(PayPalTransaction.processed == False)
    ) or 0

    return templates.TemplateResponse(
        request=request,
        name="erp_paypal.html",
        context={
            "user": user,
            "config": config,
            "transactions": transactions,
            "total_received_euros": abs(total_received) / 100,
            "total_sent_euros": abs(total_sent) / 100,
            "balance_euros": (total_received + total_sent) / 100,
            "unprocessed_count": unprocessed_count,
            "message": request.query_params.get("message"),
        }
    )


@router.post("/paypal/config")
def update_paypal_config(
    request: Request,
    environment: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(""),
    webhook_id: str = Form(""),
    enabled: bool = Form(False),
    db: Session = Depends(get_db),
):
    """PayPal-Konfiguration aktualisieren."""
    user = require_user(request, db)
    require_permission(user, "ERP_MANAGE")

    config = db.scalar(select(PayPalConfig).limit(1))
    if not config:
        config = PayPalConfig()
        db.add(config)

    config.environment = environment
    config.client_id = client_id.strip()

    if client_secret:
        config.client_secret_encrypted = encrypt_secret(client_secret)

    config.webhook_id = webhook_id.strip()
    config.enabled = enabled

    db.add(AuditLog(action="PAYPAL_CONFIG_UPDATED", actor_user_id=user.id, details=f'{{"environment": "{environment}", "enabled": {str(enabled).lower()}}}'))
    db.commit()

    return RedirectResponse(f"/erp/paypal?message={quote('PayPal-Konfiguration wurde aktualisiert')}", status_code=303)


@router.post("/paypal/sync")
def sync_paypal_transactions(request: Request, db: Session = Depends(get_db)):
    """Transaktionen von PayPal synchronisieren."""
    user = require_user(request, db)
    require_permission(user, "ERP_MANAGE")

    config = db.scalar(select(PayPalConfig).limit(1))
    if not config or not config.enabled:
        return RedirectResponse("/erp/paypal?message=PayPal+nicht+konfiguriert", status_code=303)

    try:
        from app.paypal_integration import fetch_transactions
        count = fetch_transactions(config, db)
        return RedirectResponse(f"/erp/paypal?message={quote(f'{count} Transaktionen synchronisiert')}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/erp/paypal?message={quote(f'Fehler: {str(e)}')}", status_code=303)
