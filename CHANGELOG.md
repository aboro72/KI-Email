# Änderungsverlauf

## 24.09.2026 – Phase-2-Grundlage

- Multi-Account-Datenmodell ergänzt
- IMAP-/SMTP-Felder ergänzt
- E-Mail-Passwörter verschlüsselt gespeichert
- Admin-Formular für E-Mail-Konten ergänzt
- Admin-Dashboard um E-Mail-Konten erweitert
- IMAP-/SMTP-Verbindungstest als sichere Serverfunktion vorbereitet
- Verbindungstest-Schaltfläche im Admin-Dashboard ergänzt
- IMAP-/SMTP-Verbindungstest gegen verschlüsselte Kontodaten ergänzt
- Verbindungstest prüft Zugangsdaten, verschickt aber keine Nachricht
- Öffentliche Selbstregistrierung ausdrücklich nicht vorgesehen
- Admin-Benutzerverwaltung mit Zuordnung zu einem E-Mail-Konto ergänzt
- Benutzer-Selbstregistrierung ausgeschlossen; Benutzeranlage nur durch Admin
- Gmail-OAuth-JSON-Upload im Admin-Dashboard ergänzt
- OAuth-JSON wird validiert und verschlüsselt gespeichert
- Gmail-OAuth-Start und Callback ergänzt
- Gmail-Posteingang mit Öffnen, gelesen markieren und Papierkorb ergänzt
- Status und offene Aufgaben dokumentiert

## 24.09.2026 – Phase 1

- FastAPI-Grundgerüst erstellt
- SQLite-Datenbank eingerichtet
- Login und Administratorrolle erstellt
- Rollen und Berechtigungen ergänzt
- Admin-Dashboard erstellt
- Human-in-the-Loop-Versandprüfung umgesetzt

## 24.09.2026 – Fehlerbehebung

- Fehlendes `google-auth-oauthlib` in der verwendeten `.venv` installiert
- Abhängigkeiten mit `requirements.txt` synchronisiert
- ASGI-Import und Tests in derselben virtuellen Umgebung geprüft
- Google-Redirect-URI konfigurierbar gemacht und lokal auf `localhost` vereinheitlicht
- `InvalidGrantError` verständlich abgefangen; OAuth-Session wird beim Callback erneut gesetzt
- Lokale OAuth-HTTP-Ausnahme für Entwicklung ergänzt; Produktion bleibt HTTPS-pflichtig
- Google-PKCE-Verifier über signierten OAuth-State ergänzt
- Browserfreundliche Weiterleitung von `401 Unauthorized` zur Login-Seite ergänzt
