from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import parseaddr
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.models import Activity, AuditLog, Company, Contact, Draft, EmailAccount, EmailMessage, EmailReply, Lead, OutgoingEmail, Permission, Role, User, user_email_accounts
from app.policy import approve_draft, send_draft
from app.security import create_session, current_user, decrypt_secret, encrypt_secret, hash_password, require_permission, require_user, verify_password

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _fetch_public_website(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Die Website muss eine gültige http(s)-Adresse sein.")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.startswith("10.") or host.startswith("192.168."):
        raise ValueError("Private oder lokale Adressen sind nicht erlaubt.")
    request = UrlRequest(url, headers={"User-Agent": "AboroSoft-CRM-Research/1.0"})
    with urlopen(request, timeout=12) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            raise ValueError("Die angegebene Quelle ist keine HTML-Webseite.")
        raw = response.read(750_000)
    html = raw.decode("utf-8", errors="ignore")
    text_content = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text_content).strip()


def research_company_background(company_id: int) -> None:
    """Führt die Website-Recherche nach dem Speichern einer Firma aus."""
    from app.bedrock import research_company
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        company = db.get(Company, company_id)
        if not company:
            return
        if not company.website:
            company.research_status = "skipped"
            company.research_error = "Keine Website angegeben."
            db.commit()
            return
        company.research_status = "running"
        company.research_error = ""
        db.commit()
        page_text = _fetch_public_website(company.website)
        result = research_company(company.name, company.website, page_text)
        now = datetime.now(timezone.utc)
        company.industry = result["industry"] or company.industry
        company.source_url = company.website
        company.researched_at = now
        company.research_status = "completed"
        company.research_error = ""
        signals = "\n".join(f"- {item}" for item in result["relevant_signals"] if isinstance(item, str))
        company.notes = f"Automatische KI-Recherche am {now.strftime('%d.%m.%Y %H:%M')} UTC.\n\n{result['summary']}\n\nBeobachtungen:\n{signals}\n\nGesprächshypothese:\n{result['sales_angle']}"
        db.flush()
        for item in result["public_contacts"]:
            if not isinstance(item, dict):
                continue
            email = str(item.get("email", "")).strip().lower()
            if "@" not in email or db.scalar(select(Contact).where(Contact.email == email)):
                continue
            db.add(Contact(company_id=company.id, name=str(item.get("name") or "Öffentlicher Geschäftskontakt")[:200], email=email, role_title=str(item.get("role_title") or "")[:160], source_url=company.website, researched_at=now, notes="Automatisch aus der öffentlichen Website erkannt; vor Kontaktaufnahme prüfen."))
        if result["sales_pitch"]:
            lead = db.scalar(select(Lead).where(Lead.company_id == company.id).order_by(Lead.id))
            if not lead:
                lead = Lead(company_id=company.id, status="neu", score=0)
                db.add(lead)
            lead.sales_pitch = result["sales_pitch"]
            lead.next_action = "KI-Recherche prüfen und LMS-Discovery-Entwurf freigeben"
            lead.notes = "Automatisch aus öffentlicher Website recherchiert; kein automatischer Versand."
        db.commit()
    except Exception as exc:
        db.rollback()
        company = db.get(Company, company_id)
        if company:
            company.research_status = "failed"
            company.research_error = str(exc)[:1000]
            db.commit()
    finally:
        db.close()


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
        with engine.begin() as connection:
            connection.execute(text("INSERT OR IGNORE INTO user_email_accounts (user_id, email_account_id) SELECT id, email_account_id FROM users WHERE email_account_id IS NOT NULL"))
        message_columns = {column["name"] for column in inspect(engine).get_columns("email_messages")}
        for name, definition in {
            "ai_category": "VARCHAR(80)",
            "ai_priority": "VARCHAR(20)",
            "ai_summary": "TEXT",
            "ai_reply_draft": "TEXT",
        }.items():
            if name not in message_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE email_messages ADD COLUMN {name} {definition}"))
        lead_columns = {column["name"] for column in inspect(engine).get_columns("leads")}
        if "sales_pitch" not in lead_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE leads ADD COLUMN sales_pitch TEXT NOT NULL DEFAULT ''"))
        company_columns = {column["name"] for column in inspect(engine).get_columns("companies")}
        for name, definition in {"researched_at": "DATETIME", "research_status": "VARCHAR(30) NOT NULL DEFAULT 'pending'", "research_error": "TEXT NOT NULL DEFAULT ''"}.items():
            if name not in company_columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE companies ADD COLUMN {name} {definition}"))
        contact_columns = {column["name"] for column in inspect(engine).get_columns("contacts")}
        if "researched_at" not in contact_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE contacts ADD COLUMN researched_at DATETIME"))
    with next(get_db()) as db:
        crm_permission = db.scalar(select(Permission).where(Permission.name == "CRM_MANAGE"))
        if not crm_permission:
            crm_permission = Permission(name="CRM_MANAGE")
            db.add(crm_permission)
            db.commit()
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
        if crm_permission not in admin_role.permissions:
            admin_role.permissions.append(crm_permission)
            db.commit()
        if not db.scalar(select(Role).where(Role.name == "user")):
            db.add(Role(name="user"))
            db.commit()
        sales_role = db.scalar(select(Role).where(Role.name == "sales"))
        if not sales_role:
            sales_role = Role(name="sales")
            sales_role.permissions.append(crm_permission)
            db.add(sales_role)
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
    return templates.TemplateResponse(request=request, name="admin.html", context={"user": user, "users": users, "roles": roles, "logs": logs, "accounts": accounts, "message": request.query_params.get("message")})


