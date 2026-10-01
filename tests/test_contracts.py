from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.contracts as contracts_module
from app.config import get_settings
from app.db import Base, get_db
from app.main import app
from app.models import Contract, ContractReminder, DashboardPreference, Permission, Role, User
from app.security import create_session


@pytest.fixture
def contract_env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permissions = {name: Permission(name=name) for name in ("CONTRACT_VIEW", "CONTRACT_MANAGE", "CONTRACT_AI")}
        db.add_all([
            User(id=1, email="manager@example.test", display_name="Manager", password_hash="unused",
                 role=Role(name="contract_manager", permissions=list(permissions.values()))),
            User(id=2, email="reader@example.test", display_name="Reader", password_hash="unused",
                 role=Role(name="contract_reader", permissions=[permissions["CONTRACT_VIEW"]])),
            User(id=3, email="none@example.test", display_name="None", password_hash="unused", role=Role(name="no_contracts")),
        ])
        db.commit()

    def database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(get_settings(), "contracts_enabled", True)
    fake_storage = SimpleNamespace(
        upload=lambda *args: {"id": 501},
        download=lambda file_id: ({"name": "Vertrag.txt"}, b"Vertrag"),
        office=lambda file_id: "https://office.example.test/editor",
    )
    monkeypatch.setattr(contracts_module, "contract_storage_client", lambda: fake_storage)
    queued = []
    monkeypatch.setattr(contracts_module, "enqueue", lambda db, kind, payload: queued.append((kind, payload)))
    client = TestClient(app)
    yield SimpleNamespace(client=client, engine=engine, queued=queued)
    client.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def login(env, user_id):
    env.client.cookies.set("ki_email_session", create_session(user_id))


def post(env, path, data=None, files=None):
    return env.client.post(path, data=data or {}, files=files, headers={"Origin": "http://testserver"}, follow_redirects=False)


def contract_form(**changes):
    return {"title": "Cloud-Vertrag", "contract_number": "V-10", "company_id": 0,
            "counterparty": "Beispiel GmbH", "contract_type": "kunde", "status": "aktiv",
            "owner_user_id": 1, "start_date": "2026-01-01", "end_date": "2026-12-31",
            "notice_period_days": 90, "renewal_months": 12, "description": "Test",
            "analysis_text": "Der Vertrag endet am 31. Dezember 2026.", **changes}


def create_contract(env):
    assert post(env, "/contracts", contract_form()).status_code == 303
    with Session(env.engine) as db:
        return db.scalar(select(Contract)).id


def test_permissions_and_disable(contract_env, monkeypatch):
    env = contract_env
    assert env.client.get("/contracts").status_code == 401
    login(env, 3)
    assert env.client.get("/contracts").status_code == 403
    login(env, 1)
    monkeypatch.setattr(get_settings(), "contracts_enabled", False)
    assert env.client.get("/contracts").status_code == 404


def test_create_calculates_deadline_and_reminder(contract_env):
    env = contract_env
    login(env, 1)
    contract_id = create_contract(env)
    with Session(env.engine) as db:
        contract = db.get(Contract, contract_id)
        reminder = db.scalar(select(ContractReminder).where(ContractReminder.contract_id == contract_id))
        assert contract.cancellation_deadline == "2026-10-02"
        assert reminder.due_date == "2026-10-02" and reminder.remind_date == "2026-09-18"
    response = env.client.get(f"/contracts/{contract_id}")
    assert response.status_code == 200 and "Cloud-Vertrag" in response.text


def test_reader_cannot_change_contract(contract_env):
    env = contract_env
    login(env, 1)
    contract_id = create_contract(env)
    login(env, 2)
    assert env.client.get(f"/contracts/{contract_id}").status_code == 200
    assert env.client.get(f"/contracts/{contract_id}/edit").status_code == 403
    assert post(env, f"/contracts/{contract_id}/reminders", {"title": "Prüfen", "due_date": "2026-11-01", "remind_date": "2026-10-01"}).status_code == 403


def test_upload_extracts_text_and_uses_mapping(contract_env):
    env = contract_env
    login(env, 1)
    contract_id = create_contract(env)
    with Session(env.engine) as db:
        contract = db.get(Contract, contract_id)
        contract.analysis_text = ""
        db.commit()
    response = post(env, f"/contracts/{contract_id}/documents", files={"file": ("vertrag.txt", b"Kuendigungsfrist 30 Tage", "text/plain")})
    assert response.status_code == 303
    with Session(env.engine) as db:
        assert "30 Tage" in db.get(Contract, contract_id).analysis_text
    assert env.client.get(f"/contracts/{contract_id}/documents/1/download").content == b"Vertrag"
    assert env.client.get(f"/contracts/{contract_id}/documents/999/download").status_code == 404


def test_ai_is_queued_and_does_not_change_fields(contract_env):
    env = contract_env
    login(env, 1)
    contract_id = create_contract(env)
    response = post(env, f"/contracts/{contract_id}/ai")
    assert response.status_code == 303
    assert env.queued == [("contracts.ai_analysis", {"contract_id": contract_id, "requested_by_user_id": 1})]
    with Session(env.engine) as db:
        contract = db.get(Contract, contract_id)
        assert contract.ai_status == "pending" and contract.end_date == "2026-12-31"
    assert post(env, f"/contracts/{contract_id}/ai").status_code == 303
    assert len(env.queued) == 1


def test_dashboard_shortcuts_are_personal(contract_env):
    env = contract_env
    login(env, 1)
    response = env.client.get("/dashboard")
    assert "Mein Schnellzugriff" in response.text and ">Verträge<" in response.text
    response = post(env, "/dashboard/shortcuts", {"shortcuts": ["contracts", "search"]})
    assert response.status_code == 303
    with Session(env.engine) as db:
        assert db.get(DashboardPreference, 1).shortcuts_json == '["contracts", "search"]'
