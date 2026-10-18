"""Lizenzv

altungssystem für alle ABoroSoft-Produkte."""
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import License, LicenseActivation


def generate_license_key(product_sku: str) -> str:
    """
    Generiert einen eindeutigen Lizenzschlüssel.

    Format: XXXX-XXXX-XXXX-XXXX (16 Zeichen, 4 Blöcke)
    """
    # Prefix basierend auf Produkt (erste 4 Zeichen des SKU)
    prefix = product_sku[:4].upper().ljust(4, 'X')

    # 12 zufällige Zeichen (Base32 ohne 0, O, I, L für bessere Lesbarkeit)
    chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    random_part = ''.join(secrets.choice(chars) for _ in range(12))

    # Format: PREFIX-XXXX-XXXX-XXXX
    key = f"{prefix}-{random_part[0:4]}-{random_part[4:8]}-{random_part[8:12]}"

    return key


def create_license(
    db: Session,
    product_sku: str,
    customer_name: str,
    customer_email: str,
    duration_days: int = 365,
    max_users: int = 1,
    max_activations: int = 1,
    created_by_user_id: int = 1,
    customer_company: str = "",
    notes: str = "",
    paypal_transaction_id: int | None = None,
    erp_document_id: int | None = None,
) -> License:
    """
    Erstellt eine neue Lizenz.

    Args:
        db: Datenbank-Session
        product_sku: SKU des Produkts (z.B. "ABOLMS-STD", "CLOUDSHARE-PRO")
        customer_name: Name des Kunden
        customer_email: E-Mail des Kunden
        duration_days: Gültigkeitsdauer in Tagen (Standard: 365)
        max_users: Maximale Anzahl Benutzer
        max_activations: Maximale Anzahl Aktivierungen
        created_by_user_id: User-ID des Erstellers
        customer_company: Firmenname (optional)
        notes: Notizen (optional)
        paypal_transaction_id: Verknüpfte PayPal-Transaktion (optional)
        erp_document_id: Verknüpfte Rechnung (optional)

    Returns:
        Die erstellte Lizenz
    """
    # Generiere eindeutigen Lizenzschlüssel
    while True:
        license_key = generate_license_key(product_sku)
        existing = db.scalar(select(License).where(License.license_key == license_key))
        if not existing:
            break

    # Berechne Gültigkeitsdaten
    today = date.today()
    valid_from = today.isoformat()
    valid_until = (today + timedelta(days=duration_days)).isoformat()

    # Erstelle Lizenz
    license = License(
        license_key=license_key,
        product_sku=product_sku,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_company=customer_company,
        valid_from=valid_from,
        valid_until=valid_until,
        max_users=max_users,
        max_activations=max_activations,
        notes=notes,
        paypal_transaction_id=paypal_transaction_id,
        erp_document_id=erp_document_id,
        created_by_user_id=created_by_user_id,
        status="active",
    )

    db.add(license)
    db.commit()
    db.refresh(license)

    return license


def validate_license(db: Session, license_key: str, product_sku: str) -> dict:
    """
    Validiert einen Lizenzschlüssel.

    Returns:
        dict mit Status und Details
    """
    # Debug: Zähle alle Lizenzen
    from sqlalchemy import func
    total_count = db.scalar(select(func.count(License.id)))
    print(f"[DEBUG] validate_license: Searching for '{license_key}' in product '{product_sku}'")
    print(f"[DEBUG] Total licenses in DB: {total_count}")

    license = db.scalar(select(License).where(License.license_key == license_key))

    print(f"[DEBUG] License found: {license is not None}")
    if license:
        print(f"[DEBUG] License details: product={license.product_sku}, status={license.status}")

    if not license:
        return {"valid": False, "reason": "License key not found"}

    if license.product_sku != product_sku:
        return {"valid": False, "reason": "License key not valid for this product"}

    if license.status != "active":
        return {"valid": False, "reason": f"License is {license.status}"}

    # Prüfe Gültigkeitsdatum
    today = date.today().isoformat()
    if license.valid_until and license.valid_until < today:
        return {"valid": False, "reason": "License expired"}

    if license.valid_from > today:
        return {"valid": False, "reason": "License not yet valid"}

    return {
        "valid": True,
        "license_id": license.id,
        "customer_name": license.customer_name,
        "customer_email": license.customer_email,
        "valid_until": license.valid_until,
        "max_users": license.max_users,
        "max_activations": license.max_activations,
        "current_activations": license.current_activations,
    }


def activate_license(
    db: Session,
    license_key: str,
    product_sku: str,
    machine_fingerprint: str,
    ip_address: str = "",
    hostname: str = "",
    product_version: str = "",
) -> dict:
    """
    Aktiviert eine Lizenz auf einem Gerät.

    Returns:
        dict mit Aktivierungstoken oder Fehler
    """
    # Validiere Lizenz
    validation = validate_license(db, license_key, product_sku)
    if not validation["valid"]:
        return {"success": False, "error": validation["reason"]}

    license = db.scalar(select(License).where(License.license_key == license_key))

    # Prüfe ob bereits aktiviert
    existing = db.scalar(
        select(LicenseActivation)
        .where(LicenseActivation.license_id == license.id)
        .where(LicenseActivation.machine_fingerprint == machine_fingerprint)
        .where(LicenseActivation.status == "active")
    )

    if existing:
        # Aktualisiere last_seen
        existing.last_seen = datetime.now(timezone.utc)
        db.commit()
        return {
            "success": True,
            "activation_token": existing.activation_token,
            "valid_until": license.valid_until,
        }

    # Prüfe Aktivierungslimit
    if license.current_activations >= license.max_activations:
        return {"success": False, "error": "Maximum activations reached"}

    # Erstelle Aktivierung
    activation_token = secrets.token_urlsafe(32)

    activation = LicenseActivation(
        license_id=license.id,
        activation_token=activation_token,
        machine_fingerprint=machine_fingerprint,
        ip_address=ip_address,
        hostname=hostname,
        product_version=product_version,
        status="active",
    )

    db.add(activation)
    license.current_activations += 1
    db.commit()

    return {
        "success": True,
        "activation_token": activation_token,
        "valid_until": license.valid_until,
        "max_users": license.max_users,
    }


def deactivate_license(db: Session, activation_token: str) -> bool:
    """Deaktiviert eine Lizenzaktivierung."""
    activation = db.scalar(
        select(LicenseActivation).where(LicenseActivation.activation_token == activation_token)
    )

    if not activation or activation.status != "active":
        return False

    activation.status = "deactivated"

    license = db.get(License, activation.license_id)
    if license:
        license.current_activations = max(0, license.current_activations - 1)

    db.commit()
    return True


def check_activation(db: Session, activation_token: str) -> dict:
    """
    Prüft eine Aktivierung (Heartbeat).

    Returns:
        dict mit Status
    """
    activation = db.scalar(
        select(LicenseActivation).where(LicenseActivation.activation_token == activation_token)
    )

    if not activation:
        return {"valid": False, "reason": "Activation not found"}

    if activation.status != "active":
        return {"valid": False, "reason": f"Activation is {activation.status}"}

    license = db.get(License, activation.license_id)
    if not license:
        return {"valid": False, "reason": "License not found"}

    # Validiere Lizenz
    validation = validate_license(db, license.license_key, license.product_sku)
    if not validation["valid"]:
        return {"valid": False, "reason": validation["reason"]}

    # Aktualisiere last_seen
    activation.last_seen = datetime.now(timezone.utc)
    db.commit()

    return {
        "valid": True,
        "license_key": license.license_key,
        "valid_until": license.valid_until,
        "max_users": license.max_users,
    }
