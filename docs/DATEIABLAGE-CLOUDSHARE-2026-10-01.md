# Dateiablage und Online-Office – Übergabe 01.10.2026

## Erledigt und auf beiden Servern eingerichtet

- Neues, separat abschaltbares AboroDesk-Modul `/documents` mit Dashboard-Link.
- Gemeinsame, geschützte Dateiablage: Liste, Upload, Download, Online-Bearbeitung, Versionsansicht und Wiederherstellung mit Bestätigung.
- Standardinstallation: `DOCUMENTS_ENABLED=false`; CloudShare ist keine Pflichtabhängigkeit.
- Separate Rechte `DOCUMENTS_VIEW`, `DOCUMENTS_UPLOAD`, `DOCUMENTS_EDIT`. Auf dem aktuellen Server zunächst nur Administratoren; weitere Rollen können bewusst freigeschaltet werden.
- CloudShare verwendet den technischen Benutzer `aborodesk_storage_api`, ohne Staff-/Administratorrechte. Das mitgeteilte Admin-Passwort wird nicht für die dauerhafte Verbindung verwendet.
- Eigenständiger CloudShare-Ordner `AboroDesk`, ID 25. Andere private Admin-Dateien sind über das Modul nicht zugänglich.
- Keine öffentlichen Freigabelinks; Datei-IDs werden bei Download und Office-Aufruf auf den konfigurierten Ablageordner geprüft.
- Größenlimit 25 MiB, sichere Downloads als Anhang, serverseitige Uploadvalidierung und CloudShare-Speicherlimitprüfung.
- CloudShare-Benutzerpasswort und Anmeldungstoken bleiben im Backend. Zeitlich begrenzte, dokumentgebundene Office-URLs werden nur an berechtigte Personen ausgegeben; keine Speicherung der URLs im Audit-Log.
- Upload-/Office-Aufrufe werden im AboroDesk-Audit-Log protokolliert. Fehler werden verständlich angezeigt, interne Backendfehler/Zugangsdaten nicht ausgegeben.

## CloudShare-Fehler behoben

Server: `212.44.166.234`, Quellcode `/home/storage/Cloude/cloudservice`.

- `/api/files/` und Detailabfragen scheiterten an `usershare`, einer nicht existierenden ORM-Rückbeziehung. Direkte aktive Freigaben werden jetzt über den passenden ContentType und Objekt-IDs ermittelt; Papierkorb-Dateien werden ausgeblendet.
- Ordnerabfragen scheiterten an `Sum('file__size')`; korrekt ist `Sum('size')`.
- Fremde Zielordner und Zyklen in Ordnerhierarchien werden abgewiesen.
- Dateizugriffe beachten Objektberechtigungen; reine Lesefreigaben erlauben keine Änderungen/Löschungen. Versionslisten verlangen Dateizugriff.
- `/api/files/{id}/office/` neu: authentifizierter POST liefert `editor_url` und `expires_in`. Der Aufruf ist zunächst auf Dateieigentümer beschränkt.
- Das vorhandene Collabora/WOPI-System wird wiederverwendet, kein zusätzlicher Office-Server installiert.
- Office-Speichern legt jetzt eine neue Dateiversion an und erhält die vorherigen Inhalte. Versionsnummern werden innerhalb einer Datenbanktransaktion am Dokument serialisiert.
- Wiederherstellung kopiert tatsächlich den gewählten früheren Inhalt in eine neue aktuelle Dateiversion. Eine aktive Office-Sperre oder veraltete Versionsanzahl verhindert das Überschreiben eines inzwischen geänderten Standes.
- Ungültige/abgelaufene Tokens sowie Tokens für inzwischen gelöschte, in den Papierkorb verschobene oder nicht mehr freigegebene Eigentümer-Dateien werden abgewiesen. Speichern mit fehlender/falscher Sperre liefert HTTP 409.

Reproduzierbarer Quellcode-Patch: `deploy/cloudshare/cloudshare-storage-api.patch`.
CloudShare-Tests und isolierte Testkonfiguration liegen ebenfalls unter `deploy/cloudshare/` und auf dem CloudShare-Server unter `api/test_storage_integration.py` bzw. `config/settings_api_test.py`.

## Sicherheits- und Netzwerkhinweise