def sync_account(account: EmailAccount, db: Session) -> int:
    from app.mail import fetch_imap_messages
    from app.bedrock import analyze_email

    imported = 0
    password = decrypt_secret(account.encrypted_password)
    for item in fetch_imap_messages(account.imap_host, account.imap_port, account.username, password):
        if db.scalar(select(EmailMessage).where(EmailMessage.message_id == item["external_id"])):
            continue
        message = EmailMessage(account_id=account.id, message_id=item["external_id"], sender=item["sender"], subject=item["subject"], body_text=item["body"], received_at=item["received_at"])
        try:
            analysis = analyze_email(item["subject"], item["sender"], item["body"])
            message.ai_category = analysis["category"]
            message.ai_priority = analysis["priority"]
            message.ai_summary = analysis["summary"]
            message.ai_reply_draft = analysis["reply_draft"]
        except Exception:
            # Die E-Mail bleibt auch bei einem temporären KI-Fehler erhalten.
            pass
        db.add(message)
        imported += 1
    if imported:
        db.commit()
    return imported


@app.get("/crm", response_class=HTMLResponse)
def crm_dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    companies = db.scalars(select(Company).order_by(Company.name)).all()
    contacts = db.scalars(select(Contact).order_by(Contact.name)).all()
    leads = db.scalars(select(Lead).order_by(Lead.created_at.desc())).all()
    activities = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(20)).all()
    users = db.scalars(select(User).order_by(User.display_name)).all()
    return templates.TemplateResponse(request=request, name="crm.html", context={"user": user, "companies": companies, "contacts": contacts, "leads": leads, "users": users, "activities": activities, "message": request.query_params.get("message")})


