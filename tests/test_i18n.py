import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Permission, Role, SystemSetting, User
from app.security import create_session


@pytest.fixture
def language_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permission = Permission(name="ADMIN_SETTINGS")
        db.add_all([
            User(id=1, email="admin@example.test", display_name="Admin", password_hash="unused",
                 role=Role(name="admin", permissions=[permission])),
            User(id=2, email="user@example.test", display_name="User", password_hash="unused",
                 role=Role(name="user")),
        ])
        db.commit()

    def database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = database
    client = TestClient(app)
    yield client, engine
    client.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_global_language_requires_admin_and_is_served(language_env):
    client, engine = language_env
    client.cookies.set("ki_email_session", create_session(2))
    assert client.post("/admin/language", data={"language": "en"}, headers={"Origin": "http://testserver"}).status_code == 403
    client.cookies.set("ki_email_session", create_session(1))
    response = client.post("/admin/language", data={"language": "en"}, headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert response.status_code == 303
    with Session(engine) as db:
        assert db.get(SystemSetting, "ui_language").value == "en"
    response = client.get("/ui-language.js")
    assert response.status_code == 200 and '"en"' in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_invalid_language_is_rejected(language_env):
    client, _ = language_env
    client.cookies.set("ki_email_session", create_session(1))
    response = client.post("/admin/language", data={"language": "fr"}, headers={"Origin": "http://testserver"})
    assert response.status_code == 400


def test_pages_load_global_translation_assets(language_env):
    client, _ = language_env
    client.cookies.set("ki_email_session", create_session(1))
    html = client.get("/admin").text
    assert "/ui-language.js" in html and "/static/i18n.js" in html
    assert "Global language" in html
