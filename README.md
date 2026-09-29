# KI-Email

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
