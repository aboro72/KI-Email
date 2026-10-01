"""Storage API regression tests; run against an isolated test database/media."""
import tempfile
from urllib.parse import urlparse, parse_qs
from django.core.cache import cache
from django.urls import reverse

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from core.models import StorageFile, StorageFolder
from sharing.models import UserShare


class StorageIntegrationTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory(prefix='cloudshare-api-test-')
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media.name,
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            ALLOWED_HOSTS=['testserver'],
            COLLABORA_BASE_URL='https://office.aborosoft.com',
            CLOUDSERVICE_EXTERNAL_URL='https://cloudshare.aborosoft.com',
        )
        self.settings_override.enable()
        cache.clear()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media.cleanup)
        self.owner = User.objects.create_user('api-test-owner')
        self.other = User.objects.create_user('api-test-other')
        self.folder = StorageFolder.objects.filter(owner=self.owner).first()
        self.other_folder = StorageFolder.objects.filter(owner=self.other).first()
        self.file = StorageFile.objects.create(
            owner=self.owner, folder=self.folder, name='example.txt',
            file=SimpleUploadedFile('example.txt', b'Original test text', 'text/plain'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def share(self, permission='view', active=True, folder=False):
        obj = self.folder if folder else self.file
        return UserShare.objects.create(
            owner=self.owner, shared_with=self.other,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk, permission=permission, is_active=active,
        )

    def test_lists_and_folder_size(self):
        response = self.client.get('/api/files/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        response = self.client.get('/api/folders/')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data['results'][0]['size'], 0)

    def test_private_and_inactive_shares_hidden(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/files/').data['count'], 0)
        self.share(active=False)
        self.assertEqual(self.client.get('/api/files/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/files/{self.file.pk}/versions/').status_code, 404)

    def test_view_share_cannot_write_or_open_editor(self):
        self.share()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/files/').data['count'], 1)
        self.assertEqual(self.client.patch(f'/api/files/{self.file.pk}/', {'name': 'bad.txt'}, format='multipart').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/files/{self.file.pk}/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/files/{self.file.pk}/office/').status_code, 403)

    def test_owner_upload_download_and_office(self):
        response = self.client.post('/api/files/', {
            'name': 'upload.txt', 'folder': self.folder.pk,
            'file': SimpleUploadedFile('upload.txt', b'AboroDesk upload', 'text/plain'),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        file_id = response.data['id']
        response = self.client.post(f'/api/files/{file_id}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'AboroDesk upload')
        response.close()
        response = self.client.post(f'/api/files/{file_id}/office/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(urlparse(response.data['editor_url']).hostname, 'office.aborosoft.com')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_foreign_folder_and_folder_cycles_rejected(self):
        response = self.client.post('/api/files/', {
            'name': 'bad.txt', 'folder': self.other_folder.pk,
            'file': SimpleUploadedFile('bad.txt', b'test', 'text/plain'),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f'/api/folders/{self.folder.pk}/', {'parent': self.folder.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_no_unauthenticated_office_access(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.post(f'/api/files/{self.file.pk}/office/').status_code, (401, 403))

    def test_executable_upload_rejected(self):
        response = self.client.post('/api/files/', {
            'name': 'bad.exe', 'folder': self.folder.pk,
            'file': SimpleUploadedFile('bad.exe', b'MZbad', 'application/octet-stream'),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_office_save_versions_and_real_restore(self):
        response = self.client.post(f'/api/files/{self.file.pk}/office/')
        token = parse_qs(urlparse(response.data['editor_url']).query)['access_token'][0]
        source = reverse('storage:wopi_file', kwargs={'file_id': self.file.pk})
        contents = source + '/contents'
        params = '?access_token=' + token
        locked = self.client.post(source + params, HTTP_X_WOPI_OVERRIDE='LOCK', HTTP_X_WOPI_LOCK='test-lock')
        self.assertEqual(locked.status_code, 200)
        response = self.client.post(contents + params, b'Updated Office text', content_type='application/octet-stream',
                                    HTTP_X_WOPI_OVERRIDE='PUT', HTTP_X_WOPI_LOCK='test-lock')
        self.assertEqual(response.status_code, 200)
        self.file.refresh_from_db()
        self.assertEqual(self.file.version_count, 2)
        original = self.file.versions.get(version_number=1)
        with original.file_data.open('rb') as source_file:
            self.assertEqual(source_file.read(), b'Original test text')
        response = self.client.post(f'/api/files/{self.file.pk}/restore/', {'version_id': original.pk}, format='json')
        self.assertEqual(response.status_code, 409)
        self.client.post(source + params, HTTP_X_WOPI_OVERRIDE='UNLOCK', HTTP_X_WOPI_LOCK='test-lock')
        stale = self.client.post(f'/api/files/{self.file.pk}/restore/',
            {'version_id': original.pk, 'expected_version_count': 1}, format='json')
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.file.versions.count(), 2)
        response = self.client.post(f'/api/files/{self.file.pk}/restore/', {'version_id': original.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.file.refresh_from_db()
        self.assertEqual(self.file.version_count, 3)
        with self.file.file.open('rb') as source_file:
            self.assertEqual(source_file.read(), b'Original test text')
        self.assertEqual(self.file.versions.filter(is_current=True).count(), 1)

    def test_office_rejects_invalid_token_and_wrong_lock(self):
        response = self.client.post(f'/api/files/{self.file.pk}/office/')
        token = parse_qs(urlparse(response.data['editor_url']).query)['access_token'][0]
        source = reverse('storage:wopi_file', kwargs={'file_id': self.file.pk})
        self.assertEqual(self.client.get(source + '?access_token=invalid').status_code, 403)
        response = self.client.post(source + '/contents?access_token=' + token, b'bad',
            content_type='application/octet-stream', HTTP_X_WOPI_OVERRIDE='PUT', HTTP_X_WOPI_LOCK='wrong')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.file.versions.count(), 1)
        self.file.is_trashed = True
        self.file.save(update_fields=['is_trashed'])
        self.assertEqual(self.client.get(source + '?access_token=' + token).status_code, 403)

    def test_folder_share_does_not_grant_file_with_same_id(self):
        self.share(folder=True)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/files/').data['count'], 0)
