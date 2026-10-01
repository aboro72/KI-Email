from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base
from app.main import app
from app.models import AuditLog, Notification, Permission, Project, ProjectCard, ProjectMember, Role, User
from app.project_db import project_db
from app.security import create_session


@pytest.fixture
def project_env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permissions = {name: Permission(name=name) for name in ['PROJECT_VIEW', 'PROJECT_CREATE', 'ADMIN_SETTINGS']}
        member = Role(name='project_member', permissions=[permissions['PROJECT_VIEW']])
        creator = Role(name='project_creator', permissions=[permissions['PROJECT_VIEW'], permissions['PROJECT_CREATE']])
        admin = Role(name='admin', permissions=list(permissions.values()))
        outsider = Role(name='no_module')
        users = [User(id=1, email='alice@example.test', display_name='Alice', password_hash='test', role=creator), User(id=2, email='bob@example.test', display_name='Bob', password_hash='test', role=member), User(id=3, email='eve@example.test', display_name='Eve', password_hash='test', role=creator), User(id=4, email='admin@example.test', display_name='Admin', password_hash='test', role=admin), User(id=5, email='none@example.test', display_name='No module', password_hash='test', role=outsider), User(id=6, email='inactive@example.test', display_name='Inactive', password_hash='test', role=member, is_active=False)]
        db.add_all(users)
        db.flush()
        db.add_all([Project(id=1, name='Projekt A', leader_user_id=1, created_by_user_id=1, wip_limit=1), Project(id=2, name='Projekt B', leader_user_id=2, created_by_user_id=1), Project(id=3, name='Privates Projekt', leader_user_id=3, created_by_user_id=3)])
        db.flush()
        db.add_all([ProjectMember(project_id=1, user_id=2), ProjectMember(project_id=2, user_id=1)])
        db.commit()
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[project_db] = database
    client = TestClient(app)
    def login(uid):
        client.cookies.set('ki_email_session', create_session(uid))
    def post(path, data=None, **kwargs):
        return client.post(path, data=data or {}, headers={'Origin': 'http://testserver', **kwargs.pop('headers', {})}, follow_redirects=False, **kwargs)
    env = SimpleNamespace(client=client, login=login, post=post, engine=engine)
    yield env
    client.close()
    app.dependency_overrides.pop(project_db, None)
    engine.dispose()


def card_form(**kwargs):
    return {'title': 'Kundenportal entwickeln', 'description': 'Als Kunde möchte ich …', 'acceptance_criteria': 'Tests erfolgreich', 'card_type': 'story', 'status': 'backlog', 'priority': 'high', 'assignee_user_id': '2', 'story_points': '5', 'due_date': '2026-10-31', **kwargs}


def add_card(env, **kwargs):
    assert env.post('/projects/1/cards', card_form(**kwargs)).status_code == 303
    with Session(env.engine) as db:
        card = db.scalars(select(ProjectCard).order_by(ProjectCard.id.desc())).first()
        return card.id


def test_project_scoped_roles_and_visibility(project_env):
    env = project_env
    env.login(1)
    html = env.client.get('/projects').text
    assert 'Projekt A' in html and 'Projekt B' in html and 'Privates Projekt' not in html
    assert env.client.get('/projects/1/settings').status_code == 200
    assert env.client.get('/projects/2/settings').status_code == 403
    assert env.client.get('/projects/3').status_code == 404
    env.login(2)
    assert env.client.get('/projects/1/settings').status_code == 403
    assert env.client.get('/projects/2/settings').status_code == 200


def test_module_permission_and_disabled_feature(project_env, monkeypatch):
    env = project_env
    assert env.client.get('/projects').status_code == 401
    env.login(5)
    assert env.client.get('/projects').status_code == 403
    env.login(1)
    monkeypatch.setattr(get_settings(), 'projects_enabled', False)
    assert env.client.get('/projects').status_code == 404


