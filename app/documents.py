"""Optional file module, deliberately limited to one configured CloudShare folder."""
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.cloudshare import StorageError, storage_client
from app.config import get_settings
from app.db import get_db
from app.models import AuditLog
from app.security import require_permission, require_user

router = APIRouter(prefix="/documents", tags=["Dateiablage"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def actor(request, db, write=False):
    if not get_settings().documents_enabled:
        raise HTTPException(404, "Die Dateiablage ist deaktiviert.")
    user = require_user(request, db)
    require_permission(user, "DOCUMENTS_VIEW")
    if write:
        require_permission(user, "DOCUMENTS_UPLOAD")
    return user


def storage_call(operation):
    try:
        return operation(storage_client())
    except StorageError as exc:
        raise HTTPException(502, str(exc)) from None


@router.get("")
def index(request: Request, db: Session = Depends(get_db)):
    user = actor(request, db)
    error = None
    try:
        files = storage_client().files()
    except StorageError as exc:
        files, error = [], str(exc)
    permissions = {p.name for p in user.role.permissions}
    return templates.TemplateResponse(request=request, name="documents.html", context={
        "user": user, "files": files, "error": error,
        "can_upload": "DOCUMENTS_UPLOAD" in permissions,
        "can_edit": "DOCUMENTS_EDIT" in permissions,
        "max_mb": get_settings().documents_max_bytes // (1024 * 1024),
    })


@router.post("/upload")
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = actor(request, db, write=True)
    try:
        content = await file.read(get_settings().documents_max_bytes + 1)
    finally:
        await file.close()
    # Use a worker thread for blocking HTTPS I/O, not the web event loop.
    from starlette.concurrency import run_in_threadpool
    uploaded = await run_in_threadpool(storage_call, lambda client: client.upload(file.filename or "", content, file.content_type))
    db.add(AuditLog(actor_user_id=user.id, action="document.upload", details=f"CloudShare file_id={uploaded.get('id')}"))
    db.commit()
    return RedirectResponse("/documents", status_code=303)


@router.get("/{file_id}/download")
def download(file_id: int, request: Request, db: Session = Depends(get_db)):
    actor(request, db)
    info, content = storage_call(lambda client: client.download(file_id))
    filename = quote(str(info.get("name", "Datei")), safe="")
    return Response(content, media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + filename,
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@router.post("/{file_id}/office")
def office(file_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db)
    require_permission(user, "DOCUMENTS_EDIT")
    url = storage_call(lambda client: client.office(file_id))
    db.add(AuditLog(actor_user_id=user.id, action="document.office", details=f"CloudShare file_id={file_id}"))
    db.commit()
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.get('/{file_id}/versions')
def versions(file_id: int, request: Request, db: Session = Depends(get_db)):
    user = actor(request, db)
    info = storage_call(lambda client: client.file(file_id))
    return templates.TemplateResponse(request=request, name='document_versions.html', context={
        'file': info, 'user': user, 'can_edit': any(p.name=='DOCUMENTS_EDIT' for p in user.role.permissions),
    })


@router.post('/{file_id}/restore')
def restore(file_id: int, request: Request, version_id: int = Form(...),
            expected_count: int = Form(...), db: Session = Depends(get_db)):
    user = actor(request, db)
    require_permission(user, 'DOCUMENTS_EDIT')
    storage_call(lambda client: client.restore(file_id, version_id, expected_count))
    db.add(AuditLog(actor_user_id=user.id, action='document.restore',
                    details=f'CloudShare file_id={file_id}, version_id={version_id}'))
    db.commit()
    return RedirectResponse(f'/documents/{file_id}/versions', status_code=303)
