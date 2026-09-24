# Entwicklungsstand

## Aktueller Stand: Phase 1 abgeschlossen

Zuletzt aktualisiert: 24.09.2026, nach Vorbereitung des Gmail-OAuth-Imports

## Kurz gesagt

Die Anwendung kann gestartet werden. Ein Administrator kann sich anmelden und im Admin-Dashboard die ersten IMAP-/SMTP-E-Mail-Konten speichern. Die Passwörter werden verschlüsselt gespeichert. E-Mails werden aktuell noch nicht automatisch abgerufen oder versendet.

### Fertig

- Technische Architektur dokumentiert
- FastAPI-Anwendung gestartet
- SQLite-Datenbank angebunden
- Benutzer, Rollen und Berechtigungen angelegt
- Administrator-Ersteinrichtung über Umgebungsvariablen vorbereitet
- Zusätzlicher CLI-Befehl zum Anlegen eines Administrators vorhanden
- Login und Session-Cookie umgesetzt
- Responsives Dashboard umgesetzt
- Geschütztes Admin-Dashboard mit Benutzer-, Rollen- und Audit-Übersicht umgesetzt
- Audit-Log-Grundlage umgesetzt
- Human-in-the-Loop-Versandprüfung umgesetzt
- Tests und Runtime-Smoke-Test erfolgreich ausgeführt

### Noch offen

- Gmail-OAuth-Anmeldebutton und Callback
- IMAP/SMTP und mehrere E-Mail-Konten vollständig synchronisieren
- KI-Provider und AWS-Bedrock-Anbindung

## Phase 2 begonnen: Multi-Account-Grundlage

- IMAP/SMTP-Konto-Datenmodell hinzugefügt
- E-Mail-Passwörter werden verschlüsselt gespeichert
- Admin-Formular zum Anlegen eines Kontos hinzugefügt
- Sichere IMAP-/SMTP-Verbindungstests als getrennte Funktionen vorbereitet
- Admin-Schaltfläche zum Testen von IMAP und SMTP umgesetzt
- Öffentliche Registrierung bleibt deaktiviert
- Admin kann Benutzer anlegen und einem E-Mail-Konto zuordnen
- Öffentliche Benutzer-Selbstregistrierung ist nicht vorhanden
- Google-OAuth-JSON-Upload vorbereitet; Originaldatei wird nicht gespeichert
- Google-OAuth-Start und Callback ergänzt
- Gmail-Posteingang, Nachricht öffnen, gelesen markieren und Papierkorb ergänzt
- Echter Posteingang und Synchronisationsjob folgen als nächster Teil von Phase 2

## Noch zu erledigen – in sinnvoller Reihenfolge

### Als Nächstes

1. Gmail-Antworten und neue Nachrichten mit Benutzerfreigabe ergänzen
2. Verständliche Fehlermeldungen bei falschem Server, Port oder Passwort verbessern
3. IMAP-Postfach abrufen
4. E-Mails in `EmailMessage` speichern
5. Posteingang im normalen Dashboard erweitern
6. Anhänge anzeigen

### Danach

7. SMTP-Versand für manuell geschriebene E-Mails
8. Versandvorschau mit Empfänger, Betreff, Inhalt und Anhängen
9. Harte Freigabeprüfung vor jedem Versand
10. Antworten und Weiterleiten
11. Anhänge speichern und anzeigen
12. Hintergrundjob für regelmäßige Synchronisation

### Spätere Phasen

13. Gmail-OAuth und Microsoft-OAuth
14. AWS-Bedrock- und OpenAI-Provider
15. CSV-/TXT-Import für Zugangsdaten
16. KI-Zusammenfassungen und Antwortentwürfe
17. Spam- und Phishing-Schutz
18. Termine, Support, Übersetzung, Leads und Marketing
19. PostgreSQL, Redis, Docker und Produktionshärtung

## Technischer Prüfstand

- Unit-Tests: 4 bestanden
- Runtime-Smoke-Test: bestanden
- Admin-Dashboard-Smoke-Test: bestanden
- Phase-2-Admin-Formular-Smoke-Test: bestanden
- Verbindungstest-UI-Smoke-Test: bestanden
- Benutzerverwaltungs-UI-Smoke-Test: bestanden
- Gmail-JSON-Upload-Smoke-Test: bestanden
- Gmail-Posteingang-UI-Smoke-Test: bestanden
- Virtuelle `.venv` mit allen Gmail-Abhängigkeiten geprüft
- ASGI-Importtest mit `.venv` erfolgreich
- Google-Redirect-URI als eindeutige Einstellung gegen `redirect_uri_mismatch` abgesichert
- OAuth-Callback robuster gegen abgelaufene oder doppelt verwendete Codes gemacht
- Token-Austausch auf vollständige Callback-URL umgestellt und sichere Google-Fehlerinformation ergänzt
- Lokalen OAuth-Testtransport für `localhost`/`127.0.0.1` aktiviert
- PKCE-Code-Verifier für Google-OAuth ergänzt
- Fehlende Browser-Anmeldung leitet jetzt automatisch zur Login-Seite weiter
- Anleitung für Google-Fehler `403 access_denied` und Testnutzer ergänzt
- Python-Kompilierung: erfolgreich
- CSV-/TXT-Import für Zugangsdaten
- Spam, Phishing, Kalender und Support
- Leads, Marketing und Kampagnen

## Administrator anlegen

### Variante A: automatisch beim ersten Start

In `.env` werden `ADMIN_EMAIL` und `ADMIN_PASSWORD` gesetzt. Beim Start legt die Anwendung dieses Konto automatisch an, falls es noch nicht existiert.

### Variante B: interaktiver Befehl

```powershell
py -3 -m app.cli create-admin
```

Der Befehl fragt E-Mail-Adresse, Anzeigenamen und Passwort sicher ab. Er legt die Datenbanktabellen und die Administratorrolle bei Bedarf selbst an.
