"""Kleine Verwaltungsbefehle für die lokale Entwicklung.

Diese Datei ist bewusst getrennt von der Webanwendung. So kann ein Administrator
angelegt werden, ohne zuerst den Webserver öffnen zu müssen.
"""

import getpass

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Permission, Role, User
from app.security import hash_password


def ensure_admin_role(db):
    """Legt die Administratorrolle und ihre Grundrechte an, falls nötig."""
    role = db.scalar(select(Role).where(Role.name == "admin"))
    if role:
        return role

    role = Role(name="admin")
    db.add(role)
    db.flush()
    for permission_name in ("AI_GENERATE", "EMAIL_SEND", "ADMIN_SETTINGS"):
        permission = Permission(name=permission_name)
        db.add(permission)
        role.permissions.append(permission)
    db.commit()
    return role


def create_admin() -> None:
    """Fragt die Zugangsdaten ab und legt einen Administrator an."""
    Base.metadata.create_all(engine)
    email = input("Administrator-E-Mail: ").strip().lower()
    display_name = input("Anzeigename: ").strip() or "Administrator"
    password = getpass.getpass("Passwort: ")
    password_again = getpass.getpass("Passwort wiederholen: ")

    if not email or not password:
        raise SystemExit("E-Mail und Passwort dürfen nicht leer sein.")
    if password != password_again:
        raise SystemExit("Die Passwörter stimmen nicht überein.")

    with SessionLocal() as db:
        role = ensure_admin_role(db)
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            raise SystemExit("Für diese E-Mail-Adresse existiert bereits ein Benutzer.")
        db.add(User(email=email, display_name=display_name, password_hash=hash_password(password), role_id=role.id))
        db.commit()
    print(f"Administrator {email} wurde angelegt.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "create-admin":
        create_admin()
    else:
        print("Verwendung: py -3 -m app.cli create-admin")