def test_create_multiple_projects_with_different_leaders(project_env):
    env = project_env
    env.login(1)
    for leader in [1, 2]:
        assert env.post('/projects', {'name': f'Neues Projekt {leader}', 'leader_user_id': leader, 'member_ids': [1, 2], 'wip_limit': 2}).status_code == 303
    with Session(env.engine) as db:
        projects = db.scalars(select(Project).where(Project.id > 3)).all()
        assert len(projects) == 2
        assert [p.leader_user_id for p in projects] == [1, 2]
        assert db.get(ProjectMember, (projects[1].id, 1)) is not None
    env.login(2)
    assert env.post('/projects', {'name': 'Verboten', 'leader_user_id': 2}).status_code == 403


def test_creation_validates_users_and_name(project_env):
    env = project_env
    env.login(1)
    for leader in [5, 6, 999]:
        assert env.post('/projects', {'name': 'Projekt', 'leader_user_id': leader}).status_code == 400
    assert env.post('/projects', {'name': ' ', 'leader_user_id': 1}).status_code == 400


def test_card_fields_comments_and_notification(project_env):
    env = project_env
    env.login(1)
    cid = add_card(env)
    with Session(env.engine) as db:
        card = db.get(ProjectCard, cid)
        assert card.story_points == 5 and card.assignee_user_id == 2
        assert card.acceptance_criteria == 'Tests erfolgreich'
        assert db.scalar(select(Notification).where(Notification.user_id == 2)).url.endswith(f'/cards/{cid}')
    env.login(2)
    assert env.post(f'/projects/1/cards/{cid}/comments', {'content': '<script>test</script>'}).status_code == 303
    html = env.client.get(f'/projects/1/cards/{cid}').text
    assert '&lt;script&gt;test&lt;/script&gt;' in html and '<script>test</script>' not in html


def test_move_revision_and_wip_limit(project_env):
    env = project_env
    env.login(1)
    first, second = add_card(env), add_card(env)
    assert env.post(f'/projects/1/cards/{first}/move', {'status': 'doing', 'revision': 1}).status_code == 303
    assert env.post(f'/projects/1/cards/{second}/move', {'status': 'doing', 'revision': 1}).status_code == 409
    assert env.post(f'/projects/1/cards/{first}/move', {'status': 'done', 'revision': 1}).status_code == 409
    assert env.post(f'/projects/1/cards/{first}/move', {'status': 'done', 'revision': 2}, headers={'Accept': 'application/json'}).json()['revision'] == 3
    assert env.post(f'/projects/1/cards/{second}/move', {'status': 'doing', 'revision': 1}).status_code == 303


def test_cross_project_card_and_assignee_protection(project_env):
    env = project_env
    env.login(1)
    cid = add_card(env)
    assert env.client.get(f'/projects/2/cards/{cid}').status_code == 404
    assert env.post(f'/projects/2/cards/{cid}/move', {'status': 'done', 'revision': 1}).status_code == 404
    assert env.post('/projects/1/cards', card_form(assignee_user_id='3')).status_code == 400
    env.login(3)
    assert env.post(f'/projects/1/cards/{cid}/move', {'status': 'done', 'revision': 1}).status_code == 404


@pytest.mark.parametrize('changes', [{'story_points': '-1'}, {'story_points': 'x'}, {'due_date': '2026-02-30'}, {'status': 'not-real'}, {'card_type': 'not-real'}, {'priority': 'not-real'}, {'title': ' '}])
def test_card_validation(project_env, changes):
    env = project_env
    env.login(1)
    assert env.post('/projects/1/cards', card_form(**changes)).status_code == 400


def test_remove_member_only_affects_one_project(project_env):
    env = project_env
    env.login(1)
    cid = add_card(env)
    assert env.post('/projects/1/members/1/remove').status_code == 400
    assert env.post('/projects/1/members/2/remove').status_code == 303
    with Session(env.engine) as db:
        assert db.get(ProjectCard, cid).assignee_user_id is None
        assert db.get(ProjectMember, (2, 1)) is not None
        assert db.get(Project, 2).leader_user_id == 2
    env.login(2)
    assert env.client.get('/projects/1').status_code == 404
    assert env.client.get('/projects/2').status_code == 200


