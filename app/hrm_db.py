"""HRM-Datenbankverbindung - verwendet die gleiche Datenbankverbindung wie die Hauptanwendung."""
from app.db import get_db as hrm_db

__all__ = ["hrm_db"]
