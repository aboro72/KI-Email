# Installation auf einem einzelnen Linux-Server

Diese Variante richtet einen einzelnen Debian-/Ubuntu-Server mit Python, Nginx und systemd ein. Sie ist für eine eigene VM oder einen dedizierten Server gedacht, auf dem kein ISPConfig die Webserver-Konfiguration verwaltet.

## Voraussetzungen

- frischer oder kontrollierter Debian-/Ubuntu-Server
- Root-Zugriff
- DNS-A- bzw. AAAA-Record für die Domain auf den Server
- offene Ports 80 und 443 in Firewall/Security Group
- optional ein Bedrock-Zugang

Das Skript installiert keine Datenbankserver. Standardmäßig wird SQLite unter `/var/lib/aborodesk/ki_email.db` verwendet. Für mehrere Worker oder höhere Last sollte später PostgreSQL ergänzt werden.

## Installation

Repository übertragen oder klonen und in das Projektverzeichnis wechseln:

```bash
git clone <REPOSITORY-URL> /opt/aborodesk-source
cd /opt/aborodesk-source
chmod +x deploy/single-server/install.sh
```

Nur HTTP einrichten:

```bash
sudo DOMAIN=mail.example.com deploy/single-server/install.sh
```

Mit Let's Encrypt direkt während der Installation:

```bash
sudo DOMAIN=mail.example.com ENABLE_TLS=1 CERTBOT_EMAIL=admin@example.com \
  deploy/single-server/install.sh
```

Das Skript:

- installiert Python, venv, pip, Nginx und Systemwerkzeuge
- legt den unprivilegierten Benutzer `aborodesk` an
- kopiert den Quellcode ohne Git-Metadaten, `.env`, Datenbank und lokale Secrets
- erstellt eine virtuelle Umgebung und installiert `requirements.txt`
- erzeugt eine zufällige `SECRET_KEY`
- richtet `/etc/systemd/system/aborodesk.service` ein
- legt Nginx als Reverse Proxy auf `127.0.0.1:8000` an
- prüft die Anwendung über `/health`

## Erste Konfiguration

```bash
sudoedit /etc/aborodesk/aborodesk.env
```

Produktive Zugangsdaten eintragen:

```dotenv
ADMIN_EMAIL=admin@deine-domain.tld
ADMIN_PASSWORD=<langes-einmaliges-passwort>
SESSION_COOKIE_SECURE=true
```

Anschließend:

```bash
sudo systemctl restart aborodesk
sudo systemctl status aborodesk
```

Die Environment-Datei enthält Geheimnisse und darf nicht öffentlich lesbar sein.

## Firewall

Mit UFW beispielsweise:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Port 8000 muss nicht öffentlich geöffnet werden; Uvicorn lauscht nur auf `127.0.0.1`.

## Bedrock optional einrichten

Der API-Key wird aus Sicherheitsgründen nicht aus dem Repository übernommen:

```bash
sudo install -o root -g aborodesk -m 0640 /sicherer/pfad/bedrock-long-term-api-key.csv \
  /etc/aborodesk/bedrock-long-term-api-key.csv
sudo systemctl restart aborodesk
```

Alternativ ein geeignetes Secret-Management für den Laufzeit-Token verwenden. Keine Keys in `.env`, Git, Shell-History oder Logs eintragen.

## Kontrolle und Fehleranalyse

```bash
curl -fsS http://127.0.0.1:8000/health
sudo systemctl status aborodesk nginx
sudo journalctl -u aborodesk -f
sudo nginx -t
```

Wenn die Domain nicht erreichbar ist, zuerst DNS, Firewall, Nginx und anschließend den lokalen Healthcheck prüfen.

## Updates

Vor jedem Update Datenbank und Environment-Datei sichern. Danach den neuen Quellcode übertragen und den Dienst neu starten:

```bash
sudo rsync -a --exclude '.git/' --exclude '.venv/' --exclude '*.db' ./ /opt/aborodesk/
sudo -u aborodesk /opt/aborodesk/.venv/bin/pip install -r /opt/aborodesk/requirements.txt
sudo systemctl restart aborodesk
```

Bei Änderungen am Schema den Startvorgang und die Logs kontrollieren. Für produktive Backups mindestens `/var/lib/aborodesk/ki_email.db` und `/etc/aborodesk/aborodesk.env` getrennt und verschlüsselt sichern.

## Produktionshinweise

- SQLite ist für einen einzelnen, kleinen Server geeignet; bei wachsender Nutzung PostgreSQL einsetzen.
- Regelmäßige Backups und ein getesteter Restore sind Pflicht.
- Bedrock-, Mail- und SMTP-Zugangsdaten getrennt vom Quellcode verwalten.
- Nginx-/systemd-Logs überwachen und Rotation einrichten.
- Vor dem Internetbetrieb Tests, CSRF-/Rate-Limit-Verhalten, Upload-Limits und Rollenrechte prüfen.
