"""Kleiner systemd-Worker für die durable Job-Warteschlange."""

from __future__ import annotations

import os
import time
import logging

from sqlalchemy import select

from app.db import Base, SessionLocal, engine, initialize_persistence
from app.jobs import run_pending
from app.models import BackgroundJob
import app.job_handlers  # noqa: F401 - registriert die Modul-Handler


def main() -> None:
    interval = max(2, int(os.getenv("WORKER_INTERVAL_SECONDS", "10")))
    Base.metadata.create_all(engine)
    initialize_persistence()
    logging.basicConfig(level=logging.INFO)
    # Dieser Einzelserver betreibt genau einen Worker. Beim Dienstneustart
    # stammen running-Jobs vom unterbrochenen Vorgänger.
    with SessionLocal() as db:
        for job in db.scalars(select(BackgroundJob).where(BackgroundJob.status == "running")):
            job.status = "queued"
            job.locked_at = None
        db.commit()
    while True:
        try:
            with SessionLocal() as db:
                jobs = run_pending(db, limit=10)
                for job in jobs:
                    logging.info("Job %s (%s): %s", job.id, job.job_type, job.status)
        except Exception as exc:
            logging.error("Worker-Zyklus fehlgeschlagen: %s", type(exc).__name__)
        time.sleep(interval)


if __name__ == "__main__":
    main()
