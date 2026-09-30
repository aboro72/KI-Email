# KI-Email

## Entwicklungsstatus und Roadmap

Der laufende Umsetzungsstand, die Reihenfolge der nächsten Ausbaustufen und optionale Erweiterungen stehen in [docs/fortschritt-und-roadmap.md](docs/fortschritt-und-roadmap.md).

Modularer, KI-gestützter Multi-Account-E-Mail-Arbeitsplatz. Phase 1 liefert ein ausführbares FastAPI-Grundgerüst mit Benutzerverwaltung, Rollen/Rechten, sicherem Secret-Speicher, Dashboard und technisch erzwungener Human-in-the-Loop-Versandfreigabe.

## Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Danach: http://127.0.0.1:8000

## Administrator anlegen

Am einfachsten in `.env` setzen:

```text
ADMIN_EMAIL=deine-adresse@example.com
ADMIN_PASSWORD=ein-langes-einmaliges-passwort
```

Alternativ interaktiv:

```powershell
py -3 -m app.cli create-admin
```

Der Fortschritt wird in [STATUS.md](STATUS.md) fortgeschrieben.

## Tests

```powershell
pytest -q
```

Die technische Analyse steht in [docs/architecture.md](docs/architecture.md). Bedrock wird später über die modellagnostische Converse-API integriert; Modell-ID und Region bleiben konfigurierbar. CSV/TXT-Credentialimport folgt in Phase 4. Keine echten Zugangsdaten in `.env`, Git, Logs oder Tests eintragen.

## Linux-Installation

- [ISPConfig3-Installation](deploy/ispconfig3/installation.md) mit [Installationsskript](deploy/ispconfig3/install.sh)
- [Einzelserver-Installation](deploy/single-server/installation.md) mit [Installationsskript](deploy/single-server/install.sh)

Die Skripte kopieren keine lokale Datenbank und keine API-Key-Datei. Zugangsdaten werden erst auf dem Zielserver über eine geschützte Environment-Datei bzw. ein Secret-Management hinterlegt.

## MongoDB-Migration

Die Anwendung kann mit einer MongoDB-URI betrieben werden. Für die einmalige Übernahme des bestehenden SQLite-Bestands steht [migrate_sqlite_to_mongo.py](scripts/migrate_sqlite_to_mongo.py) bereit. Die SQLite-Datei wird dabei nur gelesen und bleibt als Backup erhalten.

Der optionale [automatische Update-Dienst](deploy/update.sh) prüft per systemd-Timer alle 20 Minuten einen Git-Branch und rollt bei einem fehlgeschlagenen Healthcheck automatisch auf den vorherigen Anwendungscode zurück.
