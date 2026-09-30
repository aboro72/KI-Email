# Installation auf einem ISPConfig3-Server

Diese Variante setzt einen bestehenden Debian-/Ubuntu-Server mit ISPConfig3 voraus. ISPConfig bleibt für Domain, SSL und Webserver zuständig. Die Anwendung läuft als lokaler systemd-Dienst und wird über einen Reverse Proxy veröffentlicht.

## Voraussetzungen

- Root- oder sudo-Zugriff
- ISPConfig3 ist bereits installiert und verwaltet die gewünschte Domain
- Debian/Ubuntu mit `apt-get`
- eine freie lokale Portnummer, standardmäßig `8001`
- SMTP-/IMAP-Daten für die späteren E-Mail-Konten
- optional ein AWS-Bedrock-Zugang

Die Anwendung und Datenbank sollten nicht direkt aus dem öffentlichen ISPConfig-Webroot ausgeführt werden.

## Installation

Vor der Installation die Zielumgebung prüfen:

```bash
sudo MONGODB_URI='mongodb://BENUTZER:PASSWORT@SERVER:27017/aborodesk?authSource=admin' bash /web/app/deploy/preflight.sh
```

## FTP-Layout

Lade den kompletten Projektordner per FTP so hoch, dass die Struktur auf dem Server wie folgt aussieht:

```text
/web/app/
├── app/
├── requirements.txt
├── README.md
└── deploy/
    └── ispconfig3/
        ├── install.sh
        └── installation.md
```

Wichtig: Nur die beiden Dateien aus `deploy/ispconfig3` reichen nicht aus. Das Skript benötigt den vollständigen Projektstamm `/web/app` mit `app/` und `requirements.txt`.

Der FTP-Upload allein installiert noch nichts. Danach per SSH am Server anmelden und die Installation aus dem Projektstamm `/web/app` mit Root- oder sudo-Rechten ausführen:

```bash
cd /web/app
chmod +x deploy/ispconfig3/install.sh
sudo SERVICE_USER=webXXX SERVICE_GROUP=clientY APP_PORT=8001 \
  MONGODB_URI='mongodb://aborodesk_app:<PASSWORT>@212.44.166.238:27017/aborodesk?authSource=admin' \
  bash deploy/ispconfig3/install.sh
```

`webXXX` und `clientY` müssen durch den Benutzer und die Gruppe der betreffenden ISPConfig-Website ersetzt werden. Wenn ein separater Systembenutzer verwendet werden soll, muss dieser vorher existieren und Zugriff auf die Installationsverzeichnisse erhalten. Falls Benutzer und Gruppe identisch sind, kann `SERVICE_GROUP` entfallen.

Das Skript erkennt den Projektstamm unabhängig davon, ob es mit `bash deploy/ispconfig3/install.sh` oder direkt aus seinem Unterordner gestartet wird. Standardmäßig wird `/web/app` als Quelle verwendet.

`MONGODB_URI` ist erforderlich. Das Passwort muss URL-kodiert werden, wenn es Sonderzeichen wie `@`, `:`, `/` oder `#` enthält. Die URI wird nur in `/etc/aborodesk/aborodesk.env` mit geschützten Dateirechten gespeichert.

Der Standardquellpfad ist bereits `/web/app`. Bei einem anderen FTP-Ziel kann er ausdrücklich gesetzt werden:

```bash
sudo SOURCE_DIR=/anderer/pfad SERVICE_USER=webXXX SERVICE_GROUP=clientY ./install.sh
```

Das Skript:

- installiert Python, venv, pip und rsync
- kopiert den Quellcode ohne Git-Metadaten, `.env`, Datenbank und lokale Secrets
- erstellt `/opt/aborodesk/.venv`
- legt den systemd-Dienst `aborodesk.service` an
- legt die geschützte Environment-Datei unter `/etc/aborodesk/aborodesk.env` an
- startet den Dienst auf `127.0.0.1:8001`

Die Anwendung wird absichtlich nach `/opt/aborodesk` kopiert. Dadurch wird der FTP-Webbereich nicht als Python-Anwendung ausgeführt und die Quelldateien liegen nicht direkt im öffentlich ausgelieferten Website-Verzeichnis.

## Environment-Datei konfigurieren

```bash
sudoedit /etc/aborodesk/aborodesk.env
```

Mindestens diese Werte vor dem produktiven Start setzen:

```dotenv
ADMIN_EMAIL=admin@deine-domain.tld
ADMIN_PASSWORD=<langes-einmaliges-passwort>
SESSION_COOKIE_SECURE=true
```

Danach:

```bash
sudo systemctl restart aborodesk
sudo journalctl -u aborodesk -n 100 --no-pager
```

Die Datei muss geheim bleiben. Keine echten Passwörter oder API-Keys committen.

## ISPConfig-Reverse-Proxy

Die genaue Oberfläche hängt davon ab, ob ISPConfig Apache oder Nginx verwaltet. Die Domain darf nicht auf einen statischen Python-Quellordner zeigen.

