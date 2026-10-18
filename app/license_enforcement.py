"""Lizenz-Erzwingung für ABoroSoft-Produkte.

Dieses Modul blockiert alle Funktionen, wenn keine gültige Lizenz vorhanden ist.
Nur die Lizenz-Eingabe und -Validierung sind ohne Lizenz zugänglich.
"""
import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings


# Pfad zur lokalen Lizenzdatei
LICENSE_FILE = Path(__file__).parent.parent / ".license.json"


def get_product_sku() -> str:
    """Gibt die Produkt-SKU zurück (aus Config oder Environment)."""
    settings = get_settings()
    # Fallback: aus App-Name ableiten
    product_map = {
        "aborodesk": "DESK-STD",
        "desk": "DESK-STD",
        "lms": "ABOLMS-STD",
        "cloudshare": "CLOUDSHARE-STD",
        "helpdesk": "HELPDESK-STD",
    }
    app_name = getattr(settings, "app_name", "desk").lower()
    return product_map.get(app_name, "DESK-STD")


def load_local_license() -> dict[str, Any] | None:
    """
    Lädt die lokal gespeicherte Lizenz.

    Returns:
        dict mit Lizenzdaten oder None
    """
    if not LICENSE_FILE.exists():
        return None

    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def save_local_license(license_data: dict) -> None:
    """Speichert die Lizenz lokal."""
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(license_data, f, indent=2)
    # Nur Owner darf lesen/schreiben
    LICENSE_FILE.chmod(0o600)


def validate_local_license() -> dict[str, Any]:
    """
    Validiert die lokal gespeicherte Lizenz.

    Returns:
        dict mit 'valid' (bool) und optional 'reason' (str) und Lizenzdetails
    """
    license_data = load_local_license()

    if not license_data:
        return {"valid": False, "reason": "Keine Lizenz vorhanden"}

    # Pflichtfelder prüfen
    required_fields = ["license_key", "product_sku", "valid_until", "status"]
    for field in required_fields:
        if field not in license_data:
            return {"valid": False, "reason": f"Ungültige Lizenz: {field} fehlt"}

    # Produkt prüfen
    current_product = get_product_sku()
    if license_data["product_sku"] != current_product:
        return {
            "valid": False,
            "reason": f"Lizenz für falsches Produkt ({license_data['product_sku']} statt {current_product})",
        }

    # Status prüfen
    if license_data.get("status") != "active":
        return {"valid": False, "reason": f"Lizenz ist {license_data.get('status', 'unknown')}"}

    # Ablaufdatum prüfen
    valid_until = license_data.get("valid_until", "")
    if valid_until:
        today = date.today().isoformat()
        if valid_until < today:
            return {"valid": False, "reason": f"Lizenz abgelaufen am {valid_until}"}

    # Gültigkeitsbeginn prüfen
    valid_from = license_data.get("valid_from", "")
    if valid_from:
        today = date.today().isoformat()
        if valid_from > today:
            return {"valid": False, "reason": f"Lizenz erst gültig ab {valid_from}"}

    return {
        "valid": True,
        "license_key": license_data["license_key"],
        "customer_name": license_data.get("customer_name", ""),
        "customer_email": license_data.get("customer_email", ""),
        "valid_until": license_data.get("valid_until", ""),
        "max_users": license_data.get("max_users", 1),
    }


def is_license_required_path(path: str) -> bool:
    """
    Prüft, ob für diesen Pfad eine Lizenz erforderlich ist.

    Ohne Lizenz sind nur folgende Pfade erlaubt:
    - /license (Lizenz-Eingabe)
    - /license/activate (Lizenz aktivieren)
    - /license/validate (Lizenz validieren via API)
    - /health (Health-Check für Monitoring)
    - /static/* (CSS, JS, Bilder)
    - /favicon.ico
    """
    # Pfade, die ohne Lizenz zugänglich sind
    allowed_paths = [
        "/health",
        "/license",
        "/license/",
        "/license/activate",
        "/license/validate",
        "/static/",
        "/favicon.ico",
    ]

    for allowed in allowed_paths:
        if path == allowed or path.startswith(allowed):
            return False

    # Alle anderen Pfade benötigen eine Lizenz
    return True


