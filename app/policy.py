from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AuditLog, Draft


def approve_draft(db: Session, draft: Draft, user_id: int) -> Draft:
    draft.approved_by_user_id = user_id
    draft.approved_at = datetime.now(timezone.utc)
    db.add(AuditLog(action="USER_APPROVAL", actor_user_id=user_id, details=f'{{"draft_id": {draft.id}}}'))
    db.commit()
    db.refresh(draft)
    return draft


def assert_send_allowed(draft: Draft) -> None:
    # Diese Prüfung sitzt serverseitig und darf nicht nur im Frontend existieren.
    # Dadurch kann weder ein Prompt noch ein manipuliertes UI den Versand umgehen.
    if draft.generated_by_ai and (draft.approved_by_user_id is None or draft.approved_at is None):
        raise HTTPException(status_code=409, detail="KI-Entwurf muss vor dem Versand ausdrücklich freigegeben werden")


def send_draft(db: Session, draft: Draft, actor_user_id: int) -> None:
    assert_send_allowed(draft)
    db.add(AuditLog(action="EMAIL_SEND", actor_user_id=actor_user_id, details=f'{{"draft_id": {draft.id}}}'))
    db.commit()