- CloudShare lieferte bislang `/media/` unmittelbar über Nginx aus. Für den dedizierten AboroDesk-Benutzer wurde `/media/users/aborodesk_storage_api/` anonym gesperrt (HTTP 403); API- und WOPI-Downloads funktionieren weiterhin.
- Diese Sperre betrifft nur die neue AboroDesk-Ablage, nicht alle bisherigen CloudShare-Dateien. Eine umfassende Überarbeitung der alten Medienauslieferung ist eine separate Aufgabe.
- Das Nginx-Muster muss bei geändertem Benutzernamen, Speicherpfad oder späterer Firmenzuordnung angepasst werden. Eine Installation darf erst nach erfolgreichem Test des anonymen Downloadschutzes freigegeben werden.
- AboroDesk erreicht die öffentliche CloudShare-IP aus seinem internen Netz nicht (NAT-/Routingproblem). Auf `212.44.166.238` wurde `/etc/hosts` ergänzt: `192.168.0.182 cloudshare.aborosoft.com`.
- HTTPS-Hostname und Zertifikatsprüfung bleiben unverändert. Bei neuer interner IP den Hosts-Eintrag aktualisieren; kein Abschalten der TLS-Prüfung.
- Gunicorn und Daphne auf CloudShare sowie `aborodesk.service` wurden neu gestartet. Nginx-Konfiguration erfolgreich geprüft und neu geladen.

## Konfiguration / Neuinstallation

Alle Variablen stehen ohne echte Zugangsdaten in `.env.example`:

```dotenv
DOCUMENTS_ENABLED=true
CLOUDSHARE_BASE_URL=https://cloudshare.aborosoft.com
CLOUDSHARE_USERNAME=<technischer-benutzer>
CLOUDSHARE_PASSWORD=<eigenes-geheimes-passwort>
CLOUDSHARE_FOLDER_ID=<ordner-id>
CLOUDSHARE_TIMEOUT=60
DOCUMENTS_MAX_BYTES=26214400
OFFICE_BASE_URL=https://office.aborosoft.com
```

Auf dem aktuellen AboroDesk-Server nur in `/etc/aborodesk/aborodesk.env` hinterlegt, nicht im Repository. Auf CloudShare liegt die Zugangsdaten-Datei `/home/storage/Cloude/aborodesk-storage-credentials.json` mit Modus 0600. Diese Datei vertraulich behandeln und nicht per Git übertragen.

Einrichtungshelfer: `deploy/cloudshare/setup_aborodesk_storage.py`. Im Django-Projekt mit dessen Python-Umgebung ausführen; vorhandene Zugangsdaten werden wiederverwendet. Die Ausgabe enthält Geheimnisse und darf nur geschützt weitergereicht werden. Der Helfer ersetzt keinen vollständigen Installer und konfiguriert weder Nginx noch AboroDesk automatisch.

CloudShare-Patch nach Sicherung im Verzeichnis `cloudservice` prüfen; nur bei passendem Quellstand anwenden. Die vorhandenen Quellen benutzen CRLF, der Patch LF. Nach der Sicherung zunächst ausschließlich die fünf betroffenen Quelldateien auf LF normalisieren:

```bash
sed -i 's/\r$//' api/views.py api/serializers.py api/permissions.py core/models.py storage/views.py
patch --dry-run -p1 < cloudshare-storage-api.patch
# Erst nach erfolgreicher Prüfung:
patch -p1 < cloudshare-storage-api.patch
```

Der Patch wurde gegen eine gesonderte, normalisierte Kopie der Originalquellen erfolgreich geprüft; die unveränderten Rückweg-Sicherungen behalten ihre ursprünglichen Zeilenenden. Anschließend Django-Systemcheck und Tests ausführen, Dienste neu starten. Keine Schemaänderung/Migration für diese Korrekturen nötig.

## Verifikation

