# Installation auf einem einzelnen Linux-Server

Diese Variante richtet einen einzelnen Debian-/Ubuntu-Server mit Python, Nginx und systemd ein. Sie ist für eine eigene VM oder einen dedizierten Server gedacht, auf dem kein ISPConfig die Webserver-Konfiguration verwaltet.

## Voraussetzungen

- frischer oder kontrollierter Debian-/Ubuntu-Server
- Root-Zugriff
- DNS-A- bzw. AAAA-Record für die Domain auf den Server
- offene Ports 80 und 443 in Firewall/Security Group
- optional ein Bedrock-Zugang

Das Skript installiert keinen Datenbankserver. Die Anwendung verwendet die konfigurierte MongoDB als dauerhafte Persistenz.

## Installation

Repository übertragen oder klonen und in das Projektverzeichnis wechseln:

```bash
git clone https://github.com/aboro72/KI-Email.git /opt/aborodesk-source
cd /opt/aborodesk-source
chmod +x deploy/single-server/install.sh
```

Nur HTTP einrichten:

```bash
sudo DOMAIN=mail.example.com \
  MONGODB_URI='mongodb://aborodesk_app:<PASSWORT>@212.44.166.238:27017/aborodesk?authSource=admin' \
  deploy/single-server/install.sh
```

Mit Let's Encrypt direkt während der Installation:

```bash
sudo DOMAIN=mail.example.com ENABLE_TLS=1 CERTBOT_EMAIL=admin@example.com \
  MONGODB_URI='mongodb://aborodesk_app:<PASSWORT>@212.44.166.238:27017/aborodesk?authSource=admin' \
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

`MONGODB_URI` ist erforderlich. Das Passwort muss URL-kodiert werden, wenn es Sonderzeichen wie `@`, `:`, `/` oder `#` enthält. Danach wird MongoDB als dauerhafte Persistenz verwendet; eine SQLite-Produktionsdatei wird nicht angelegt.

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

Vor jedem Update MongoDB und Environment-Datei sichern. Danach den neuen Quellcode übertragen und den Dienst neu starten:

```bash
sudo rsync -a --exclude '.git/' --exclude '.venv/' --exclude '*.db' ./ /opt/aborodesk/
sudo -u aborodesk /opt/aborodesk/.venv/bin/pip install -r /opt/aborodesk/requirements.txt
sudo systemctl restart aborodesk
```

Bei Änderungen am Schema den Startvorgang und die Logs kontrollieren. Für produktive Backups die MongoDB-Datenbank `aborodesk` und `/etc/aborodesk/aborodesk.env` getrennt und verschlüsselt sichern.

## Automatische Updates alle 20 Minuten

Nach der ersten Installation kann der systemd-Timer einen Git-Branch überwachen:

```bash
cd /opt/aborodesk
chmod +x deploy/update.sh deploy/install-update-timer.sh
sudo REPOSITORY_URL='https://github.com/aboro72/KI-Email.git' \
  GIT_BRANCH=master SERVICE_NAME=aborodesk APP_DIR=/opt/aborodesk APP_PORT=8000 \
  bash deploy/install-update-timer.sh
```

Bei privaten Repositories einen SSH-Deploy-Key oder einen eingerichteten Git-Credential-Helper verwenden. Der Timer prüft alle 20 Minuten, installiert neue Python-Abhängigkeiten, startet den Dienst neu und prüft `/health`. Bei einem Fehler wird der vorherige Quellstand wiederhergestellt.

Der Update-Dienst schreibt seinen Status nach `/var/lib/aborodesk-updater/status.json`. Das Dashboard zeigt dadurch an, ob die Anwendung aktuell ist, wann ein Update installiert wurde oder ob ein Rollback erfolgt ist.

```bash
sudo systemctl list-timers aborodesk-update.timer
sudo journalctl -u aborodesk-update.service -f
```

## Produktionshinweise

- MongoDB-Backups und ein getesteter Restore sind Pflicht.
- Regelmäßige Backups und ein getesteter Restore sind Pflicht.
- Bedrock-, Mail- und SMTP-Zugangsdaten getrennt vom Quellcode verwalten.
- Nginx-/systemd-Logs überwachen und Rotation einrichten.
- Vor dem Internetbetrieb Tests, CSRF-/Rate-Limit-Verhalten, Upload-Limits und Rollenrechte prüfen.
