#!/usr/bin/env python3
"""Geführte AboroDesk-Installation für Debian/Ubuntu."""
from getpass import getpass
import os
from pathlib import Path
import re
import subprocess
import sys


def ask(prompt, default="", secret=False):
    suffix = f" [{default}]" if default else ""
    value = (getpass if secret else input)(prompt + suffix + ": ").strip()
    return value or default


def choice(prompt, options, default):
    while True:
        value = ask(prompt, default).lower()
        if value in options:
            return value
        print("Bitte auswählen / Please choose: " + ", ".join(options))


def valid_email(value):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def main():
    if os.name != "posix" or os.geteuid() != 0:
        raise SystemExit("Bitte unter Debian/Ubuntu als root ausführen / Run as root on Debian/Ubuntu.")
    root = Path(__file__).resolve().parent.parent
    print("\nAboroDesk – geführte Installation / guided setup\n")
    mode = choice("Installation: 1 = ISPConfig3, 2 = Einzelserver / single server", {"1", "2"}, "1")
    language = choice("Globale Sprache / global language (de/en)", {"de", "en"}, "de")
    admin_email = ask("Administrator-E-Mail / administrator email", "admin@example.com")
    if not valid_email(admin_email):
        raise SystemExit("Ungültige E-Mail-Adresse / Invalid email address.")
    admin_password = ask("Administrator-Passwort / administrator password", secret=True)
    confirmation = ask("Passwort wiederholen / repeat password", secret=True)
    if len(admin_password) < 12 or admin_password != confirmation:
        raise SystemExit("Passwörter stimmen nicht überein oder sind kürzer als 12 Zeichen / Passwords differ or are shorter than 12 characters.")
    mongodb_uri = ask("MongoDB-Verbindungsadresse / connection URI")
    if not mongodb_uri.startswith(("mongodb://", "mongodb+srv://")):
        raise SystemExit("MongoDB-Adresse muss mit mongodb:// oder mongodb+srv:// beginnen.")

    env = os.environ.copy()
    env.update({"SOURCE_DIR": str(root), "MONGODB_URI": mongodb_uri, "ADMIN_EMAIL": admin_email,
                "ADMIN_PASSWORD": admin_password, "UI_LANGUAGE": language})
    if mode == "1":
        env["SERVICE_USER"] = ask("ISPConfig-Webbenutzer / web user", env.get("SERVICE_USER", "www-data"))
        env["SERVICE_GROUP"] = ask("ISPConfig-Webgruppe / web group", env.get("SERVICE_GROUP", env["SERVICE_USER"]))
        env["APP_PORT"] = ask("Lokaler Port / local port", "8001")
        script = root / "deploy" / "ispconfig3" / "install.sh"
    else:
        env["DOMAIN"] = ask("Domain", "_")
        env["APP_PORT"] = ask("Lokaler Port / local port", "8000")
        tls = choice("Let's Encrypt automatisch einrichten? / configure automatically? (yes/no)", {"yes", "no"}, "no")
        env["ENABLE_TLS"] = "1" if tls == "yes" else "0"
        if tls == "yes":
            env["CERTBOT_EMAIL"] = ask("E-Mail für Let's Encrypt")
        script = root / "deploy" / "single-server" / "install.sh"

    print("\nDie Installation startet jetzt. Passwörter werden nicht ausgegeben.\n")
    subprocess.run(["bash", str(script)], env=env, check=True)
    print("\nFertig / Complete. Globale Sprache:", "Deutsch" if language == "de" else "English")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen / Cancelled.")
        sys.exit(130)