def test_leadership_handover_keeps_old_leader_as_member(project_env):
    env = project_env
    env.login(1)
    assert env.post('/projects/1/settings', {'name': 'Projekt A', 'description': '', 'leader_user_id': 2, 'revision': 1, 'wip_limit': 3}).status_code == 303
    assert env.client.get('/projects/1/settings').status_code == 403
    assert env.client.get('/projects/1').status_code == 200
    env.login(2)
    assert env.client.get('/projects/1/settings').status_code == 200
    assert env.post('/projects/1/settings', {'name': 'Alter Stand', 'leader_user_id': 2, 'revision': 1}).status_code == 409


def test_archive_and_reopen(project_env):
    env = project_env
    env.login(1)
    cid = add_card(env)
    assert env.post('/projects/1/archive', {'archived': 'true', 'revision': 1}).status_code == 303
    assert env.client.get('/projects/1').status_code == 200
    assert env.post('/projects/1/cards', card_form()).status_code == 409
    assert env.post(f'/projects/1/cards/{cid}/comments', {'content': 'Test'}).status_code == 409
    assert env.post('/projects/1/archive', {'archived': 'false', 'revision': 2}).status_code == 303
    assert env.post('/projects/1/cards', card_form()).status_code == 303


def test_csrf_and_friendly_browser_error(project_env):
    env = project_env
    env.login(1)
    assert env.client.post('/projects/1/members', data={'user_id': 2}).status_code == 403
    env.login(2)
    response = env.client.get('/projects/1/settings', headers={'Accept': 'text/html'})
    assert response.status_code == 403 and 'Aktion nicht möglich' in response.text


def test_admin_access_and_team_permission(project_env):
    env = project_env
    env.login(4)
    assert env.client.get('/projects/3/settings').status_code == 200
    assert env.post('/projects/1/members', {'user_id': 3}).status_code == 303
    assert env.post('/projects/1/members', {'user_id': 3}).status_code == 303
    env.login(3)
    assert env.client.get('/projects/1').status_code == 200
    assert env.client.get('/projects/1/settings').status_code == 403


def test_update_card_and_filter_counts(project_env):
    env = project_env
    env.login(1)
    cid = add_card(env, status='doing')
    response = env.post(f'/projects/1/cards/{cid}', card_form(revision=1, status='doing', title='Neuer Titel', assignee_user_id='1'))
    assert response.status_code == 303
    assert env.post(f'/projects/1/cards/{cid}', card_form(revision=1)).status_code == 409
    html = env.client.get('/projects/1?mine=1').text
    assert 'Neuer Titel' in html and '1 / 1' in html
    env.login(2)
    html = env.client.get('/projects/1?mine=1').text
    assert 'Neuer Titel' not in html and '1 / 1' in html
    with Session(env.engine) as db:
        assert db.get(ProjectCard, cid).revision == 2
    env.login(1)
    assert 'Neuer Titel' in env.client.get('/projects').text
    env.login(2)
    assert 'Neuer Titel' not in env.client.get('/projects').text


def test_project_db_locks_before_opening_session(monkeypatch, tmp_path):
    import threading
    from app import project_db as module
    opened = []
    started = threading.Event()
    yielded = threading.Event()
    class FakeSession:
        def __enter__(self):
            opened.append(True)
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(module, 'SessionLocal', FakeSession)
    monkeypatch.setattr(module, 'get_settings', lambda: SimpleNamespace(projects_enabled=True, project_lock_file=str(tmp_path / 'project.lock')))
    first = module.project_db()
    next(first)
    def second_request():
        started.set()
        generator = module.project_db()
        next(generator)
        yielded.set()
        generator.close()
    thread = threading.Thread(target=second_request)
    thread.start()
    try:
        assert started.wait(2)
        assert not yielded.wait(.1)
        assert len(opened) == 1
    finally:
        first.close()
        thread.join(5)
    assert not thread.is_alive() and yielded.is_set()
    assert len(opened) == 2
