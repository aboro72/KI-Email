"""Kurze, modulbezogene Sperre vor dem Laden eines frischen Datenbankstands."""
from pathlib import Path
import os
import threading
import time

from fastapi import HTTPException

from app.config import get_settings
from app.db import SessionLocal

_lock = threading.Lock()


def project_db():
    if not get_settings().projects_enabled:
        raise HTTPException(404, "Projektplanung ist deaktiviert")
    # SQLite und Mongo-Snapshot-Adapter: erst sperren, dann Sitzung laden.
    # Unabhängig von der KI-Sperre; kein Warten auf laufende Qwen-Anfragen.
    with _lock:
        with Path(get_settings().project_lock_file).open("a+b") as handle:
            if os.name == "nt":
                import msvcrt
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                while True:
                    handle.seek(0)
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(.05)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                with SessionLocal() as db:
                    yield db
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
