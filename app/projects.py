"""Eigenständiges Projektmodul mit projektbezogenen Rollen und Kanban."""
from datetime import date, datetime, timezone
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditLog, Notification, Project, ProjectCard, ProjectComment, ProjectMember, User
from app.project_db import project_db
from app.security import require_permission, require_user

router = APIRouter(prefix="/projects", tags=["Projektplanung"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
COLUMNS = {"backlog": "Backlog", "planned": "Geplant", "doing": "In Arbeit", "review": "Prüfung", "done": "Erledigt"}
TYPES = {"story": "User Story", "bug": "Fehler", "task": "Aufgabe"}
PRIORITIES = {"low": "Niedrig", "normal": "Normal", "high": "Hoch", "critical": "Kritisch"}


def has_permission(user, name):
    return any(p.name == name for p in user.role.permissions)


def actor(request, db):
    if not get_settings().projects_enabled:
        raise HTTPException(404, "Projektplanung ist deaktiviert")
    user = require_user(request, db)
    require_permission(user, "PROJECT_VIEW")
    return user


def can_manage(user, project):
    return project.leader_user_id == user.id or has_permission(user, "ADMIN_SETTINGS")


def project_access(db, user, project_id, manage=False, write=False):
    project = db.get(Project, project_id)
    if not project or not (can_manage(user, project) or db.get(ProjectMember, (project_id, user.id))):
        raise HTTPException(404, "Projekt nicht gefunden oder nicht freigegeben")
    if manage and not can_manage(user, project):
        raise HTTPException(403, "Nur die Projektleitung oder Administration darf diese Einstellung ändern")
    if write and project.archived:
        raise HTTPException(409, "Das Projekt ist archiviert und schreibgeschützt")
    return project


def team(db, project):
    ids = set(db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project.id))) | {project.leader_user_id}
    return db.scalars(select(User).where(User.id.in_(ids)).order_by(User.display_name)).all()


def eligible_users(db):
    return [u for u in db.scalars(select(User).where(User.is_active).order_by(User.display_name)).all() if has_permission(u, "PROJECT_VIEW")]


def eligible_user(db, user_id):
    user = db.get(User, user_id)
    if not user or not user.is_active or not has_permission(user, "PROJECT_VIEW"):
        raise HTTPException(400, "Die Person muss aktiv sein und das Modulrecht PROJECT_VIEW besitzen")
    return user


def audit(db, user, action, project_id, **details):
    db.add(AuditLog(action=action, actor_user_id=user.id, details=json.dumps({"project_id": project_id, **details}, ensure_ascii=False)))


def notify(db, actor_user, recipient_id, title, message, url):
    if recipient_id and recipient_id != actor_user.id:
        db.add(Notification(user_id=recipient_id, title=title[:240], message=message, url=url))


def redirect(project_id=None):
    return RedirectResponse(f"/projects/{project_id}" if project_id else "/projects", status_code=303)


def render(request, name, **context):
    return templates.TemplateResponse(request=request, name=name, context={"columns": COLUMNS, "types": TYPES, "priorities": PRIORITIES, **context})


def validate_text(value, maximum, label, required=False):
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise HTTPException(400, f"{label}: bitte {'1–' if required else 'höchstens '}{maximum} Zeichen eingeben")
    return value


def check_revision(card, revision):
    if revision != card.revision:
        raise HTTPException(409, "Dieser Eintrag wurde inzwischen geändert. Bitte Seite neu laden, damit keine Änderungen überschrieben werden.")


def check_wip(db, project, status, previous=None):
    if status not in COLUMNS:
        raise HTTPException(400, "Ungültige Kanban-Spalte")
    if status == "doing" and previous != "doing" and project.wip_limit:
        count = db.scalar(select(func.count()).select_from(ProjectCard).where(ProjectCard.project_id == project.id, ProjectCard.status == "doing")) or 0
        if count >= project.wip_limit:
            raise HTTPException(409, "Das WIP-Limit für ‚In Arbeit‘ ist erreicht. Zuerst eine laufende Karte abschließen oder verschieben.")


def card_access(db, user, project_id, card_id, write=False):
    project = project_access(db, user, project_id, write=write)
    card = db.get(ProjectCard, card_id)
    if not card or card.project_id != project.id:
        raise HTTPException(404, "Karte nicht in diesem Projekt gefunden")
    return project, card


