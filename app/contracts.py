"""Optionales Modul für Verträge, Fristen, Dokumente und geprüfte KI-Hinweise."""
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
from urllib.parse import quote
import zipfile
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.cloudshare import StorageError, contract_storage_client
from app.config import get_settings
from app.db import get_db
from app.jobs import enqueue
from app.models import AuditLog, Company, Contract, ContractDocument, ContractReminder, User
from app.security import require_permission, require_user

router = APIRouter(prefix="/contracts", tags=["Vertragsverwaltung"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
STATUSES = {"entwurf": "Entwurf", "aktiv": "Aktiv", "gekündigt": "Gekündigt", "beendet": "Beendet", "archiviert": "Archiviert"}
TYPES = {"kunde": "Kundenvertrag", "lieferant": "Lieferantenvertrag", "wartung": "Wartung / Service", "lizenz": "Lizenz", "miete": "Miete", "personal": "Personal", "sonstiges": "Sonstiges"}
OFFICE_EXTENSIONS = {"doc", "docx", "odt", "xls", "xlsx", "ods", "ppt", "pptx", "odp", "csv", "txt", "rtf"}


def _permissions(user):
    return {permission.name for permission in user.role.permissions}


def actor(request, db, manage=False, ai=False):
    if not get_settings().contracts_enabled:
        raise HTTPException(404, "Die Vertragsverwaltung ist deaktiviert.")
    user = require_user(request, db)
    require_permission(user, "CONTRACT_VIEW")
    if manage:
        require_permission(user, "CONTRACT_MANAGE")
    if ai:
        require_permission(user, "CONTRACT_AI")
    return user


def contract_or_404(db, contract_id):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, "Vertrag nicht gefunden.")
    return contract


def parsed_date(value, label, required=False):
    value = value.strip()
    if not value and not required:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(400, f"{label} ist kein gültiges Datum.") from None


def text(value, maximum, label, required=False):
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise HTTPException(400, f"{label} muss {'ausgefüllt sein' if required else f'höchstens {maximum} Zeichen enthalten'}.")
    return value


def _deadline(end_date, notice_days):
    return (date.fromisoformat(end_date) - timedelta(days=notice_days)).isoformat() if end_date else ""


def _audit(db, user, action, contract_id, **details):
    db.add(AuditLog(action=action, actor_user_id=user.id, details=json.dumps({"contract_id": contract_id, **details}, ensure_ascii=False)))


def _storage(operation):
    try:
        return operation(contract_storage_client())
    except StorageError as exc:
        raise HTTPException(502, str(exc)) from None


def _analysis_result(contract):
    try:
        value = json.loads(contract.ai_result_json or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def render(request, name, user, **context):
    permissions = _permissions(user)
    return templates.TemplateResponse(request=request, name=name, context={
        "user": user, "statuses": STATUSES, "types": TYPES,
        "can_manage": "CONTRACT_MANAGE" in permissions,
        "can_ai": "CONTRACT_AI" in permissions,
        "can_crm": "CRM_MANAGE" in permissions,
        "can_helpdesk": "HELPDESK_VIEW" in permissions,
        "can_marketing": "MARKETING_VIEW" in permissions,
        "can_projects": get_settings().projects_enabled and "PROJECT_VIEW" in permissions,
        "can_documents": get_settings().documents_enabled and "DOCUMENTS_VIEW" in permissions,
        "can_contracts": True,
        **context,
    })


def _apply_form(contract, *, title, contract_number, company_id, counterparty, contract_type, status,
                owner_user_id, start_date, end_date, notice_period_days, auto_renew, renewal_months,
                description, analysis_text, db):
    contract.title = text(title, 240, "Titel", required=True)
    contract.contract_number = text(contract_number, 100, "Vertragsnummer")
    contract.company_id = company_id or None
    if contract.company_id and not db.get(Company, contract.company_id):
        raise HTTPException(400, "Die ausgewählte Firma existiert nicht.")
    contract.counterparty = text(counterparty, 240, "Vertragspartner")
    contract.contract_type = contract_type if contract_type in TYPES else "sonstiges"
    contract.status = status if status in STATUSES else "entwurf"
    owner = db.get(User, owner_user_id)
    if not owner or not owner.is_active:
        raise HTTPException(400, "Die verantwortliche Person ist nicht verfügbar.")
    contract.owner_user_id = owner.id
    contract.start_date = parsed_date(start_date, "Vertragsbeginn")
    contract.end_date = parsed_date(end_date, "Vertragsende")
    if contract.start_date and contract.end_date and contract.start_date > contract.end_date:
        raise HTTPException(400, "Das Vertragsende liegt vor dem Vertragsbeginn.")
    contract.notice_period_days = max(0, min(int(notice_period_days), 3650))
    contract.cancellation_deadline = _deadline(contract.end_date, contract.notice_period_days)
    contract.auto_renew = bool(auto_renew)
    contract.renewal_months = max(0, min(int(renewal_months), 120))
    contract.description = text(description, 10000, "Beschreibung")
    contract.analysis_text = text(analysis_text, 50000, "Prüftext")


def _sync_deadline_reminder(db, contract, user_id):
    if not contract.cancellation_deadline:
        return
    title = "Kündigungsfrist prüfen"
    reminder = db.scalar(select(ContractReminder).where(ContractReminder.contract_id == contract.id, ContractReminder.title == title, ContractReminder.completed_at.is_(None)))
    remind_date = (date.fromisoformat(contract.cancellation_deadline) - timedelta(days=14)).isoformat()
    if reminder:
        reminder.due_date, reminder.remind_date = contract.cancellation_deadline, remind_date
        reminder.notification_sent_at = None
    else:
        db.add(ContractReminder(contract_id=contract.id, title=title, due_date=contract.cancellation_deadline,
                                remind_date=remind_date, created_by_user_id=user_id))


@router.get("", response_class=HTMLResponse)
def index(request: Request, q: str = "", status: str = "", db: Session = Depends(get_db)):
    user = actor(request, db)
    statement = select(Contract).order_by(Contract.end_date == "", Contract.end_date, Contract.title)
    if q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(or_(Contract.title.ilike(term), Contract.contract_number.ilike(term), Contract.counterparty.ilike(term)))
    if status in STATUSES:
        statement = statement.where(Contract.status == status)
    contracts = db.scalars(statement).all()
    return render(request, "contracts.html", user, contracts=contracts, query=q, selected_status=status,
                  message=request.query_params.get("message"))


@router.get("/new", response_class=HTMLResponse)
def new_form(request: Request, db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    return render(request, "contract_form.html", user, contract=None,
                  companies=db.scalars(select(Company).order_by(Company.name)).all(),
                  users=db.scalars(select(User).where(User.is_active).order_by(User.display_name)).all())


@router.post("")
def create(request: Request, title: str = Form(...), contract_number: str = Form(""), company_id: int = Form(0),
           counterparty: str = Form(""), contract_type: str = Form("sonstiges"), status: str = Form("entwurf"),
           owner_user_id: int = Form(...), start_date: str = Form(""), end_date: str = Form(""),
           notice_period_days: int = Form(0), auto_renew: str = Form(""), renewal_months: int = Form(0),
           description: str = Form(""), analysis_text: str = Form(""), db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    contract = Contract(title="", owner_user_id=user.id, created_by_user_id=user.id)
    _apply_form(contract, title=title, contract_number=contract_number, company_id=company_id,
                counterparty=counterparty, contract_type=contract_type, status=status,
                owner_user_id=owner_user_id, start_date=start_date, end_date=end_date,
                notice_period_days=notice_period_days, auto_renew=auto_renew,
                renewal_months=renewal_months, description=description, analysis_text=analysis_text, db=db)
    db.add(contract)
    db.flush()
    _sync_deadline_reminder(db, contract, user.id)
    _audit(db, user, "contract.created", contract.id)
    db.commit()
    return RedirectResponse(f"/contracts/{contract.id}?message=Vertrag+angelegt", status_code=303)


@router.get("/{contract_id}", response_class=HTMLResponse)
def detail(contract_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db)
    contract = contract_or_404(db, contract_id)
    documents = db.scalars(select(ContractDocument).where(ContractDocument.contract_id == contract.id).order_by(ContractDocument.created_at.desc())).all()
    reminders = db.scalars(select(ContractReminder).where(ContractReminder.contract_id == contract.id).order_by(ContractReminder.completed_at.is_not(None), ContractReminder.due_date)).all()
    return render(request, "contract_detail.html", user, contract=contract, documents=documents,
                  reminders=reminders, analysis=_analysis_result(contract), office_extensions=OFFICE_EXTENSIONS,
                  message=request.query_params.get("message"), max_mb=get_settings().documents_max_bytes // (1024 * 1024))


@router.get("/{contract_id}/edit", response_class=HTMLResponse)
def edit_form(contract_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    return render(request, "contract_form.html", user, contract=contract_or_404(db, contract_id),
                  companies=db.scalars(select(Company).order_by(Company.name)).all(),
                  users=db.scalars(select(User).where(User.is_active).order_by(User.display_name)).all())


@router.post("/{contract_id}")
def update(contract_id: int, request: Request, revision: int = Form(...), title: str = Form(...),
           contract_number: str = Form(""), company_id: int = Form(0), counterparty: str = Form(""),
           contract_type: str = Form("sonstiges"), status: str = Form("entwurf"), owner_user_id: int = Form(...),
           start_date: str = Form(""), end_date: str = Form(""), notice_period_days: int = Form(0),
           auto_renew: str = Form(""), renewal_months: int = Form(0), description: str = Form(""),
           analysis_text: str = Form(""), db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    contract = contract_or_404(db, contract_id)
    if contract.revision != revision:
        raise HTTPException(409, "Der Vertrag wurde zwischenzeitlich geändert. Bitte neu laden.")
    _apply_form(contract, title=title, contract_number=contract_number, company_id=company_id,
                counterparty=counterparty, contract_type=contract_type, status=status,
                owner_user_id=owner_user_id, start_date=start_date, end_date=end_date,
                notice_period_days=notice_period_days, auto_renew=auto_renew,
                renewal_months=renewal_months, description=description, analysis_text=analysis_text, db=db)
    contract.revision += 1
    _sync_deadline_reminder(db, contract, user.id)
    _audit(db, user, "contract.updated", contract.id, revision=contract.revision)
    db.commit()
    return RedirectResponse(f"/contracts/{contract.id}?message=Änderungen+gespeichert", status_code=303)


@router.post("/{contract_id}/reminders")
def add_reminder(contract_id: int, request: Request, title: str = Form(...), due_date: str = Form(...),
                 remind_date: str = Form(...), db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    contract = contract_or_404(db, contract_id)
    due, remind = parsed_date(due_date, "Fälligkeit", True), parsed_date(remind_date, "Erinnerungsdatum", True)
    if remind > due:
        raise HTTPException(400, "Das Erinnerungsdatum darf nicht nach der Fälligkeit liegen.")
    db.add(ContractReminder(contract_id=contract.id, title=text(title, 240, "Titel", True), due_date=due,
                            remind_date=remind, created_by_user_id=user.id))
    _audit(db, user, "contract.reminder_created", contract.id, due_date=due)
    db.commit()
    return RedirectResponse(f"/contracts/{contract.id}?message=Erinnerung+angelegt", status_code=303)


@router.post("/{contract_id}/reminders/{reminder_id}/complete")
def complete_reminder(contract_id: int, reminder_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    contract_or_404(db, contract_id)
    reminder = db.get(ContractReminder, reminder_id)
    if not reminder or reminder.contract_id != contract_id:
        raise HTTPException(404, "Erinnerung nicht gefunden.")
    reminder.completed_at = datetime.now(timezone.utc)
    _audit(db, user, "contract.reminder_completed", contract_id, reminder_id=reminder.id)
    db.commit()
    return RedirectResponse(f"/contracts/{contract_id}", status_code=303)


def _extract_text(filename, content):
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".rtf"}:
        return content.decode("utf-8", errors="ignore")[:50000]
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
            return " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))[:50000]
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
            return ""
    return ""


@router.post("/{contract_id}/documents")
async def upload_document(contract_id: int, request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    contract = contract_or_404(db, contract_id)
    try:
        content = await file.read(get_settings().documents_max_bytes + 1)
    finally:
        await file.close()
    from starlette.concurrency import run_in_threadpool
    uploaded = await run_in_threadpool(_storage, lambda client: client.upload(file.filename or "", content, file.content_type))
    cloud_id = int(uploaded.get("id", 0))
    if cloud_id <= 0:
        raise HTTPException(502, "CloudShare lieferte keine gültige Datei-ID.")
    db.add(ContractDocument(contract_id=contract.id, cloudshare_file_id=cloud_id,
                            filename=(file.filename or "Datei")[:255], uploaded_by_user_id=user.id))
    extracted = _extract_text(file.filename or "", content)
    if extracted and not contract.analysis_text:
        contract.analysis_text = extracted
        contract.revision += 1
    _audit(db, user, "contract.document_uploaded", contract.id, cloudshare_file_id=cloud_id)
    db.commit()
    return RedirectResponse(f"/contracts/{contract.id}?message=Dokument+hochgeladen", status_code=303)


def _mapped_document(db, contract_id, document_id):
    document = db.get(ContractDocument, document_id)
    if not document or document.contract_id != contract_id:
        raise HTTPException(404, "Vertragsdokument nicht gefunden.")
    return document


@router.get("/{contract_id}/documents/{document_id}/download")
def download_document(contract_id: int, document_id: int, request: Request, db: Session = Depends(get_db)):
    actor(request, db)
    contract_or_404(db, contract_id)
    document = _mapped_document(db, contract_id, document_id)
    info, content = _storage(lambda client: client.download(document.cloudshare_file_id))
    filename = quote(str(info.get("name", document.filename)), safe="")
    return Response(content, media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + filename,
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@router.post("/{contract_id}/documents/{document_id}/office")
def office_document(contract_id: int, document_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db, manage=True)
    document = _mapped_document(db, contract_id, document_id)
    url = _storage(lambda client: client.office(document.cloudshare_file_id))
    _audit(db, user, "contract.document_office", contract_id, cloudshare_file_id=document.cloudshare_file_id)
    db.commit()
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.post("/{contract_id}/ai")
def request_ai(contract_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db, ai=True)
    contract = contract_or_404(db, contract_id)
    if not contract.analysis_text.strip():
        raise HTTPException(400, "Für die KI-Prüfung wird ein auslesbares Dokument oder ein Prüftext benötigt.")
    if contract.ai_status in {"pending", "running"}:
        return RedirectResponse(f"/contracts/{contract.id}?message=Die+KI-Prüfung+läuft+bereits", status_code=303)
    contract.ai_status, contract.ai_error = "pending", ""
    _audit(db, user, "contract.ai_requested", contract.id)
    db.commit()
    enqueue(db, "contracts.ai_analysis", {"contract_id": contract.id, "requested_by_user_id": user.id})
    return RedirectResponse(f"/contracts/{contract.id}?message=KI-Prüfung+gestartet", status_code=303)
