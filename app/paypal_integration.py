"""PayPal API Integration für Transaktionsverwaltung und Webhook-Empfang."""
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PayPalConfig, PayPalTransaction
from app.security import decrypt_secret, encrypt_secret


class PayPalAPIError(Exception):
    """Fehler bei PayPal API-Aufrufen."""
    pass


def get_paypal_config(db: Session) -> PayPalConfig | None:
    """Lädt die PayPal-Konfiguration."""
    return db.scalar(select(PayPalConfig).limit(1))


def get_access_token(config: PayPalConfig) -> str:
    """Holt OAuth 2.0 Access Token von PayPal."""
    if not config.client_id or not config.client_secret_encrypted:
        raise PayPalAPIError("PayPal API-Credentials nicht konfiguriert")

    base_url = "https://api-m.sandbox.paypal.com" if config.environment == "sandbox" else "https://api-m.paypal.com"
    client_secret = decrypt_secret(config.client_secret_encrypted)

    response = requests.post(
        f"{base_url}/v1/oauth2/token",
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        auth=(config.client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=30
    )

    if response.status_code != 200:
        raise PayPalAPIError(f"OAuth fehlgeschlagen: {response.status_code} - {response.text}")

    return response.json()["access_token"]


def fetch_transactions(config: PayPalConfig, db: Session, start_date: str | None = None, end_date: str | None = None) -> int:
    """
    Synchronisiert Transaktionen von PayPal.

    Args:
        config: PayPal-Konfiguration
        db: Datenbank-Session
        start_date: Startdatum im Format YYYY-MM-DD (default: vor 30 Tagen)
        end_date: Enddatum im Format YYYY-MM-DD (default: heute)

    Returns:
        Anzahl der importierten Transaktionen
    """
    if not config.enabled:
        raise PayPalAPIError("PayPal-Integration ist deaktiviert")

    access_token = get_access_token(config)
    base_url = "https://api-m.sandbox.paypal.com" if config.environment == "sandbox" else "https://api-m.paypal.com"

    # Standard: letzte 30 Tage
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    else:
        start_date = f"{start_date}T00:00:00Z"

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")
    else:
        end_date = f"{end_date}T23:59:59Z"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "fields": "all",
        "page_size": 100,
    }

    response = requests.get(
        f"{base_url}/v1/reporting/transactions",
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        raise PayPalAPIError(f"Transaktionsabruf fehlgeschlagen: {response.status_code} - {response.text}")

    data = response.json()
    transactions = data.get("transaction_details", [])
    imported = 0

    for tx in transactions:
        tx_info = tx.get("transaction_info", {})
        tx_id = tx_info.get("transaction_id")

        if not tx_id:
            continue

        # Prüfe ob Transaktion bereits existiert
        existing = db.scalar(select(PayPalTransaction).where(PayPalTransaction.transaction_id == tx_id))
        if existing:
            continue

        # Betrag parsen
        amount_info = tx_info.get("transaction_amount", {})
        amount_value = float(amount_info.get("value", 0))
        amount_cents = int(amount_value * 100)

        fee_info = tx_info.get("fee_amount", {})
        fee_value = float(fee_info.get("value", 0))
        fee_cents = int(abs(fee_value) * 100)

        net_cents = amount_cents - fee_cents

        # Payer-Info
        payer_info = tx.get("payer_info", {})
        payer_email = payer_info.get("email_address", "")
        payer_name = payer_info.get("payer_name", {})
        payer_full_name = f"{payer_name.get('given_name', '')} {payer_name.get('surname', '')}".strip()

        # Datum
        tx_date_str = tx_info.get("transaction_initiation_date")
        tx_date = datetime.fromisoformat(tx_date_str.replace("Z", "+00:00")) if tx_date_str else datetime.now(timezone.utc)

        transaction = PayPalTransaction(
            transaction_id=tx_id,
            transaction_type=tx_info.get("transaction_event_code", ""),
            transaction_status=tx_info.get("transaction_status", ""),
            transaction_amount_cents=amount_cents,
            transaction_currency=amount_info.get("currency_code", "EUR"),
            fee_amount_cents=fee_cents,
            net_amount_cents=net_cents,
            payer_email=payer_email,
            payer_name=payer_full_name,
            transaction_date=tx_date,
            transaction_note=tx_info.get("transaction_note", ""),
            raw_data=json.dumps(tx),
            synced_at=datetime.now(timezone.utc),
        )

        db.add(transaction)
        imported += 1

    config.last_sync = datetime.now(timezone.utc)
    db.commit()

    return imported


def get_balance(config: PayPalConfig) -> dict[str, Any]:
    """
    Holt den aktuellen PayPal-Kontostand.

    Returns:
        Dict mit Kontoständen pro Währung
    """
    if not config.enabled:
        raise PayPalAPIError("PayPal-Integration ist deaktiviert")

    access_token = get_access_token(config)
    base_url = "https://api-m.sandbox.paypal.com" if config.environment == "sandbox" else "https://api-m.paypal.com"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{base_url}/v1/reporting/balances",
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise PayPalAPIError(f"Kontostandabruf fehlgeschlagen: {response.status_code} - {response.text}")

    return response.json()


def verify_webhook_signature(webhook_id: str, transmission_id: str, timestamp: str,
                             webhook_event: dict, cert_url: str, actual_signature: str,
                             config: PayPalConfig) -> bool:
    """
    Verifiziert die Signatur eines PayPal Webhooks.

    Returns:
        True wenn die Signatur gültig ist
    """
    access_token = get_access_token(config)
    base_url = "https://api-m.sandbox.paypal.com" if config.environment == "sandbox" else "https://api-m.paypal.com"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    verify_data = {
        "transmission_id": transmission_id,
        "transmission_time": timestamp,
        "cert_url": cert_url,
        "auth_algo": "SHA256withRSA",
        "transmission_sig": actual_signature,
        "webhook_id": webhook_id,
        "webhook_event": webhook_event
    }

    response = requests.post(
        f"{base_url}/v1/notifications/verify-webhook-signature",
        headers=headers,
        json=verify_data,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
        return result.get("verification_status") == "SUCCESS"

    return False