@router.get("", response_class=HTMLResponse)
def overview(request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    statement = select(Project)
    if not has_permission(user, "ADMIN_SETTINGS"):
        memberships = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        statement = statement.where(or_(Project.leader_user_id == user.id, Project.id.in_(memberships)))
    projects = db.scalars(statement.order_by(Project.archived, Project.created_at.desc())).all()
    counts = {}
    for project in projects:
        cards = db.scalars(select(ProjectCard).where(ProjectCard.project_id == project.id)).all()
        counts[project.id] = {"total": len(cards), "done": sum(c.status == "done" for c in cards)}
    assigned = db.scalars(select(ProjectCard).where(ProjectCard.project_id.in_([p.id for p in projects if not p.archived]), ProjectCard.assignee_user_id == user.id, ProjectCard.status != "done").order_by(ProjectCard.due_date == "", ProjectCard.due_date, ProjectCard.id).limit(50)).all()
    return render(request, "projects.html", user=user, projects=projects, counts=counts, assigned=assigned, project_names={p.id: p.name for p in projects}, can_create=has_permission(user, "PROJECT_CREATE"))


@router.get("/new", response_class=HTMLResponse)
def new_project(request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    require_permission(user, "PROJECT_CREATE")
    return render(request, "project_form.html", user=user, project=None, users=eligible_users(db))


@router.post("")
def create_project(request: Request, name: str = Form(...), leader_user_id: int = Form(...), description: str = Form(""), member_ids: list[int] = Form([]), wip_limit: int = Form(3), db: Session = Depends(project_db)):
    user = actor(request, db)
    require_permission(user, "PROJECT_CREATE")
    eligible_user(db, leader_user_id)
    for uid in set(member_ids):
        eligible_user(db, uid)
    if not 0 <= wip_limit <= 100:
        raise HTTPException(400, "WIP-Limit muss zwischen 0 und 100 liegen")
    project = Project(name=validate_text(name, 200, "Projektname", True), description=validate_text(description, 20000, "Beschreibung"), leader_user_id=leader_user_id, created_by_user_id=user.id, wip_limit=wip_limit)
    db.add(project)
    db.flush()
    for uid in set(member_ids) - {leader_user_id}:
        db.add(ProjectMember(project_id=project.id, user_id=uid))
    audit(db, user, "PROJECT_CREATED", project.id, leader_user_id=leader_user_id)
    for uid in set(member_ids) | {leader_user_id}:
        notify(db, user, uid, "Neues Projekt: " + project.name, "Du wurdest dem Projektteam zugeordnet.", f"/projects/{project.id}")
    db.commit()
    # Wer ein fremdes Projekt anlegt, erhält nicht automatisch Teamzugriff.
    return redirect(project.id if can_manage(user, project) or user.id in member_ids else None)


@router.get("/{project_id}", response_class=HTMLResponse)
def board(project_id: int, request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id)
    cards = db.scalars(select(ProjectCard).where(ProjectCard.project_id == project_id).order_by(ProjectCard.position, ProjectCard.id)).all()
    mine = request.query_params.get("mine") == "1"
    query = request.query_params.get("q", "").strip().lower()
    filtered = [c for c in cards if (not mine or c.assignee_user_id == user.id) and (not query or query in (c.title + " " + c.description).lower())]
    return render(request, "project_board.html", user=user, project=project, team=team(db, project), cards_by_column={key: [c for c in filtered if c.status == key] for key in COLUMNS}, counts={key: sum(c.status == key for c in cards) for key in COLUMNS}, mine=mine, query=request.query_params.get("q", ""), can_manage=can_manage(user, project), total=len(cards), done=sum(c.status == "done" for c in cards))


@router.get("/{project_id}/settings", response_class=HTMLResponse)
def settings(project_id: int, request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, manage=True)
    return render(request, "project_form.html", user=user, project=project, users=eligible_users(db), team=team(db, project))


@router.post("/{project_id}/settings")
def update_project(project_id: int, request: Request, revision: int = Form(...), name: str = Form(...), leader_user_id: int = Form(...), description: str = Form(""), wip_limit: int = Form(3), db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, manage=True, write=True)
    check_revision(project, revision)
    eligible_user(db, leader_user_id)
    if not 0 <= wip_limit <= 100:
        raise HTTPException(400, "WIP-Limit muss zwischen 0 und 100 liegen")
    project.name = validate_text(name, 200, "Projektname", True)
    project.description = validate_text(description, 20000, "Beschreibung")
    previous = project.leader_user_id
    if previous != leader_user_id and not db.get(ProjectMember, (project.id, previous)):
        db.add(ProjectMember(project_id=project.id, user_id=previous))
    project.leader_user_id = leader_user_id
    project.wip_limit = wip_limit
    project.revision += 1
    audit(db, user, "PROJECT_UPDATED", project.id, previous_leader=previous, leader_user_id=leader_user_id)
    if previous != leader_user_id:
        notify(db, user, leader_user_id, "Projektleitung übernommen", project.name, f"/projects/{project.id}")
    db.commit()
    return redirect(project.id)


@router.post("/{project_id}/members")
def add_member(project_id: int, request: Request, user_id: int = Form(...), db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, manage=True, write=True)
    eligible_user(db, user_id)
    if user_id != project.leader_user_id and not db.get(ProjectMember, (project_id, user_id)):
        db.add(ProjectMember(project_id=project_id, user_id=user_id))
        audit(db, user, "PROJECT_MEMBER_ADDED", project_id, user_id=user_id)
        project.revision += 1
        notify(db, user, user_id, "Zum Projekt hinzugefügt", project.name, f"/projects/{project_id}")
        db.commit()
    return RedirectResponse(f"/projects/{project_id}/settings", status_code=303)


@router.post("/{project_id}/members/{user_id}/remove")
def remove_member(project_id: int, user_id: int, request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, manage=True, write=True)
    if project.leader_user_id == user_id:
        raise HTTPException(400, "Projektleitung zuerst an eine andere Person übergeben")
    member = db.get(ProjectMember, (project_id, user_id))
    if member:
        for card in db.scalars(select(ProjectCard).where(ProjectCard.project_id == project_id, ProjectCard.assignee_user_id == user_id)).all():
            card.assignee_user_id = None
            card.revision += 1
            card.updated_at = datetime.now(timezone.utc)
        db.delete(member)
        project.revision += 1
        audit(db, user, "PROJECT_MEMBER_REMOVED", project_id, user_id=user_id)
        db.commit()
    return RedirectResponse(f"/projects/{project_id}/settings", status_code=303)


@router.post("/{project_id}/archive")
def archive_project(project_id: int, request: Request, revision: int = Form(...), archived: bool = Form(...), db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, manage=True)
    check_revision(project, revision)
    project.archived = archived
    project.revision += 1
    audit(db, user, "PROJECT_ARCHIVED" if archived else "PROJECT_REOPENED", project_id)
    db.commit()
    return redirect(project_id)


@router.get("/{project_id}/cards/new", response_class=HTMLResponse)
def new_card(project_id: int, request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, write=True)
    return render(request, "project_card.html", user=user, project=project, card=None, team=team(db, project), comments=[])


def card_values(db, project, title, description, acceptance_criteria, card_type, status, priority, assignee_user_id, due_date, story_points, previous=None):
    check_wip(db, project, status, previous)
    if card_type not in TYPES or priority not in PRIORITIES:
        raise HTTPException(400, "Ungültiger Aufgabentyp oder Priorität")
    try:
        assignee = int(assignee_user_id) if assignee_user_id else None
        points = int(story_points) if story_points else None
        if points is not None and not 0 <= points <= 100:
            raise ValueError()
        if due_date:
            if date.fromisoformat(due_date).isoformat() != due_date:
                raise ValueError()
    except ValueError:
        raise HTTPException(400, "Bitte gültige Person, Datum und Story Points (0–100) eingeben")
    if assignee is not None:
        eligible_user(db, assignee)
        if assignee not in {u.id for u in team(db, project)}:
            raise HTTPException(400, "Zuständige Person gehört nicht zum Projektteam")
    return dict(title=validate_text(title, 240, "Titel", True), description=validate_text(description, 30000, "Beschreibung"), acceptance_criteria=validate_text(acceptance_criteria, 20000, "Abnahmekriterien"), card_type=card_type, status=status, priority=priority, assignee_user_id=assignee, due_date=due_date, story_points=points)


@router.post("/{project_id}/cards")
def create_card(project_id: int, request: Request, title: str = Form(...), description: str = Form(""), acceptance_criteria: str = Form(""), card_type: str = Form("task"), status: str = Form("backlog"), priority: str = Form("normal"), assignee_user_id: str = Form(""), due_date: str = Form(""), story_points: str = Form(""), db: Session = Depends(project_db)):
    user = actor(request, db)
    project = project_access(db, user, project_id, write=True)
    values = card_values(db, project, title, description, acceptance_criteria, card_type, status, priority, assignee_user_id, due_date, story_points)
    position = (db.scalar(select(func.max(ProjectCard.position)).where(ProjectCard.project_id == project_id, ProjectCard.status == status)) or 0) + 1
    card = ProjectCard(project_id=project_id, created_by_user_id=user.id, position=position, **values)
    db.add(card)
    db.flush()
    audit(db, user, "PROJECT_CARD_CREATED", project_id, card_id=card.id)
    notify(db, user, card.assignee_user_id, "Projektkarte zugewiesen", card.title, f"/projects/{project_id}/cards/{card.id}")
    db.commit()
    return redirect(project_id)


@router.get("/{project_id}/cards/{card_id}", response_class=HTMLResponse)
def show_card(project_id: int, card_id: int, request: Request, db: Session = Depends(project_db)):
    user = actor(request, db)
    project, card = card_access(db, user, project_id, card_id)
    comments = db.scalars(select(ProjectComment).where(ProjectComment.card_id == card.id).order_by(ProjectComment.created_at, ProjectComment.id)).all()
    return render(request, "project_card.html", user=user, project=project, card=card, team=team(db, project), comments=comments)


@router.post("/{project_id}/cards/{card_id}")
def update_card(project_id: int, card_id: int, request: Request, revision: int = Form(...), title: str = Form(...), description: str = Form(""), acceptance_criteria: str = Form(""), card_type: str = Form("task"), status: str = Form("backlog"), priority: str = Form("normal"), assignee_user_id: str = Form(""), due_date: str = Form(""), story_points: str = Form(""), db: Session = Depends(project_db)):
    user = actor(request, db)
    project, card = card_access(db, user, project_id, card_id, write=True)
    check_revision(card, revision)
    previous_assignee = card.assignee_user_id
    values = card_values(db, project, title, description, acceptance_criteria, card_type, status, priority, assignee_user_id, due_date, story_points, card.status)
    if card.status != status:
        card.position = (db.scalar(select(func.max(ProjectCard.position)).where(ProjectCard.project_id == project_id, ProjectCard.status == status)) or 0) + 1
    for key, value in values.items():
        setattr(card, key, value)
    card.revision += 1
    card.updated_at = datetime.now(timezone.utc)
    audit(db, user, "PROJECT_CARD_UPDATED", project_id, card_id=card.id)
    if previous_assignee != card.assignee_user_id:
        notify(db, user, card.assignee_user_id, "Projektkarte zugewiesen", card.title, f"/projects/{project_id}/cards/{card.id}")
    db.commit()
    return redirect(project_id)


@router.post("/{project_id}/cards/{card_id}/move")
def move_card(project_id: int, card_id: int, request: Request, status: str = Form(...), revision: int = Form(...), db: Session = Depends(project_db)):
    user = actor(request, db)
    project, card = card_access(db, user, project_id, card_id, write=True)
    check_revision(card, revision)
    check_wip(db, project, status, card.status)
    old = card.status
    card.status = status
    card.position = (db.scalar(select(func.max(ProjectCard.position)).where(ProjectCard.project_id == project_id, ProjectCard.status == status)) or 0) + 1
    card.revision += 1
    card.updated_at = datetime.now(timezone.utc)
    audit(db, user, "PROJECT_CARD_MOVED", project_id, card_id=card.id, previous=old, status=status)
    db.commit()
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"status": card.status, "revision": card.revision})
    return redirect(project_id)


@router.post("/{project_id}/cards/{card_id}/comments")
def add_comment(project_id: int, card_id: int, request: Request, content: str = Form(...), db: Session = Depends(project_db)):
    user = actor(request, db)
    project, card = card_access(db, user, project_id, card_id, write=True)
    db.add(ProjectComment(card_id=card.id, author_user_id=user.id, content=validate_text(content, 10000, "Kommentar", True)))
    audit(db, user, "PROJECT_COMMENT_ADDED", project_id, card_id=card.id)
    for uid in {card.assignee_user_id, project.leader_user_id} - {None}:
        notify(db, user, uid, "Neuer Kommentar zur Projektkarte", card.title, f"/projects/{project_id}/cards/{card.id}")
    db.commit()
    return RedirectResponse(f"/projects/{project_id}/cards/{card_id}", status_code=303)
