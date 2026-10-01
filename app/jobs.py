"""Datenbankbasierte Job-Warteschlange für den Einzelserver und kleine Installationen."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import BackgroundJob, Notification, Task

Handler = Callable[[Session, Mapping[str, object]], None]
_HANDLERS: dict[str, Handler] = {}


def register_handler(job_type: str, handler: Handler) -> None:
    if not job_type or not callable(handler):
        raise ValueError("Ein Job-Handler benötigt einen Typ und eine aufrufbare Funktion.")
    _HANDLERS[job_type] = handler


def enqueue(db: Session, job_type: str, payload: Mapping[str, object], *, max_attempts: int = 3) -> BackgroundJob:
    job = BackgroundJob(job_type=job_type, payload_json=json.dumps(dict(payload), default=str), max_attempts=max(1, max_attempts))
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def recover_stale_jobs(db: Session, *, stale_after_seconds: int = 900) -> int:
    """Gibt nach einem Worker-Abbruch verwaiste Jobs kontrolliert wieder frei."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=max(1, stale_after_seconds))
    retryable = db.execute(
        update(BackgroundJob)
        .where(BackgroundJob.status == "running", BackgroundJob.locked_at.is_not(None), BackgroundJob.locked_at < cutoff, BackgroundJob.attempts < BackgroundJob.max_attempts)
        .values(status="queued", locked_at=None, available_at=now, error="Worker-Neustart erkannt; Aufgabe wird erneut versucht.")
    ).rowcount
    exhausted = db.execute(
        update(BackgroundJob)
        .where(BackgroundJob.status == "running", BackgroundJob.locked_at.is_not(None), BackgroundJob.locked_at < cutoff, BackgroundJob.attempts >= BackgroundJob.max_attempts)
        .values(status="failed", finished_at=now, error="Worker-Neustart erkannt; maximale Anzahl Versuche erreicht.")
    ).rowcount
    if retryable or exhausted:
        db.commit()
    return retryable + exhausted


def _claim_next_job(db: Session, now: datetime) -> BackgroundJob | None:
    """Beansprucht genau einen Job per bedingtem Update, auch bei mehreren Workern."""
    candidate_ids = db.scalars(
        select(BackgroundJob.id)
        .where(BackgroundJob.status == "queued", BackgroundJob.available_at <= now)
        .order_by(BackgroundJob.created_at)
        .limit(10)
    ).all()
    for job_id in candidate_ids:
        claimed = db.execute(
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id, BackgroundJob.status == "queued")
            .values(status="running", locked_at=now, attempts=BackgroundJob.attempts + 1)
        ).rowcount
        if claimed:
            db.commit()
            return db.get(BackgroundJob, job_id)
    return None


def run_pending(db: Session, *, limit: int = 10, stale_after_seconds: int = 900) -> list[BackgroundJob]:
    """Verarbeitet eine begrenzte Anzahl Jobs; ein Worker kann diese Funktion zyklisch aufrufen."""
    now = datetime.now(timezone.utc)
    # Erinnerungen werden idempotent erzeugt: pro Aufgabe genau eine fällige Meldung.
    due_tasks = db.scalars(select(Task).where(Task.status == "open", Task.due_at.is_not(None), Task.due_at <= now, Task.reminder_sent_at.is_(None))).all()
    for task in due_tasks:
        recipient_id = task.assigned_to_user_id or task.created_by_user_id
        db.add(Notification(user_id=recipient_id, title="Aufgabe fällig", message=task.title, url="/tasks"))
        task.reminder_sent_at = now
    if due_tasks:
        db.commit()
    recover_stale_jobs(db, stale_after_seconds=stale_after_seconds)
    jobs = []
    for _ in range(limit):
        job = _claim_next_job(db, datetime.now(timezone.utc))
        if job is None:
            break
        jobs.append(job)
        try:
            handler = _HANDLERS.get(job.job_type)
            if handler is None:
                raise ValueError(f"Unbekannter Job-Typ: {job.job_type}")
            handler(db, json.loads(job.payload_json or "{}"))
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            job.error = ""
        except Exception as exc:
            job.error = str(exc)[:1000]
            job.status = "failed" if job.attempts >= job.max_attempts else "queued"
        db.commit()
    return jobs