### Nginx-Variante

In den zusätzlichen Nginx-Direktiven der Website sinngemäß eintragen:

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 25m;
}
```

### Apache-Variante

Die Proxy-Module müssen aktiviert sein (`proxy`, `proxy_http`, gegebenenfalls `headers`). In den zusätzlichen Apache-Direktiven sinngemäß:

```apache
ProxyPreserveHost On
ProxyPass        / http://127.0.0.1:8001/
ProxyPassReverse / http://127.0.0.1:8001/
RequestHeader set X-Forwarded-Proto "https"
```

Die Direktiven nur in dem von ISPConfig vorgesehenen Feld hinterlegen und anschließend die Webserver-Konfiguration über ISPConfig neu laden. Keine automatisch generierten ISPConfig-Dateien dauerhaft per Hand überschreiben.

## SSL und erster Aufruf

In ISPConfig Let's Encrypt für die Domain aktivieren. Danach aufrufen:

```text
https://deine-domain.tld/
```

Die Anwendung sollte über HTTPS laufen, weil `SESSION_COOKIE_SECURE=true` gesetzt ist.

## Bedrock optional einrichten

Der Key wird bewusst nicht vom Skript erzeugt oder aus dem Repository kopiert. Wenn die Anwendung Bedrock nutzen soll:

```bash
sudo install -o root -g webXXX -m 0640 /sicherer/pfad/bedrock-long-term-api-key.csv \
  /etc/aborodesk/bedrock-long-term-api-key.csv
sudo systemctl restart aborodesk
```

Alternativ kann der für die Laufzeit vorgesehene AWS-Bearer-Token über ein geeignetes Secret-Management bereitgestellt werden. Der Schlüssel darf weder in Git noch in Logs landen.

## Wartung

## Hintergrund-Worker und MongoDB-Backups

Den Worker nach der Installation als root aktivieren:

```bash
sudo APP_DIR=/opt/aborodesk SERVICE_NAME=aborodesk SERVICE_USER=webXXX SERVICE_GROUP=clientY bash /opt/aborodesk/deploy/install-worker.sh
```

Für tägliche Backups die MongoDB Database Tools installieren und `deploy/backup-mongodb.sh` per Cron oder systemd ausführen. Eine Wiederherstellung erfolgt kontrolliert mit `deploy/restore-mongodb.sh`; vorher immer den laufenden Dienst stoppen und ein aktuelles Backup anlegen.

```bash
sudo systemctl status aborodesk
sudo journalctl -u aborodesk -f
sudo systemctl restart aborodesk
```

Für Updates Quellcode sichern, neuen Stand übertragen und danach die Abhängigkeiten aktualisieren:

```bash
sudo rsync -a --exclude '.git/' --exclude '.venv/' --exclude '*.db' ./ /opt/aborodesk/
sudo -u webXXX /opt/aborodesk/.venv/bin/pip install -r /opt/aborodesk/requirements.txt
sudo systemctl restart aborodesk
```

Vor Updates immer ein Datenbank- und Konfigurationsbackup erstellen.

## Automatische Updates alle 20 Minuten

Der automatische Updater verwendet GitHub als Quelle. Der FTP-Ordner `/web/app` bleibt der initiale Installationsort; spätere Updates werden kontrolliert aus dem Git-Repository nach `/opt/aborodesk` übernommen. Dafür muss der Server SSH-/HTTPS-Zugriff auf das Repository haben.

Nach der ersten Installation und dem Upload des neuen Projektstands:

```bash
cd /web/app
chmod +x deploy/update.sh deploy/install-update-timer.sh
sudo REPOSITORY_URL='https://github.com/aboro72/KI-Email.git' \
  GIT_BRANCH=master SERVICE_NAME=aborodesk APP_DIR=/opt/aborodesk APP_PORT=8001 \
  bash deploy/install-update-timer.sh
```

Für ein privates Repository sollte statt eines Tokens in der URL ein SSH-Deploy-Key oder ein bereits eingerichteter Git-Credential-Helper verwendet werden. Zugangsdaten niemals in die URL, in Git-Dateien oder Logs schreiben.

Der Timer prüft alle 20 Minuten und aktualisiert nur bei einem neuen Commit. Vorher wird der aktuelle Anwendungscode unter `/var/backups/aborodesk/` gesichert. Nach dem Neustart wird `/health` geprüft; bei Fehlern erfolgt ein Code-Rollback. MongoDB wird nicht überschrieben, da sie außerhalb des Anwendungscodes liegt.

Der Update-Dienst schreibt seinen Status nach `/var/lib/aborodesk-updater/status.json`. Das Dashboard zeigt dadurch an, ob die Anwendung aktuell ist, wann ein Update installiert wurde oder ob ein Rollback erfolgt ist.

Kontrolle:

```bash
sudo systemctl list-timers aborodesk-update.timer
sudo journalctl -u aborodesk-update.service -f
sudo systemctl start aborodesk-update.service
```
