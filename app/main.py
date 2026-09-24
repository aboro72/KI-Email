from contextlib import asynccontextmanager
import json
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import AuditLog, Draft, EmailAccount, EmailMessage, GoogleOAuthConfig, Permission, Role, User
from app.policy import approve_draft, send_draft
from app.security import create_session, current_user, decrypt_secret, encrypt_secret, hash_password, require_permission, require_user, verify_password

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def enable_local_google_oauth() -> None:
    """Erlaubt HTTP nur für lokale OAuth-Tests; Produktion muss HTTPS nutzen."""
    redirect_uri = get_settings().google_redirect_uri.lower()
    if redirect_uri.startswith("http://localhost") or redirect_uri.startswith("http://127.0.0.1"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Beim Start werden nur die Tabellen und die vorkonfigurierte Ersteinrichtung
    # vorbereitet. E-Mail-Versand oder KI-Aufgaben werden hier nicht ausgeführt.
    Base.metadata.create_all(engine)
    # Kleine Entwicklungs-Migration: vorhandene SQLite-Datenbanken bekommen
    # die neue Zuordnung Benutzer -> E-Mail-Konto, ohne Daten zu verlieren.
    if engine.dialect.name == "sqlite":
        columns = {column["name"] for column in inspect(engine).get_columns("users")}
        if "email_account_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN email_account_id INTEGER"))
        account_columns = {column["name"] for column in inspect(engine).get_columns("email_accounts")}
        if "oauth_email" not in account_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE email_accounts ADD COLUMN oauth_email VARCHAR(320)"))
    with next(get_db()) as db:
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        if not admin_role:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.flush()
            for name in ("AI_GENERATE", "EMAIL_SEND", "ADMIN_SETTINGS"):
                permission = Permission(name=name)
                db.add(permission)
                admin_role.permissions.append(permission)
            db.commit()
        if not db.scalar(select(Role).where(Role.name == "user")):
            db.add(Role(name="user"))
            db.commit()
        if not db.scalar(select(User).where(User.email == get_settings().admin_email.lower())):
            db.add(User(email=get_settings().admin_email.lower(), display_name="Administrator", password_hash=hash_password(get_settings().admin_password), role_id=admin_role.id))
            db.commit()
    yield


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)


@app.exception_handler(HTTPException)
async def browser_auth_handler(request: Request, exception: HTTPException):
    """Browser-Benutzer landen bei fehlender Sitzung verständlich auf /login."""
    if exception.status_code == 401 and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/login", status_code=303)
    return JSONResponse(status_code=exception.status_code, content={"detail": exception.detail})
# Diese Route stellt die CSS-Datei bereit. Ohne dieses Mounting würde die Seite
# funktionieren, aber ohne Gestaltung ausgeliefert werden.
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/health")
def health():
    # Ein kleiner Endpunkt für Docker, Monitoring und den schnellen Funktionstest.
    return {"status": "ok", "service": get_settings().app_name}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="index.html", context={"user": current_user(request, db)})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Ungültige Zugangsdaten"}, status_code=401)
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("ki_email_session", create_session(user.id), httponly=True, secure=get_settings().session_cookie_secure, samesite="lax", max_age=43200)
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("ki_email_session")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    drafts = db.scalars(select(Draft).order_by(Draft.created_at.desc())).all()
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(8)).all()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "drafts": drafts, "logs": logs})


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Geschützte Systemübersicht für Administratoren."""
    user = require_user(request, db)
    require_permission(user, "ADMIN_SETTINGS")
    users = db.scalars(select(User).order_by(User.email)).all()
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)).all()
    accounts = db.scalars(select(EmailAccount).order_by(EmailAccount.email_address)).all()
    google_configured = db.scalar(select(GoogleOAuthConfig)) is not None
    return templates.TemplateResponse(request=request, name="admin.html", context={"user": user, "users": users, "roles": roles, "logs": logs, "accounts": accounts, "google_configured": google_configured, "message": request.query_params.get("message")})


@app.post("/admin/google/upload")
async def upload_google_config(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Liest eine Google-OAuth-JSON nur im Speicher und speichert sie verschlüsselt."""
    import json
    from app.security import encrypt_secret

    user = require_user(request, db)
    require_permission(user, "ADMIN_SETTINGS")
    if not file.filename or not file.filename.lower().endswith(".json"):
        return RedirectResponse("/admin?message=Bitte+eine+JSON-Datei+auswählen", status_code=303)
    raw = await file.read()
    if len(raw) > 256 * 1024:
        return RedirectResponse("/admin?message=Die+JSON-Datei+ist+zu+groß", status_code=303)
    try:
        document = json.loads(raw.decode("utf-8"))
        client = document.get("web") or document.get("installed")
        required = ("client_id", "client_secret", "auth_uri", "token_uri")
        if not isinstance(client, dict) or any(not client.get(key) for key in required):
            raise ValueError("OAuth-Felder fehlen")
        safe_config = {key: client[key] for key in (*required, "redirect_uris") if key in client}
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError):
        return RedirectResponse("/admin?message=Keine+gültige+Google-OAuth-JSON", status_code=303)
    existing = db.scalar(select(GoogleOAuthConfig))
    encrypted = encrypt_secret(json.dumps(safe_config))
    if existing:
        existing.encrypted_client_config = encrypted
    else:
        db.add(GoogleOAuthConfig(encrypted_client_config=encrypted))
    db.add(AuditLog(action="GOOGLE_OAUTH_CONFIGURED", actor_user_id=user.id, details="{}"))
    db.commit()
    return RedirectResponse("/admin?message=Google-OAuth-Datei+erfolgreich+eingelesen", status_code=303)


