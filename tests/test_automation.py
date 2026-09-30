import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.automation import emit_event, register_action
from app.db import Base
from app.models import AutomationRule


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_automation_rule_matches_and_records_run(db_session):
    calls = []
    register_action("tests.record", lambda db, event, config: calls.append(event) or {"ok": True})
    db_session.add(AutomationRule(name="Neue Mail", module="tests", event_name="email.received", conditions_json=json.dumps({"priority": "hoch"}), actions_json=json.dumps(["tests.record"])))
    db_session.commit()

    runs = emit_event(db_session, "email.received", {"priority": "hoch", "message_id": 3})

    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert calls == [{"priority": "hoch", "message_id": 3}]


def test_automation_rule_ignores_non_matching_event(db_session):
    db_session.add(AutomationRule(name="Nur hoch", module="tests", event_name="email.received", conditions_json='{"priority":"hoch"}', actions_json='[]'))
    db_session.commit()
    assert emit_event(db_session, "email.received", {"priority": "normal"}) == []
