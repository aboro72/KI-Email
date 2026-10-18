"""HRM (Human Resource Management) Modul - Personalverwaltung."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.hrm_db import hrm_db as get_db
from app.models import Employee, LeaveRequest, OnboardingTask
from app.security import require_permission, require_user
from app.personnel_access import can_read_personnel

router = APIRouter(prefix="/hrm", tags=["Personalverwaltung"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def visible_employees(user):
    """Gibt eine Query zurück, die nur für den Benutzer sichtbare Mitarbeiter enthält."""
    statement = select(Employee)
    if not can_read_personnel(user):
        # Nur eigene Daten sichtbar
        statement = statement.where(Employee.user_id == user.id)
    return statement


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def hrm_overview(request: Request, db: Session = Depends(get_db)):
    """Personalübersicht mit Mitarbeitern, Urlaubsanträgen und Onboarding-Aufgaben."""
    if not get_settings().hrm_enabled:
        raise HTTPException(404, "Die Personalverwaltung ist deaktiviert.")

    user = require_user(request, db)
    require_permission(user, "HRM_VIEW")

    # Mitarbeiter abrufen
    employees = db.scalars(visible_employees(user).order_by(Employee.name)).all()

    # Offene Urlaubsanträge
    leave_requests = []
    if can_read_personnel(user):
        leave_requests = db.scalars(
            select(LeaveRequest)
            .where(LeaveRequest.status == "pending")
            .order_by(LeaveRequest.start_date)
        ).all()

    # Offene Onboarding-Aufgaben
    onboarding_tasks = []
    if can_read_personnel(user):
        onboarding_tasks = db.scalars(
            select(OnboardingTask)
            .where(OnboardingTask.completed_at.is_(None))
            .order_by(OnboardingTask.due_date)
        ).all()

    return templates.TemplateResponse(
        request=request,
        name="hrm.html",
        context={
            "user": user,
            "employees": employees,
            "leave_requests": leave_requests,
            "onboarding_tasks": onboarding_tasks,
            "can_manage": can_read_personnel(user),
        }
    )
