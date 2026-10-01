from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy.orm.exc import StaleDataError

from app import db as persistence
from app.models import Company


class Collection:
    def __init__(self):
        self.rows = {}

    def find(self, *args):
        return deepcopy(list(self.rows.values()))

    def insert_one(self, row):
        assert row['_id'] not in self.rows
        self.rows[row['_id']] = deepcopy(row)

    def update_one(self, criteria, update):
        matches = [row for row in self.rows.values() if all(row.get(key) == value for key, value in criteria.items())]
        for row in matches:
            row.update(deepcopy(update['$set']))
        return SimpleNamespace(matched_count=len(matches))

    def delete_one(self, criteria):
        for key, row in list(self.rows.items()):
            if all(row.get(name) == value for name, value in criteria.items()):
                del self.rows[key]

    def replace_one(self, *args, **kwargs):
        pass


class Database(dict):
    def __missing__(self, key):
        self[key] = Collection()
        return self[key]


@pytest.fixture
def store(monkeypatch):
    result = persistence.MongoStore.__new__(persistence.MongoStore)
    result.database = Database()
    result.database['companies'].insert_one({'_id':1,'id':1,'name':'Example','domain':'example.invalid'})
    counter = iter(range(2, 100))
    result.allocate_id = lambda table: next(counter)
    result.ping = lambda: None
    monkeypatch.setattr(persistence, 'mongo_store', result)
    return result


def test_sessions_preserve_other_sessions_fields_and_new_rows(store):
    with persistence.SessionLocal() as first, persistence.SessionLocal() as second:
        first.get(Company, 1).notes = 'Recherche'
        second.get(Company, 1).domain = 'updated.invalid'
        second.add(Company(name='New',domain='new.invalid'))
        second.commit()
        first.commit()
    with persistence.SessionLocal() as fresh:
        assert fresh.get(Company, 1).notes == 'Recherche'
        assert fresh.get(Company, 1).domain == 'updated.invalid'
        assert fresh.get(Company, 2).name == 'New'


def test_project_roles_and_cards_survive_mongo_session_reload(store):
    from app.models import Project, ProjectCard, ProjectMember, Role, User
    with persistence.SessionLocal() as db:
        db.add(Role(id=1, name='project_test'))
        db.flush()
        db.add_all([User(id=1, email='a@test.invalid', display_name='Alice', password_hash='test', role_id=1), User(id=2, email='b@test.invalid', display_name='Bob', password_hash='test', role_id=1)])
        db.flush()
        db.add_all([Project(id=1, name='A', leader_user_id=1, created_by_user_id=1), Project(id=2, name='B', leader_user_id=2, created_by_user_id=1)])
        db.flush()
        db.add_all([ProjectMember(project_id=1, user_id=2), ProjectMember(project_id=2, user_id=1)])
        db.add(ProjectCard(id=1, project_id=1, title='Karte', created_by_user_id=1, assignee_user_id=2))
        db.commit()
    with persistence.SessionLocal() as fresh:
        assert fresh.get(Project, 1).leader_user_id == 1
        assert fresh.get(Project, 2).leader_user_id == 2
        assert fresh.get(ProjectMember, (1, 2)) is not None
        assert fresh.get(ProjectMember, (2, 1)) is not None
        card = fresh.get(ProjectCard, 1)
        card.status = 'doing'
        card.revision += 1
        fresh.commit()
    with persistence.SessionLocal() as fresh:
        assert fresh.get(ProjectCard, 1).status == 'doing'
        assert fresh.get(ProjectCard, 1).revision == 2


def test_stale_session_cannot_resurrect_deleted_company(store):
    with persistence.SessionLocal() as first, persistence.SessionLocal() as second:
        company = first.get(Company, 1)
        second.delete(second.get(Company, 1))
        second.commit()
        company.notes = 'Späte KI-Antwort'
        with pytest.raises(StaleDataError):
            first.commit()
    with persistence.SessionLocal() as fresh:
        assert fresh.get(Company, 1) is None


def test_application_startup_keeps_session_alive(store, monkeypatch):
    import asyncio
    from app.main import lifespan
    from app import main
    from app.models import Permission
    from sqlalchemy import select, create_engine
    test_engine=create_engine('sqlite:///:memory:')
    monkeypatch.setattr(main,'engine',test_engine)
    monkeypatch.setattr(persistence,'engine',test_engine)
    async def start():
        async with lifespan(None):
            with persistence.SessionLocal() as session:
                assert session.scalar(select(Permission).where(Permission.name == 'EMAIL_VIEW'))
    try:
        asyncio.run(start())
    finally:
        test_engine.dispose()


def test_company_delete_preserves_campaign_history(store, monkeypatch):
    from app import main
    from app.models import Contact, Lead, Activity, MarketingRecipient
    from sqlalchemy import select
    user=SimpleNamespace(id=1,role=SimpleNamespace(permissions=[SimpleNamespace(name='CRM_MANAGE')]))
    monkeypatch.setattr(main,'require_user',lambda request,db:user)
    with persistence.SessionLocal() as session:
        contact=Contact(company_id=1,name='Contact',email='test@example.invalid')
        session.add(contact)
        session.flush()
        lead=Lead(company_id=1,contact_id=contact.id)
        session.add(lead)
        session.flush()
        session.add(Activity(contact_id=contact.id,lead_id=lead.id,user_id=1,subject='Related'))
        recipient=MarketingRecipient(campaign_id=77,contact_id=contact.id,email=contact.email)
        session.add(recipient)
        session.commit()
        recipient_id=recipient.id
    with persistence.SessionLocal() as session:
        assert main.delete_company(1,None,session).status_code == 303
    with persistence.SessionLocal() as session:
        assert session.get(Company,1) is None
        assert session.scalar(select(Contact)) is None
        assert session.scalar(select(Lead)) is None
        assert session.scalar(select(Activity)) is None
        assert session.get(MarketingRecipient,recipient_id).contact_id is None
