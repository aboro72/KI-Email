"""Optional CloudShare storage adapter. Credentials/tokens never reach the browser."""
from functools import lru_cache
import threading
import time
from urllib.parse import urlparse

import httpx

from app.config import get_settings


class StorageError(Exception):
    pass


def https_url(value):
    url = urlparse(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise StorageError("Die Dateiablage benötigt eine gültige HTTPS-Adresse.")
    return value.rstrip("/")


class CloudShareClient:
    def __init__(self, settings=None, transport=None, folder_id=None):
        self.settings = settings or get_settings()
        self.base_url = https_url(self.settings.cloudshare_base_url)
        self.office_url = https_url(self.settings.office_base_url)
        self.folder_id = self.settings.cloudshare_folder_id if folder_id is None else folder_id
        if not self.settings.cloudshare_username or not self.settings.cloudshare_password or self.folder_id <= 0:
            raise StorageError("CloudShare-Zugang und Ablageordner müssen eingerichtet werden.")
        self.http = httpx.Client(base_url=self.base_url, timeout=max(10, self.settings.cloudshare_timeout),
                                 follow_redirects=False, transport=transport)
        self._token = ""
        self._token_until = 0
        self._token_lock = threading.Lock()

    def token(self, refresh=False):
        with self._token_lock:
            if not refresh and self._token and time.monotonic() < self._token_until:
                return self._token
            response = self.http.post("/api/auth/token/", json={
                "username": self.settings.cloudshare_username, "password": self.settings.cloudshare_password,
            })
            if response.status_code != 200:
                raise StorageError("CloudShare-Anmeldung fehlgeschlagen. Bitte die Administration informieren.")
            try:
                token = response.json()["access"]
                if not isinstance(token, str) or not token:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise StorageError("CloudShare lieferte keine gültige Anmeldung.") from None
            self._token, self._token_until = token, time.monotonic() + 180
            return token

    def request(self, method, path, **kwargs):
        try:
            response = self.http.request(method, path, headers={"Authorization": "Bearer " + self.token()}, **kwargs)
            # 401 means the operation was rejected; no retries after ambiguous upload failures.
            if response.status_code == 401:
                response = self.http.request(method, path, headers={"Authorization": "Bearer " + self.token(refresh=True)}, **kwargs)
        except httpx.HTTPError:
            raise StorageError("CloudShare ist nicht erreichbar oder antwortet zu langsam. Vor erneutem Upload die Dateiliste prüfen.") from None
        if response.status_code >= 400 or response.status_code < 200 or response.status_code >= 300:
            if response.status_code == 400:
                message = "CloudShare hat die Datei oder Eingaben abgelehnt (Dateityp, Größe, Speicherlimit oder Ordner prüfen)."
            elif response.status_code in (403, 404):
                message = "Die Datei oder der Ordner ist nicht freigegeben oder nicht mehr vorhanden."
            elif response.status_code == 409:
                message = "Das Dokument wird gerade bearbeitet oder wurde geändert. Office schließen und die Versionsliste neu laden."
            else:
                message = "Die CloudShare-Schnittstelle meldet einen Fehler. Bitte die Administration informieren."
            raise StorageError(message)
        return response

    def json(self, response):
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except (ValueError, TypeError):
            raise StorageError("CloudShare lieferte ein ungültiges Antwortformat.") from None

    def files(self):
        data = self.json(self.request("GET", f"/api/folders/{self.folder_id}/contents/"))
        files = data.get("files")
        if not isinstance(files, list) or any(not isinstance(f, dict) for f in files):
            raise StorageError("Die CloudShare-Dateiliste ist ungültig.")
        return [f for f in files if f.get("folder") == self.folder_id]

    def file(self, file_id):
        if file_id <= 0:
            raise StorageError("Ungültige Datei.")
        data = self.json(self.request("GET", f"/api/files/{file_id}/"))
        if data.get("folder") != self.folder_id:
            raise StorageError("Diese Datei gehört nicht zur AboroDesk-Ablage.")
        return data

    def upload(self, name, content, mime_type):
        if not content or len(content) > self.settings.documents_max_bytes:
            raise StorageError("Die Datei ist leer oder überschreitet die erlaubte Größe.")
        if not name or len(name) > 255 or any(c in name for c in '/\\\x00\r\n'):
            raise StorageError("Der Dateiname ist ungültig.")
        return self.json(self.request("POST", "/api/files/", data={
            "name": name, "folder": str(self.folder_id), "is_public": "false",
        }, files={"file": (name, content, mime_type or "application/octet-stream")}))

    def download(self, file_id):
        info = self.file(file_id)
        # Stream with a hard bound so the response cannot exhaust app memory.
        content = bytearray()
        try:
            with self.http.stream("POST", f"/api/files/{file_id}/download/", headers={"Authorization": "Bearer " + self.token()}) as response:
                if response.status_code != 200:
                    raise StorageError("Der Download wurde von CloudShare abgelehnt. Bitte erneut versuchen.")
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > self.settings.documents_max_bytes:
                        raise StorageError("Die Datei überschreitet die erlaubte Downloadgröße.")
        except httpx.HTTPError:
            raise StorageError("CloudShare-Download fehlgeschlagen.") from None
        return info, bytes(content)

    def office(self, file_id):
        self.file(file_id)
        data = self.json(self.request("POST", f"/api/files/{file_id}/office/"))
        url = data.get("editor_url", "")
        if not isinstance(url, str):
            raise StorageError("CloudShare lieferte eine ungültige Office-Adresse.")
        actual, expected = urlparse(url), urlparse(self.office_url)
        if (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc) or actual.username or actual.password:
            raise StorageError("CloudShare lieferte eine nicht erlaubte Office-Adresse.")
        return url

    def restore(self, file_id, version_id, expected_count):
        info = self.file(file_id)
        if info.get('version_count') != expected_count:
            raise StorageError('Das Dokument wurde inzwischen geändert. Bitte die Versionsliste neu laden.')
        if not any(v.get('id') == version_id for v in info.get('versions', [])):
            raise StorageError('Diese Version gehört nicht zum ausgewählten Dokument.')
        return self.json(self.request('POST', f'/api/files/{file_id}/restore/', json={
            'version_id': version_id, 'expected_version_count': expected_count,
        }))


@lru_cache(maxsize=1)
def storage_client():
    return CloudShareClient()


@lru_cache(maxsize=1)
def contract_storage_client():
    return CloudShareClient(folder_id=get_settings().contracts_cloudshare_folder_id)
