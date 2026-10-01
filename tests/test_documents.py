from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.cloudshare import CloudShareClient, StorageError
from app.config import get_settings
from app.db import Base, get_db
from app.main import app
from app.models import Permission, Role, User
from app.security import create_session
import app.documents as documents


def client_with(handler, **settings):
    config = SimpleNamespace(cloudshare_base_url='https://cloudshare.example.test',
        office_base_url='https://office.example.test', cloudshare_username='integration',
        cloudshare_password='test-not-a-real-password', cloudshare_folder_id=42,
        cloudshare_timeout=30, documents_max_bytes=100, **settings)
    def dispatch(request):
        if request.url.path == '/api/auth/token/':
            return httpx.Response(200, json={'access': 'test-token'})
        assert request.headers['Authorization'] == 'Bearer test-token'
        return handler(request)
    return CloudShareClient(config, transport=httpx.MockTransport(dispatch))


def test_client_folder_scope_and_foreign_office():
    client = client_with(lambda request: httpx.Response(200, json={
        'folder': 99, 'editor_url': 'https://evil.example.test/steal',
    }))
    with pytest.raises(StorageError, match='nicht zur'):
        client.office(1)
    client.http.close()


def test_client_rejects_untrusted_editor_address():
    client = client_with(lambda request: httpx.Response(200, json={
        'folder': 42, 'editor_url': 'https://evil.example.test/steal',
    }))
    with pytest.raises(StorageError, match='nicht erlaubte'):
        client.office(1)
    client.http.close()


def test_download_size_limit():
    def handler(request):
        if request.url.path.endswith('/download/'):
            return httpx.Response(200, content=b'x' * 101)
        return httpx.Response(200, json={'folder': 42})
    client = client_with(handler)
    with pytest.raises(StorageError, match='Downloadgröße'):
        client.download(1)
    client.http.close()


@pytest.mark.parametrize('name,content', [('bad/name.txt', b'x'), ('test.txt', b'x'*101), ('test.txt', b'')])
def test_invalid_uploads(name, content):
    client = client_with(lambda request: pytest.fail('Invalid upload must not be sent'))
    with pytest.raises(StorageError):
        client.upload(name, content, 'text/plain')
    client.http.close()


def test_upload_is_private_and_not_retried_on_server_error():
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(500, text='internal secret detail')
    client = client_with(handler)
    with pytest.raises(StorageError) as error:
        client.upload('contract.txt', b'data', 'text/plain')
    assert len(sent) == 1 and b'false' in sent[0]
    assert 'internal secret' not in str(error.value)
    client.http.close()


@pytest.fixture
def document_env(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        perms = [Permission(name=n) for n in ('DOCUMENTS_VIEW','DOCUMENTS_UPLOAD','DOCUMENTS_EDIT')]
        db.add_all([
            User(id=1, email='admin@example.test', display_name='Admin', password_hash='unused', role=Role(name='doc_admin', permissions=perms)),
            User(id=2, email='reader@example.test', display_name='Reader', password_hash='unused', role=Role(name='doc_reader', permissions=[perms[0]])),
            User(id=3, email='none@example.test', display_name='None', password_hash='unused', role=Role(name='doc_none')),
        ])
        db.commit()
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(get_settings(), 'documents_enabled', True)
    fake = SimpleNamespace(
        files=lambda: [{'id': 10, 'name': '<script>contract</script>.txt', 'size_mb': 0.1, 'extension': 'txt', 'updated_at': '2026-10-01'}],
        upload=lambda *args: {'id': 11},
        office=lambda file_id: 'https://office.example.test/editor?access_token=short-token',
        download=lambda file_id: ({'name': 'Vertrag.txt'}, b'contract'),
        file=lambda file_id: {'id': file_id, 'name': 'Vertrag.txt', 'version_count': 2, 'versions': [
            {'id': 1, 'version_number': 1, 'is_current': False, 'size': 10, 'created_at': '2026-10-01'},
            {'id': 2, 'version_number': 2, 'is_current': True, 'size': 12, 'created_at': '2026-10-01'},
        ]},
        restore=lambda *args: {'version_number': 3},
    )
    monkeypatch.setattr(documents, 'storage_client', lambda: fake)
    client = TestClient(app)
    yield client
    client.close()
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def login(client, user_id):
    client.cookies.set('ki_email_session', create_session(user_id))


def test_module_auth_and_disable(document_env, monkeypatch):
    client = document_env
    assert client.get('/documents').status_code == 401
    login(client, 3)
    assert client.get('/documents').status_code == 403
    monkeypatch.setattr(get_settings(), 'documents_enabled', False)
    assert client.get('/documents').status_code == 404


def test_reader_cannot_upload_or_edit(document_env):
    client = document_env
    login(client, 2)
    response = client.get('/documents')
    assert '&lt;script&gt;' in response.text and '<script>contract' not in response.text
    headers = {'Origin':'http://testserver'}
    assert client.post('/documents/upload', files={'file':('a.txt', b'a')}, headers=headers).status_code == 403
    assert client.post('/documents/10/office', headers=headers).status_code == 403
    assert client.post('/documents/10/restore', data={'version_id':1,'expected_count':2}, headers=headers).status_code == 403
    response = client.get('/documents/10/download')
    assert response.content == b'contract' and response.headers['Cache-Control'] == 'no-store'


def test_upload_office_and_csrf(document_env):
    client = document_env
    login(client, 1)
    response = client.post('/documents/upload', files={'file':('a.txt', b'a')}, headers={'Origin':'http://testserver'}, follow_redirects=False)
    assert response.status_code == 303
    response = client.post('/documents/10/office', headers={'Origin':'http://testserver'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['Referrer-Policy'] == 'no-referrer'
    response = client.post('/documents/10/office', headers={'Origin':'https://evil.example.test'})
    assert response.status_code == 403


def test_versions_and_restore(document_env):
    client = document_env
    login(client, 1)
    response = client.get('/documents/10/versions')
    assert response.status_code == 200 and 'Version wiederherstellen' in response.text
    response = client.post('/documents/10/restore', data={'version_id':1,'expected_count':2},
                           headers={'Origin':'http://testserver'}, follow_redirects=False)
    assert response.status_code == 303 and response.headers['location']=='/documents/10/versions'
    login(client, 2)
    assert 'Version wiederherstellen' not in client.get('/documents/10/versions').text


def test_restore_rejects_changed_document():
    client = client_with(lambda request: httpx.Response(200, json={'folder':42,'version_count':3,'versions':[{'id':1}]}))
    with pytest.raises(StorageError, match='inzwischen geändert'):
        client.restore(1, 1, 2)
    client.http.close()