@app.get("/auth/google/start")
def google_start(request: Request, db: Session = Depends(get_db)):
    """Startet den Google-OAuth-Login für den angemeldeten Benutzer."""
    from google_auth_oauthlib.flow import Flow
    from app.gmail import SCOPES
    enable_local_google_oauth()
    user = require_user(request, db)
    config = db.scalar(select(GoogleOAuthConfig))
    if not config:
        return RedirectResponse("/admin?message=Bitte+zuerst+die+Google-JSON+einlesen", status_code=303)
    client_config = json.loads(decrypt_secret(config.encrypted_client_config))
    redirect_uri = get_settings().google_redirect_uri
    # PKCE schützt den OAuth-Code. Der Verifier wird signiert im State
    # mitgeführt und beim Rücksprung wieder eingesetzt.
    flow = Flow.from_client_config({"web": client_config}, scopes=SCOPES, redirect_uri=redirect_uri, autogenerate_code_verifier=True)
    serializer = __import__("itsdangerous").URLSafeTimedSerializer(get_settings().secret_key, salt="google-oauth-state")
    state = serializer.dumps({"user_id": user.id, "nonce": secrets.token_urlsafe(16), "code_verifier": flow.code_verifier})
    authorization_url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state)
    return RedirectResponse(authorization_url, status_code=307)


