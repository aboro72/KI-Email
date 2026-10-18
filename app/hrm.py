"""HRM (Human Resource Management) Modul - Personalverwaltung."""
from fastapi import APIRouter
from sqlalchemy import select

router = APIRouter(prefix="/hrm", tags=["Personalverwaltung"])


def visible_employees(user):
    """Gibt eine Query zurück, die nur für den Benutzer sichtbare Mitarbeiter enthält."""
    from app.models import Employee
    from app.personnel_access import can_read_personnel

    statement = select(Employee)
    if not can_read_personnel(user):
        # Nur eigene Daten sichtbar
        statement = statement.where(Employee.user_id == user.id)
    return statement