def check_license_middleware(request: Request) -> RedirectResponse | None:
    """
    Middleware-Funktion zur Lizenzprüfung.

    Returns:
        RedirectResponse zur Lizenz-Seite, wenn keine Lizenz vorhanden
        None, wenn Zugriff erlaubt ist
    """
    path = request.url.path

    # Pfad benötigt keine Lizenz
    if not is_license_required_path(path):
        return None

    # Lizenz validieren
    validation = validate_local_license()

    if not validation["valid"]:
        # Keine gültige Lizenz: Umleitung zur Lizenz-Eingabe
        return RedirectResponse(url="/license", status_code=303)

    # Lizenz gültig: Zugriff erlaubt
    return None


def get_license_page_html(message: str = "", error: str = "") -> str:
    """
    Erstellt die HTML-Seite für die Lizenz-Eingabe.

    Diese Seite ist die EINZIGE, die ohne Lizenz zugänglich ist.
    """
    product_name = {
        "DESK-STD": "ABoroDesk",
        "ABOLMS-STD": "ABoroLMS",
        "CLOUDSHARE-STD": "CloudShare",
        "HELPDESK-STD": "HelpDesk",
    }.get(get_product_sku(), "ABoroSoft")

    validation = validate_local_license()
    current_license = load_local_license()

    # Status-Anzeige
    status_html = ""
    if validation["valid"]:
        status_html = f"""
        <div style="background: #e8f5e9; border: 1px solid #4caf50; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <strong style="color: #2e7d32;">✓ Lizenz aktiv</strong><br>
            <small>
                Kunde: {validation.get('customer_name', 'N/A')}<br>
                Gültig bis: {validation.get('valid_until', 'N/A')}<br>
                Max. Benutzer: {validation.get('max_users', 1)}
            </small>
        </div>
        """
    elif current_license:
        reason = validation.get("reason", "Unbekannter Fehler")
        status_html = f"""
        <div style="background: #ffebee; border: 1px solid #f44336; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <strong style="color: #c62828;">✗ Lizenz ungültig</strong><br>
            <small>{reason}</small>
        </div>
        """

    if error:
        status_html += f"""
        <div style="background: #ffebee; border: 1px solid #f44336; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
            <strong style="color: #c62828;">Fehler:</strong> {error}
        </div>
        """

    if message:
        status_html += f"""
        <div style="background: #e3f2fd; border: 1px solid #2196f3; padding: 1rem; border-radius: 4px; margin-bottom: 1rem;">
            {message}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lizenzaktivierung - {product_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 1rem;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            padding: 2rem;
        }}
        h1 {{
            margin: 0 0 0.5rem 0;
            color: #333;
            font-size: 1.8rem;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 2rem;
        }}
        label {{
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #333;
        }}
        input {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 1rem;
            box-sizing: border-box;
            font-family: monospace;
            letter-spacing: 0.05em;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        button {{
            width: 100%;
            padding: 0.75rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 1rem;
        }}
        button:hover {{
            opacity: 0.9;
        }}
        .lock-icon {{
            text-align: center;
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        small {{
            color: #666;
        }}
        .info {{
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 6px;
            margin-top: 2rem;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="lock-icon">🔐</div>
        <h1>{product_name}</h1>
        <p class="subtitle">Lizenzaktivierung erforderlich</p>

        {status_html}

        <form method="POST" action="/license/activate">
            <label for="license_key">Lizenzschlüssel</label>
            <input
                type="text"
                id="license_key"
                name="license_key"
                placeholder="XXXX-XXXX-XXXX-XXXX"
                pattern="[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}"
                maxlength="19"
                required
                autofocus
            >
            <button type="submit">Lizenz aktivieren</button>
        </form>

        <div class="info">
            <strong>Keine Lizenz?</strong><br>
            Besuchen Sie <a href="https://aborosoft.com" target="_blank">aborosoft.com</a>
            um eine Lizenz zu erwerben.<br><br>
            <strong>Produkt:</strong> {product_name} ({get_product_sku()})
        </div>
    </div>
</body>
</html>"""


# Export für einfachen Import
__all__ = [
    "validate_local_license",
    "load_local_license",
    "save_local_license",
    "check_license_middleware",
    "get_license_page_html",
    "is_license_required_path",
]