@app.get("/auth/google/callback", name="google_callback")
def google_callback(request: Request, code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    """Speichert das Google-Token verschlüsselt und legt das Gmail-Konto an."""
    from google_auth_oauthlib.flow import Flow
    from app.gmail import SCOPES
    from itsdangerous import BadSignature, URLSafeTimedSerializer
    enable_local_google_oauth()
    from urllib.parse import quote
    if not code or not state:
        return HTMLResponse("<h1>Google-Anmeldung abgebrochen</h1><p>Bitte den Vorgang über das Admin-Dashboard neu starten.</p>", status_code=400)
    try:
        state_data = URLSafeTimedSerializer(get_settings().secret_key, salt="google-oauth-state").loads(state, max_age=600)
    except BadSignature:
        return HTMLResponse("<h1>Ungültige Google-Anmeldung</h1><p>Der Sicherheitscode ist abgelaufen. Bitte den Vorgang neu starten.</p>", status_code=400)
    user = db.get(User, int(state_data["user_id"]))
    config = db.scalar(select(GoogleOAuthConfig))
    if not user or not config:
        return HTMLResponse("<h1>Google-Konfiguration fehlt</h1><p>Bitte zuerst die Google-JSON im Admin-Bereich einlesen.</p>", status_code=400)
    client_config = json.loads(decrypt_secret(config.encrypted_client_config))
    flow = Flow.from_client_config({"web": client_config}, scopes=SCOPES, redirect_uri=get_settings().google_redirect_uri, code_verifier=state_data.get("code_verifier"))
    try:
        # Die komplette Callback-URL verwenden. Die OAuth-Bibliothek setzt
        # dadurch den beim Start verwendeten Redirect-URI korrekt in den
        # Token-Austausch ein.
        flow.fetch_token(authorization_response=str(request.url))
        service = __import__("googleapiclient.discovery", fromlist=["build"]).build("gmail", "v1", credentials=flow.credentials, cache_discovery=False)
        gmail_address = service.users().getProfile(userId="me").execute()["emailAddress"]
        token_json = flow.credentials.to_json()
    except Exception as error:
        # Ein OAuth-Code ist nur einmal und nur kurze Zeit gültig. Häufige
        # Ursachen sind ein Doppelklick, ein Neuladen der Callback-Seite oder
        # eine alte Google-Seite aus einem vorherigen Testlauf.
        safe_error = str(error).replace("<", "&lt;").replace(">", "&gt;")[:300]
        return HTMLResponse(f"<h1>Google-Verbindung fehlgeschlagen</h1><p>Fehler: {type(error).__name__}</p><p>Google meldet: {safe_error}</p><p>Bitte zurück zum Admin-Dashboard gehen und die Anmeldung neu starten. Die Google-Callback-Seite darf nicht neu geladen werden.</p>", status_code=400)
    account = db.scalar(select(EmailAccount).where(EmailAccount.email_address == gmail_address.lower()))
    if not account:
        account = EmailAccount(account_name=f"Gmail {gmail_address}", email_address=gmail_address.lower(), oauth_email=gmail_address, provider="gmail_oauth", display_name=gmail_address, imap_host="imap.gmail.com", imap_port=993, smtp_host="smtp.gmail.com", smtp_port=587, username=gmail_address, encrypted_password=encrypt_secret(token_json))
        db.add(account)
        db.flush()
    else:
        account.encrypted_password = encrypt_secret(token_json)
        account.oauth_email = gmail_address
        account.provider = "gmail_oauth"
    if not user.email_account_id:
        user.email_account_id = account.id
    db.add(AuditLog(action="GOOGLE_ACCOUNT_CONNECTED", actor_user_id=user.id, details="{}"))
    db.commit()
    response = RedirectResponse("/inbox", status_code=303)
    # Der OAuth-Callback kann auf localhost zurückkommen, auch wenn der Start
    # über eine andere lokale Schreibweise erfolgte. Session erneut setzen.
    response.set_cookie("ki_email_session", create_session(user.id), httponly=True, secure=get_settings().session_cookie_secure, samesite="lax", max_age=43200)
    return response


@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request, db: Session = Depends(get_db)):
    """Zeigt die neuesten Gmail-Nachrichten des angemeldeten Benutzers."""
    user = require_user(request, db)
    account = user.email_account or db.scalar(select(EmailAccount).where(EmailAccount.provider == "gmail_oauth"))
    messages = []
    error = None
    if account:
        try:
            from app.gmail import message_summary, service_from_token
            service, credentials = service_from_token(decrypt_secret(account.encrypted_password))
            result = service.users().messages().list(userId="me", maxResults=25, labelIds=["INBOX"]).execute()
            for item in result.get("messages", []):
                detail = service.users().messages().get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
                messages.append(message_summary(detail))
            if credentials.to_json() != decrypt_secret(account.encrypted_password):
                account.encrypted_password = encrypt_secret(credentials.to_json())
                db.commit()
        except Exception as exception:
            error = f"Gmail konnte nicht geladen werden: {type(exception).__name__}"
    else:
        error = "Noch kein Gmail-Konto verbunden."
    return templates.TemplateResponse(request=request, name="inbox.html", context={"user": user, "account": account, "messages": messages, "error": error})


