"""Kleine Gmail-API-Schicht für Posteingang und Nachrichten."""

import base64
import json
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def service_from_token(token_json: str):
    """Erzeugt einen Gmail-Service aus dem verschlüsselten OAuth-Token."""
    credentials = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return build("gmail", "v1", credentials=credentials, cache_discovery=False), credentials


def header(message: dict, name: str) -> str:
    for item in message.get("payload", {}).get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def body_text(message: dict) -> str:
    """Liest nur einfachen Text; HTML wird nicht als Seite ausgeführt."""
    payload = message.get("payload", {})
    for part in [payload, *payload.get("parts", [])]:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    return "(Kein einfacher Textinhalt vorhanden.)"


def message_summary(message: dict) -> dict:
    date = header(message, "Date")
    try:
        date = parsedate_to_datetime(date).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError, OverflowError):
        pass
    return {"id": message.get("id", ""), "sender": header(message, "From"), "subject": header(message, "Subject") or "(Ohne Betreff)", "date": date, "body": body_text(message), "labels": message.get("labelIds", [])}
