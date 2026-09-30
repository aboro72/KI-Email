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

Repository auf den Server übertragen oder klonen und in das Projektverzeichnis wechseln:

```bash
git clone <REPOSITORY-URL> /opt/aborodesk-source
cd /opt/aborodesk-source
chmod +x deploy/ispconfig3/install.sh
sudo SOURCE_DIR="$PWD" SERVICE_USER=webXXX SERVICE_GROUP=clientY APP_PORT=8001 deploy/ispconfig3/install.sh
```

`webXXX` und `clientY` müssen durch den Benutzer und die Gruppe der betreffenden ISPConfig-Website ersetzt werden. Wenn ein separater Systembenutzer verwendet werden soll, muss dieser vorher existieren und Zugriff auf die Installationsverzeichnisse erhalten. Falls Benutzer und Gruppe identisch sind, kann `SERVICE_GROUP` entfallen.

Das Skript:

- installiert Python, venv, pip und rsync
- kopiert den Quellcode ohne Git-Metadaten, `.env`, Datenbank und lokale Secrets
- erstellt `/opt/aborodesk/.venv`
- legt den systemd-Dienst `aborodesk.service` an
- legt die geschützte Environment-Datei unter `/etc/aborodesk/aborodesk.env` an
- startet den Dienst auf `127.0.0.1:8001`

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
