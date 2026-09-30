"""Kleiner systemd-Worker für die durable Job-Warteschlange."""

from __future__ import annotations

import os
import time

from app.db import Base, SessionLocal, engine, initialize_persistence
from app.jobs import run_pending


def main() -> None:
    interval = max(2, int(os.getenv("WORKER_INTERVAL_SECONDS", "10")))
    Base.metadata.create_all(engine)
    initialize_persistence()
    while True:
        with SessionLocal() as db:
            run_pending(db, limit=10)
        time.sleep(interval)


if __name__ == "__main__":
    main()
