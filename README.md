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

Für Gmail muss `GOOGLE_REDIRECT_URI` exakt mit der in Google Cloud eingetragenen Weiterleitungsadresse übereinstimmen. Standardmäßig ist das lokal:

```text
http://localhost:8000/auth/google/callback
```

Wenn Google `403 access_denied` meldet, muss die Gmail-Adresse im OAuth-Zustimmungsbildschirm als Testnutzer eingetragen werden. Siehe [Gmail-OAuth-Fehlerhilfe](docs/google-oauth-troubleshooting.md).

Der lokale Test verwendet `http://localhost`. Dafür wird HTTPS nur während des lokalen OAuth-Tests ausdrücklich erlaubt. Für einen späteren Betrieb im Internet muss die Anwendung mit HTTPS betrieben werden; die lokale Ausnahme gilt dann nicht.

## Tests

```powershell
pytest -q
```

Die technische Analyse steht in [docs/architecture.md](docs/architecture.md). Bedrock wird später über die modellagnostische Converse-API integriert; Modell-ID und Region bleiben konfigurierbar. CSV/TXT-Credentialimport folgt in Phase 4. Keine echten Zugangsdaten in `.env`, Git, Logs oder Tests eintragen.
