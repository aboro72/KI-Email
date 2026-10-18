"""Zugangskontrolle für Personalverträge und -dokumente."""
from sqlalchemy import select

from app.models import Contract


def can_read_personnel(user) -> bool:
    """Prüft, ob ein Benutzer Personalverträge/-dokumente lesen darf."""
    permissions = {permission.name for permission in user.role.permissions}
    return "HRM_DOCUMENTS_VIEW" in permissions or "HRM_DOCUMENTS_MANAGE" in permissions


def visible_contracts(user):
    """Gibt eine Query zurück, die nur für den Benutzer sichtbare Verträge enthält."""
    statement = select(Contract)
    if not can_read_personnel(user):
        statement = statement.where(Contract.contract_type != "personal")
    return statement
