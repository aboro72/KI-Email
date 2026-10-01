"""Run on CloudShare with its Django environment; prints credentials for secure piping only.

Never redirect the output to a public file or paste it into application logs.
The account is not staff/admin. Existing credentials are reused, not rotated.
"""
import json
import os
from pathlib import Path
import secrets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth.models import User
from django.db import transaction
from core.models import StorageFolder

credential_file = Path('/home/storage/Cloude/aborodesk-storage-credentials.json')
if credential_file.exists():
    data = json.loads(credential_file.read_text())
    user = User.objects.get(username=data['username'], is_staff=False, is_superuser=False)
    folder = StorageFolder.objects.get(pk=data['folder_id'], owner=user)
    if not user.check_password(data['password']):
        raise RuntimeError('Stored CloudShare credentials no longer match; refusing automatic rotation')
    contracts_folder = StorageFolder.objects.filter(owner=user, parent=folder, name='AboroDesk Verträge').first()
    if not contracts_folder:
        contracts_folder = StorageFolder.objects.create(owner=user, parent=folder, name='AboroDesk Verträge', is_public=False)
    data['contracts_folder_id'] = contracts_folder.pk
    credential_file.write_text(json.dumps(data))
else:
    username = 'aborodesk_storage_api'
    if User.objects.filter(username=username).exists():
        raise RuntimeError('Integration username already exists without credentials; refusing to overwrite')
    password = secrets.token_urlsafe(40)
    with transaction.atomic():
        user = User.objects.create_user(username, password=password, is_staff=False, is_superuser=False)
        folder = StorageFolder.objects.filter(owner=user, parent=None).first()
        if folder:
            folder.name = 'AboroDesk'
            folder.is_public = False
            folder.save()
        else:
            folder = StorageFolder.objects.create(owner=user, name='AboroDesk', is_public=False)
        contracts_folder = StorageFolder.objects.create(owner=user, parent=folder, name='AboroDesk Verträge', is_public=False)
        data = {'username': username, 'password': password, 'folder_id': folder.pk,
                'contracts_folder_id': contracts_folder.pk}
        # 0600 before any secret bytes are written.
        fd = os.open(credential_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
os.chmod(credential_file, 0o600)
print(json.dumps(data))