@app.post("/crm/companies")
def create_company(background_tasks: BackgroundTasks, request: Request, name: str = Form(...), domain: str = Form(""), industry: str = Form(""), website: str = Form(""), source_url: str = Form(""), notes: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    clean_name = name.strip()
    clean_domain = domain.strip().lower().removeprefix("www.")
    duplicate = db.scalar(select(Company).where((Company.domain == clean_domain) | (Company.name == clean_name)))
    if duplicate:
        return RedirectResponse("/crm?message=Firma+bereits+vorhanden", status_code=303)
    company = Company(name=clean_name, domain=clean_domain, industry=industry.strip(), website=website.strip(), source_url=source_url.strip(), notes=notes.strip(), researched_at=None, research_status="pending")
    db.add(company)
    db.add(AuditLog(action="COMPANY_CREATED", actor_user_id=user.id, details="{}"))
    db.commit()
    if company.website:
        background_tasks.add_task(research_company_background, company.id)
    return RedirectResponse("/crm?message=Firma+gespeichert", status_code=303)


@app.post("/crm/contacts")
def create_contact(request: Request, company_id: int = Form(...), name: str = Form(...), email: str = Form(...), role_title: str = Form(""), phone: str = Form(""), source_url: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    if not db.get(Company, company_id):
        return RedirectResponse("/crm?message=Firma+nicht+gefunden", status_code=303)
    clean_email = email.strip().lower()
    duplicate = db.scalar(select(Contact).where(Contact.email == clean_email))
    if duplicate:
        if duplicate.opt_out:
            return RedirectResponse("/crm?message=Kontakt+ist+gesperrt", status_code=303)
        return RedirectResponse("/crm?message=Kontakt+bereits+vorhanden", status_code=303)
    db.add(Contact(company_id=company_id, name=name.strip(), email=clean_email, role_title=role_title.strip(), phone=phone.strip(), source_url=source_url.strip(), researched_at=datetime.now(timezone.utc) if source_url.strip() else None))
    db.add(AuditLog(action="CONTACT_CREATED", actor_user_id=user.id, details=f'{{"company_id": {company_id}}}'))
    db.commit()
    return RedirectResponse("/crm?message=Kontakt+gespeichert", status_code=303)


@app.post("/crm/companies/{company_id}/research")
def rerun_company_research(company_id: int, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    company = db.get(Company, company_id)
    if not company:
        return RedirectResponse("/crm?message=Firma+nicht+gefunden", status_code=303)
    company.research_status = "pending"
    company.research_error = ""
    db.commit()
    background_tasks.add_task(research_company_background, company.id)
    return RedirectResponse("/crm?message=Recherche+gestartet", status_code=303)


@app.post("/crm/leads")
def create_lead(request: Request, company_id: int = Form(...), contact_id: int | None = Form(None), owner_user_id: int | None = Form(None), status: str = Form("neu"), score: int = Form(0), next_action: str = Form(""), sales_pitch: str = Form(""), notes: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    if not db.get(Company, company_id):
        return RedirectResponse("/crm?message=Firma+nicht+gefunden", status_code=303)
    contact = db.get(Contact, contact_id) if contact_id else None
    if contact and (contact.company_id != company_id or contact.opt_out):
        return RedirectResponse("/crm?message=Kontakt+nicht+verwendbar", status_code=303)
    db.add(Lead(company_id=company_id, contact_id=contact_id, owner_user_id=owner_user_id, status=status, score=max(0, min(score, 100)), next_action=next_action.strip(), sales_pitch=sales_pitch.strip(), notes=notes.strip()))
    db.add(AuditLog(action="LEAD_CREATED", actor_user_id=user.id, details=f'{{"company_id": {company_id}}}'))
    db.commit()
    return RedirectResponse("/crm?message=Lead+gespeichert", status_code=303)


@app.post("/crm/activities")
def create_activity(request: Request, company_id: int | None = Form(None), lead_id: int | None = Form(None), activity_type: str = Form("note"), subject: str = Form(""), body: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db)
    require_permission(user, "CRM_MANAGE")
    if company_id and not db.get(Company, company_id):
        return RedirectResponse("/crm?message=Firma+nicht+gefunden", status_code=303)
    if lead_id and not db.get(Lead, lead_id):
        return RedirectResponse("/crm?message=Lead+nicht+gefunden", status_code=303)
    db.add(Activity(company_id=company_id, lead_id=lead_id, user_id=user.id, activity_type=activity_type.strip(), subject=subject.strip(), body=body.strip()))
    db.add(AuditLog(action="CRM_ACTIVITY_CREATED", actor_user_id=user.id, details="{}"))
    db.commit()
    return RedirectResponse("/crm?message=Aktivität+gespeichert", status_code=303)


@app.get("/compose", response_class=HTMLResponse)
def compose_page(request: Request, reply_to: int | None = None, forward: int | None = None, db: Session = Depends(get_db)):
    user = require_user(request, db)
    accounts = [account for account in user.email_accounts if account.is_active]
    source = db.get(EmailMessage, reply_to or forward) if (reply_to or forward) else None
    if source and source.account_id not in {account.id for account in accounts}:
        source = None
        reply_to = None
        forward = None
    recipient = parseaddr(source.sender)[1] if source and reply_to else ""
    subject = source.subject if source and reply_to else (f"Fwd: {source.subject}" if source else "")
    body = source.ai_reply_draft if source and reply_to else (f"\n\n--- Weitergeleitete Nachricht ---\nVon: {source.sender}\nBetreff: {source.subject}\n\n{source.body_text}" if source else "")
    return templates.TemplateResponse(request=request, name="compose.html", context={"user": user, "accounts": accounts, "source": source, "recipient": recipient, "subject": subject, "body": body, "reply_to": reply_to, "forward": forward})


@app.post("/compose")
async def compose_email(
    request: Request,
    account_id: int = Form(...),
    recipient: str = Form(...),
    cc: str = Form(""),
    bcc: str = Form(""),
    subject: str = Form(""),
    body: str = Form(""),
    html_body: str = Form(""),
    content_type: str = Form("text"),
    in_reply_to: str = Form(""),
    attachments: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    account = next((item for item in user.email_accounts if item.id == account_id and item.is_active), None)
    if not account or not recipient.strip() or not body.strip():
        return RedirectResponse("/compose", status_code=303)
    prepared = []
    for upload in attachments:
        if not upload.filename:
            continue
        content = await upload.read()
        if len(content) > 10 * 1024 * 1024:
            continue
        mime, _ = mimetypes.guess_type(upload.filename)
        maintype, subtype = (mime or "application/octet-stream").split("/", 1)
        prepared.append({"filename": upload.filename, "content": content, "maintype": maintype, "subtype": subtype})
    from app.mail import send_email
    send_email(account.smtp_host, account.smtp_port, account.username, decrypt_secret(account.encrypted_password), account.email_address, recipient.strip(), subject.strip(), body.strip(), in_reply_to.strip() or None, cc.strip(), bcc.strip(), html_body.strip() if content_type == "html" else None, prepared)
    db.add(OutgoingEmail(account_id=account.id, created_by_user_id=user.id, recipient=recipient.strip(), cc=cc.strip(), bcc=bcc.strip(), subject=subject.strip(), text_body=body.strip(), html_body=html_body.strip() if content_type == "html" else None, content_type=content_type, in_reply_to=in_reply_to.strip() or None, status="sent", sent_at=datetime.now(timezone.utc)))
    db.add(AuditLog(action="EMAIL_SENT", actor_user_id=user.id, details=f'{{"account_id": {account.id}}}'))
    db.commit()
    return RedirectResponse("/inbox", status_code=303)


@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    available_accounts = [account for account in user.email_accounts if account.is_active]
    account_id = request.query_params.get("account_id")
    account = next((item for item in available_accounts if account_id and account_id.isdigit() and item.id == int(account_id)), None)
    if not account:
        account = available_accounts[0] if available_accounts else None
    error = None
    imported = 0
    if account:
        try:
            imported = sync_account(account, db)
        except Exception as exception:
            error = f"Postfach konnte nicht abgerufen werden: {type(exception).__name__}"
        messages = db.scalars(select(EmailMessage).where(EmailMessage.account_id == account.id).order_by(EmailMessage.received_at.desc(), EmailMessage.id.desc())).all()
    else:
        messages = []
        error = "Noch kein E-Mail-Konto eingerichtet."
    return templates.TemplateResponse(request=request, name="inbox.html", context={"user": user, "account": account, "accounts": available_accounts, "messages": messages, "error": error, "imported": imported})


@app.get("/inbox/{message_id}", response_class=HTMLResponse)
def read_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    message = db.get(EmailMessage, message_id)
    allowed_account_ids = {account.id for account in user.email_accounts if account.is_active}
    if not message or message.account_id not in allowed_account_ids:
        return RedirectResponse("/inbox", status_code=303)
    message.is_read = True
    db.commit()
    return templates.TemplateResponse(request=request, name="message.html", context={"user": user, "message": message})


@app.post("/inbox/{message_id}/ai")
def ai_assist_message(message_id: int, request: Request, action: str = Form("analyze"), db: Session = Depends(get_db)):
    user = require_user(request, db)
    message = db.get(EmailMessage, message_id)
    allowed_account_ids = {account.id for account in user.email_accounts if account.is_active}
    if not message or message.account_id not in allowed_account_ids:
        return RedirectResponse("/inbox", status_code=303)
    from app.bedrock import analyze_email, assist_email
    if action == "analyze":
        result = analyze_email(message.subject, message.sender, message.body_text)
        message.ai_category = result["category"]
        message.ai_priority = result["priority"]
        message.ai_summary = result["summary"]
        message.ai_reply_draft = result["reply_draft"]
    else:
        message.ai_reply_draft = assist_email(message.subject, message.sender, message.body_text, action, message.ai_reply_draft or "")
    db.add(AuditLog(action="AI_ASSISTANCE_USED", actor_user_id=user.id, details=f'{{"message_id": {message.id}, "action": "{action}"}}'))
    db.commit()
    return RedirectResponse(f"/inbox/{message.id}", status_code=303)


@app.post("/inbox/{message_id}/reply")
def reply_to_message(message_id: int, request: Request, body: str = Form(...), action: str = Form("save"), db: Session = Depends(get_db)):
    user = require_user(request, db)
    message = db.get(EmailMessage, message_id)
    allowed_account_ids = {account.id for account in user.email_accounts if account.is_active}
    if not message or message.account_id not in allowed_account_ids:
        return RedirectResponse("/inbox", status_code=303)
    account = db.get(EmailAccount, message.account_id)
    recipient = parseaddr(message.sender)[1]
    subject = message.subject if message.subject.lower().startswith("re:") else f"Re: {message.subject}"
    reply = EmailReply(message_id=message.id, account_id=account.id, recipient=recipient, subject=subject, body=body.strip(), created_by_user_id=user.id)
    if action == "send":
        if not body.strip() or not recipient:
            return RedirectResponse(f"/inbox/{message.id}", status_code=303)
        from app.mail import send_email
        send_email(account.smtp_host, account.smtp_port, account.username, decrypt_secret(account.encrypted_password), account.email_address, recipient, subject, body.strip(), message.message_id)
        reply.status = "sent"
        reply.sent_at = datetime.now(timezone.utc)
        db.add(AuditLog(action="EMAIL_REPLY_SENT", actor_user_id=user.id, details=f'{{"message_id": {message.id}}}'))
    else:
        db.add(AuditLog(action="EMAIL_REPLY_SAVED", actor_user_id=user.id, details=f'{{"message_id": {message.id}}}'))
    db.add(reply)
    db.commit()
    return RedirectResponse(f"/inbox/{message.id}", status_code=303)


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
    from urllib.parse import quote
    from app.security import encrypt_secret

    normalized_email = email_address.strip().lower()
    account = db.scalar(select(EmailAccount).where(EmailAccount.email_address == normalized_email))
    if account:
        account.account_name = account_name
        account.display_name = display_name
        account.imap_host = imap_host
        account.imap_port = imap_port
        account.smtp_host = smtp_host
        account.smtp_port = smtp_port
        account.username = username
        account.encrypted_password = encrypt_secret(password)
        action = "EMAIL_ACCOUNT_UPDATED"
        message = f"E-Mail-Konto {normalized_email} wurde aktualisiert"
    else:
        account = EmailAccount(account_name=account_name, email_address=normalized_email, display_name=display_name, imap_host=imap_host, imap_port=imap_port, smtp_host=smtp_host, smtp_port=smtp_port, username=username, encrypted_password=encrypt_secret(password))
        db.add(account)
        action = "EMAIL_ACCOUNT_CREATED"
        message = f"E-Mail-Konto {normalized_email} wurde angelegt"
    db.add(AuditLog(action=action, actor_user_id=user.id, details=f'{{"email": "{normalized_email}"}}'))
    db.commit()
    return RedirectResponse(f"/admin?message={quote(message)}", status_code=303)


@app.post("/admin/users")
def create_user(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    email_account_ids: list[int] = Form(...),
    db: Session = Depends(get_db),
):
    """Nur ein Administrator darf neue Benutzer für ein E-Mail-Konto anlegen."""
    admin = require_user(request, db)
    require_permission(admin, "ADMIN_SETTINGS")
    role = db.scalar(select(Role).where(Role.name == "user"))
    accounts = db.scalars(select(EmailAccount).where(EmailAccount.id.in_(email_account_ids))).all()
    if not role or not accounts or len(accounts) != len(set(email_account_ids)):
        return RedirectResponse("/admin?message=Rolle+oder+E-Mail-Konto+nicht+gefunden", status_code=303)
    if db.scalar(select(User).where(User.email == email.lower())):
        return RedirectResponse("/admin?message=E-Mail-Adresse+existiert+bereits", status_code=303)
    user = User(email=email.lower(), display_name=display_name, password_hash=hash_password(password), role_id=role.id, email_account_id=accounts[0].id)
    user.email_accounts.extend(accounts)
    db.add(user)
    db.add(AuditLog(action="USER_CREATED", actor_user_id=admin.id, details=f'{{"email": "{email.lower()}", "account_ids": {sorted({account.id for account in accounts})}}}'))
    db.commit()
    return RedirectResponse("/admin?message=Benutzer+angelegt", status_code=303)


@app.post("/admin/users/{user_id}")
def update_user(
    user_id: int,
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(""),
    email_account_ids: list[int] = Form(...),
    db: Session = Depends(get_db),
):
    admin = require_user(request, db)
    require_permission(admin, "ADMIN_SETTINGS")
    target = db.get(User, user_id)
    accounts = db.scalars(select(EmailAccount).where(EmailAccount.id.in_(email_account_ids))).all()
    normalized_email = email.strip().lower()
    duplicate = db.scalar(select(User).where(User.email == normalized_email, User.id != user_id))
    if not target or not accounts or len(accounts) != len(set(email_account_ids)):
        return RedirectResponse("/admin?message=Benutzer+oder+E-Mail-Konto+nicht+gefunden", status_code=303)
    if duplicate:
        return RedirectResponse("/admin?message=Login-E-Mail+existiert+bereits", status_code=303)
    target.email = normalized_email
    target.display_name = display_name.strip()
    if password:
        target.password_hash = hash_password(password)
    target.email_accounts = accounts
    target.email_account_id = accounts[0].id
    db.add(AuditLog(action="USER_UPDATED", actor_user_id=admin.id, details=f'{{"user_id": {user_id}}}'))
    db.commit()
    return RedirectResponse("/admin?message=Benutzer+aktualisiert", status_code=303)


@app.post("/admin/users/{user_id}/delete")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = require_user(request, db)
    require_permission(admin, "ADMIN_SETTINGS")
    target = db.get(User, user_id)
    if not target:
        return RedirectResponse("/admin?message=Benutzer+nicht+gefunden", status_code=303)
    if target.id == admin.id:
        return RedirectResponse("/admin?message=Du+kannst+dich+nicht+selbst+löschen", status_code=303)
    if target.role.name == "admin" and db.scalar(select(User).join(Role).where(Role.name == "admin").where(User.id != target.id)) is None:
        return RedirectResponse("/admin?message=Der+letzte+Administrator+kann+nicht+gelöscht+werden", status_code=303)
    db.execute(delete(user_email_accounts).where(user_email_accounts.c.user_id == target.id))
    db.add(AuditLog(action="USER_DELETED", actor_user_id=admin.id, details=f'{{"user_id": {user_id}, "email": "{target.email}"}}'))
    db.delete(target)
    db.commit()
    return RedirectResponse("/admin?message=Benutzer+gelöscht", status_code=303)


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