- AboroDesk lokal: 70 Tests bestanden, darunter 12 neue Dateiablage-Tests. `pytest.ini` begrenzt die normale Sammlung auf `tests`; die mitgelieferten Django-Tests werden separat auf CloudShare ausgeführt.
- CloudShare: 10 Regressionstests gegen isolierte SQLite-Testdatenbank und temporäre Mediendateien bestanden. Bestehende MySQL-spezifische Migrationen werden in dieser Testkonfiguration bewusst nicht ausgeführt; dies ist kein Migrationstest der Produktionsdatenbank.
- Live über CloudShare: Ordner-/Dateilisten HTTP 200, Upload HTTP 201, Download, Office-API, WOPI-Sperren/Speichern und erneuter Download erfolgreich.
- Live direkt aus AboroDesk: Seite, Upload, Download, Office-Start, WOPI-Speichern, erneuter Download, Versionsansicht, tatsächliche Wiederherstellung, Dashboard-Link und Health erfolgreich. Der Test prüfte Version 1 → Office-Version 2 → wiederhergestellte Version 3 samt Dateiinhalten.
- Anonymer direkter Download der neuen Ablage: HTTP 403.
- Nur eigens angelegte Testdateien/-ordner wurden gelöscht. Bestehende Dokumente unverändert; der dauerhafte Ablageordner und der technische Benutzer bleiben bestehen. Audit-Einträge der Tests bleiben nachvollziehbar.
- Ein vollständiger visueller Browser-/Mehrbenutzer-Office-Test ist noch offen; der Speichertest prüfte die tatsächlichen WOPI-HTTP-Aufrufe, nicht die komplette Collabora-Oberfläche.
- Die AboroDesk-Datei- und Versionsseiten wurden im Browser mit synthetischen Daten bei 1400 und 390 Pixel Breite geprüft und die Screenshots visuell kontrolliert: keine horizontalen Überläufe/JavaScript-Fehler. Navigation und lange Dateinamen bleiben auch mobil bedienbar.

## Sicherungen / Rückweg

- CloudShare-Code vorher: `/home/storage/Cloude/rollback-storage-api-20261001/`.
- Nginx vorher dort: `nginx_cloude.conf`; aktive Datei `/etc/nginx/sites-available/cloude`.
- AboroDesk-Code und vorherige Umgebung: `/opt/aborodesk/deploy/rollback-storage-20261001/`, Verzeichnis geschützt. Vorherige Hosts-Datei: `hosts`.
- Zusätzlich dauerhaft außerhalb des vom Updater ersetzten App-Verzeichnisses gesichert: `/var/backups/aborodesk/storage-20261001/rollback-storage-20261001/` (rootgeschützt). Bei einer späteren automatischen Aktualisierung diesen unabhängigen Rückweg verwenden.
- Zum einfachen Abschalten `DOCUMENTS_ENABLED=false` setzen und AboroDesk neu starten. Dateien bleiben erhalten. Keine automatischen Löschungen des CloudShare-Ordners oder Benutzers.

## Nächste erforderliche Schritte für Vertragsverwaltung

1. Eigenständiges Vertragsmodul: Vertragspartner/CRM-Verknüpfung, Vertragstyp, Status, Beginn/Ende, Kündigungsfristen, Verantwortliche und Erinnerungen.
2. Zuordnung einer oder mehrerer CloudShare-Datei-IDs zu einem Vertrag; Objektberechtigungen pro Vertrag statt lediglich gemeinsamer Modulzugriff.
3. Mehrbenutzer-Browser-Test durchführen: parallele Bearbeitung, gleichzeitige Sperranforderungen/Wiederherstellungen, Tokenablauf und Wiederanmeldung über längere Sitzungen. Einzelne Sperrkonflikte, veraltete Versionsstände und widerrufene Tokens sind abgedeckt; dies ersetzt keinen vollständigen Last-/Nebenläufigkeitstest.
4. CloudShare-Dateien in Backup-/Restore-Konzept einbeziehen: AboroDesk-MongoDB-Backups allein enthalten die Vertragsdateien nicht. Echten Wiederherstellungstest beider Systeme durchführen. Quotenberechnung und Aufbewahrung für wachsende Versionshistorien ergänzen.

## Optional

- Unterordner pro Firma/Projekt/Vertrag, Dateisuche, Vorschau, Lösch-/Papierkorb-Funktion.
- Vertragsvorlagen und automatische Dokumentenerstellung; OCR/KI-Auswertung erst nach ausdrücklicher Auswahl.
- Austauschbarer lokaler Speicheradapter, Installationsassistent und Verbindungsprüfung in der Administration. Der aktuelle erste Adapter unterstützt CloudShare; lokaler Dateispeicher ist noch nicht implementiert.
- Unveränderbare Archivierung, externe Signaturen und weitergehende Aufbewahrungsregeln gesondert planen. Die jetzige Ablage wird nicht als revisionssicher bezeichnet.
