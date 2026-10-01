"""Textadapter für Nova; vorhandene KI-Aufgaben behalten ihr Ausgabeformat."""

from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import math
import os
import threading
import time

import httpx

from app.config import get_settings

_request_lock = threading.Lock()


@contextmanager
def sequential_requests(lock_file):
    """Gemeinsame Dateisperre für Webapp, Worker und weitere App-Prozesse."""
    with _request_lock:
        with Path(lock_file).open("a+b") as handle:
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
                        time.sleep(0.1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def retry_delay(value):
    try:
        delay = float(value)
    except (ValueError, TypeError):
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            delay = 5
    return max(5, delay) if math.isfinite(delay) else 5


class NovaClient:
    def converse(self, *, modelId, system, messages, inferenceConfig):
        settings = get_settings()
        if not settings.nova_api_key:
            raise RuntimeError("Nova-API-Key fehlt")
        if settings.nova_model not in {"local", "bedrock"}:
            raise RuntimeError("Nova-Backend muss local oder bedrock sein")
        if not settings.nova_base_url.startswith("https://"):
            raise RuntimeError("Nova benötigt eine HTTPS-Adresse")
        chat = [{"role": "system", "content": "\n".join(item["text"] for item in system)}]
        chat.extend({"role": item["role"], "content": "\n".join(block["text"] for block in item["content"])} for item in messages)
        payload = {
            "model": settings.nova_model,
            "messages": chat,
            "stream": False,
            "max_tokens": inferenceConfig.get("maxTokens", 1024),
            "temperature": inferenceConfig.get("temperature", 0.2),
        }
        # Die Sperre bleibt auch während Retry-After aktiv: kein anderer
        # App-Prozess startet zwischen zwei Versuchen eine parallele Anfrage.
        with sequential_requests(settings.nova_request_lock_file):
            for attempt in range(max(0, min(3, settings.nova_max_retries)) + 1):
                try:
                    response = httpx.post(
                settings.nova_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.nova_api_key},
                json=payload,
                timeout=httpx.Timeout(max(180, settings.nova_request_timeout)),
                follow_redirects=False,
                    )
                except httpx.TimeoutException:
                    raise RuntimeError("Nova-Zeitlimit erreicht; Anfrage später erneut starten") from None
                except httpx.HTTPError:
                    raise RuntimeError("Nova-Verbindung fehlgeschlagen") from None
                if response.status_code != 429 or attempt >= max(0, min(3, settings.nova_max_retries)):
                    break
                delay = retry_delay(response.headers.get("Retry-After"))
                if delay > 60:
                    break  # Nicht früher wiederholen als vom Server erlaubt.
                time.sleep(delay)
        if response.status_code != 200:
            reasons = {401: "Zugang abgelehnt", 429: "Kapazität belegt; später erneut versuchen", 502: "Backendfehler", 503: "API deaktiviert"}
            raise RuntimeError(f"Nova: {reasons.get(response.status_code, 'Anfrage fehlgeschlagen')} (HTTP {response.status_code})")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise RuntimeError("Nova lieferte ein ungültiges Antwortformat") from None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Nova lieferte keinen Antworttext")
        return {"output": {"message": {"content": [{"text": content}]}}}
