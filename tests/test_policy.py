from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models import Draft
from app.policy import assert_send_allowed


def test_ai_draft_cannot_send_without_user_approval():
    draft = Draft(subject="Test", body="Antwort", generated_by_ai=True)
    with pytest.raises(HTTPException) as error:
        assert_send_allowed(draft)
    assert error.value.status_code == 409


def test_ai_draft_can_send_after_explicit_approval():
    draft = Draft(subject="Test", body="Antwort", generated_by_ai=True, approved_by_user_id=7, approved_at=datetime.now(timezone.utc))
    assert_send_allowed(draft)
