import base64
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User

_passwords = PasswordHasher()


class InMemoryRateLimiter:
    """Kleine Schutzschicht für einen einzelnen Prozess.

    Für mehrere Web-Worker muss sie später durch Redis oder ein Gateway ersetzt
    werden; sie verhindert aber bereits Brute-Force- und Kosten-Spitzen im
    lokalen bzw. einzelnen Deployment.
    """

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        requests = self._requests[key]
        while requests and requests[0] <= now - window_seconds:
            requests.popleft()
        if len(requests) >= limit:
            return False
        requests.append(now)
        return True


rate_limiter = InMemoryRateLimiter()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_matches(submitted: str | None, expected: str | None) -> bool:
    return bool(submitted and expected and hmac.compare_digest(submitted, expected))


def hash_password(password: str) -> str:
    return _passwords.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _passwords.verify(hashed, password)
    except Exception:
        return False


def create_session(user_id: int) -> str:
    serializer = URLSafeTimedSerializer(get_settings().secret_key, salt="ki-email-session")
    return serializer.dumps({"user_id": user_id})


def current_user(request: Request, db: Session) -> User | None:
    value = request.cookies.get("ki_email_session")
    if not value:
        return None
    try:
        serializer = URLSafeTimedSerializer(get_settings().secret_key, salt="ki-email-session")
        data = serializer.loads(value, max_age=60 * 60 * 12)
    except BadSignature:
        return None
    return db.get(User, int(data["user_id"]))


def require_user(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Anmeldung erforderlich")
    return user


def require_permission(user: User, permission: str) -> None:
    """Prüft Rechte serverseitig, nicht nur über sichtbare Navigationslinks."""
    if not user.role or not any(item.name == permission for item in user.role.permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Berechtigung fehlt")


def encrypt_secret(value: str) -> str:
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().secret_key.encode()).digest())
    return Fernet(fernet_key).encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().secret_key.encode()).digest())
    return Fernet(fernet_key).decrypt(value.encode()).decode()