@app.get("/inbox/{message_id}", response_class=HTMLResponse)
def read_message(message_id: str, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    account = user.email_account or db.scalar(select(EmailAccount).where(EmailAccount.provider == "gmail_oauth"))
    if not account:
        return RedirectResponse("/inbox", status_code=303)
    from app.gmail import message_summary, service_from_token
    service, _ = service_from_token(decrypt_secret(account.encrypted_password))
    message = message_summary(service.users().messages().get(userId="me", id=message_id, format="full").execute())
    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    return templates.TemplateResponse(request=request, name="message.html", context={"user": user, "message": message})


@app.post("/inbox/{message_id}/trash")
def trash_message(message_id: str, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    account = user.email_account or db.scalar(select(EmailAccount).where(EmailAccount.provider == "gmail_oauth"))
    if account:
        from app.gmail import service_from_token
        service, _ = service_from_token(decrypt_secret(account.encrypted_password))
        service.users().messages().trash(userId="me", id=message_id).execute()
    return RedirectResponse("/inbox", status_code=303)


@app.post("/admin/email-accounts/{account_id}/test")
def test_email_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    """Testet IMAP und SMTP, ohne eine Nachricht zu senden."""
    from urllib.parse import quote
    from app.mail import test_imap_connection, test_smtp_connection
    from app.security import decrypt_secret

    user = require_user(request, db)
    require_permission(user, "ADMIN_SETTINGS")
    account = db.get(EmailAccount, account_id)
    if not account:
        return RedirectResponse("/admin?message=Konto+nicht+gefunden", status_code=303)
    try:
        password = decrypt_secret(account.encrypted_password)
        test_imap_connection(account.imap_host, account.imap_port, account.username, password)
        test_smtp_connection(account.smtp_host, account.smtp_port, account.username, password)
        message = f"Verbindung erfolgreich: {account.email_address}"
    except Exception as error:
        # Die konkrete Fehlermeldung hilft dem Administrator. Das Passwort
        # wird niemals in diese Meldung aufgenommen oder geloggt.
        message = f"Verbindung fehlgeschlagen: {type(error).__name__}"
    return RedirectResponse(f"/admin?message={quote(message)}", status_code=303)


@app.post("/admin/email-accounts")
def create_email_account(
    request: Request,
    account_name: str = Form(...),
    email_address: str = Form(...),
    display_name: str = Form(...),
    imap_host: str = Form(...),
    imap_port: int = Form(993),
    smtp_host: str = Form(...),
    smtp_port: int = Form(587),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Speichert ein IMAP/SMTP-Konto; das Passwort verlässt den Server nie im Klartext."""
    user = require_user(request, db)
    require_permission(user, "ADMIN_SETTINGS")
    from app.security import encrypt_secret
    account = EmailAccount(account_name=account_name, email_address=email_address.lower(), display_name=display_name, imap_host=imap_host, imap_port=imap_port, smtp_host=smtp_host, smtp_port=smtp_port, username=username, encrypted_password=encrypt_secret(password))
    db.add(account)
    db.add(AuditLog(action="EMAIL_ACCOUNT_CREATED", actor_user_id=user.id, details=f'{{"email": "{email_address.lower()}"}}'))
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/users")
def create_user(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    email_account_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Nur ein Administrator darf neue Benutzer für ein E-Mail-Konto anlegen."""
    admin = require_user(request, db)
    require_permission(admin, "ADMIN_SETTINGS")
    role = db.scalar(select(Role).where(Role.name == "user"))
    account = db.get(EmailAccount, email_account_id)
    if not role or not account:
        return RedirectResponse("/admin?message=Rolle+oder+E-Mail-Konto+nicht+gefunden", status_code=303)
    if db.scalar(select(User).where(User.email == email.lower())):
        return RedirectResponse("/admin?message=E-Mail-Adresse+existiert+bereits", status_code=303)
    db.add(User(email=email.lower(), display_name=display_name, password_hash=hash_password(password), role_id=role.id, email_account_id=account.id))
    db.add(AuditLog(action="USER_CREATED", actor_user_id=admin.id, details=f'{{"email": "{email.lower()}", "account_id": {account.id}}}'))
    db.commit()
    return RedirectResponse("/admin?message=Benutzer+angelegt", status_code=303)


@app.post("/drafts/{draft_id}/approve")
def approve(draft_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    draft = db.get(Draft, draft_id)
    if draft:
        approve_draft(db, draft, user.id)
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/drafts/{draft_id}/send")
def send(draft_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    draft = db.get(Draft, draft_id)
    if draft:
        send_draft(db, draft, user.id)
    return RedirectResponse("/dashboard", status_code=303)
