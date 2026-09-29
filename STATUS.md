# Entwicklungsstand

Zuletzt aktualisiert: 29.09.2026

## Erledigt

- FastAPI-Anwendung mit Login, Sessions, Rollen und Berechtigungen
- Administrator-Verwaltung: Benutzer anlegen, bearbeiten, Passwörter ändern und löschen
- Sicherheitsprüfung: letzter Admin und eigener Benutzer können nicht gelöscht werden
- Viele-zu-viele-Zuordnung zwischen Benutzern und E-Mail-Konten
- Zugriffsschutz: Benutzer sehen und synchronisieren nur zugeordnete Konten
- IMAP-Empfang beim Öffnen/Aktualisieren des Posteingangs
- Speicherung von Nachrichten in `EmailMessage` inklusive Duplikatprüfung
- Helle, responsive Oberfläche mit sichtbarer Navigation
- Bedrock-Anbindung über `eu.anthropic.claude-sonnet-4-6`
- KI-Analyse neuer Nachrichten: Kategorie, Priorität, Zusammenfassung und Antwortentwurf
- Sichtbare KI-Seitenleiste im Nachrichtenfenster
- KI-Aktionen: analysieren, Antwort entwerfen, kürzen, freundlicher und professioneller formulieren
- Antworteditor direkt an der Nachricht
- Antwort als Entwurf speichern
- Manueller SMTP-Versand nach ausdrücklicher Bestätigung
- Neues E-Mail-Fenster mit An, CC und BCC
- Antworten und Weiterleiten über den gemeinsamen Editor
- Text- und HTML-Modus mit einfacher WYSIWYG-Formatierung
- Erweiterte Formatierung: Schriftarten, Größen, Farben, Hervorhebung, Ausrichtung, Listen und Links
- Bilder direkt im HTML-Editor einfügen
- Mehrere Anhänge bis 10 MB pro Datei
- Audit-Logs für Benutzeränderungen, KI-Entwürfe und Antworten
- API-Key-Datei gegen Git-Commits abgesichert
- 4 automatisierte Tests erfolgreich

## CRM bereits umgesetzt

- Firmen, Kontakte und Leads mit eigenem CRM-Bereich
- Vertriebsrolle und `CRM_MANAGE`-Berechtigung
- Quellen-URL, Opt-out-Feld, Lead-Status, Score und nächste Aktion
- CRM-Schnellzugriff im Dashboard

## Als Nächstes

1. Recherche öffentlicher geschäftlicher Kontaktdaten mit Quellen-URL und Abrufdatum
2. Duplikatprüfung und vollständige Opt-out-/Sperrliste
3. Individuelle Verkaufstexte für AboroSoft auf Basis der Firmeninformationen
4. Vertriebs-Dashboard mit Aktivitäten und Entwürfen
6. Anhänge und vollständige E-Mail-Threads
7. Hintergrund-Synchronisation mit Retry und Fehlerstatus
8. Tokenverbrauch und Bedrock-Kostenschätzung pro Nachricht/Benutzer/Monat
9. CSRF-Schutz, Rate-Limits und Produktions-Secret-Management
10. PostgreSQL, Backups und Deployment-Härtung

## Testrecherche ML Consulting

- Die Firma wurde mit oeffentlichen Firmendaten angereichert.
- Der allgemeine Geschaeftskontakt `info@mlgruppe.de` wurde mit Impressum-Quelle gespeichert.
- Ein individueller AboroSoft-Verkaufsentwurf wurde als Lead-Draft gespeichert und im CRM sichtbar gemacht.
- Es wurde keine E-Mail automatisch versendet.

## Vertriebsregeln

## LMS-Vertriebsansatz

- Bildungsunternehmen werden im Vertrieb standardmäßig mit dem LMS-Ansatz angesprochen.
- ABoroOffice wird in solchen Entwürfen nicht als fertiges Produkt beworben.
- Die KI soll Discovery-Fragen formulieren und unfertige Funktionen nicht als produktionsreif darstellen.
- Die ML-Consulting-Testrecherche wurde um E-Learning, Blended Learning, Bildungsmanagement und öffentliche Funktionskontakte vertieft.
- Neue Firmen starten bei angegebener Website automatisch eine öffentliche KI-Recherche im Hintergrund.
- Recherche-Status (`pending`, `running`, `completed`, `failed`) und Fehlertext werden im CRM angezeigt.

## CRM-Erweiterung

- Duplikate werden bei Firmen nach Name/Domain und bei Kontakten nach E-Mail erkannt.
- Opt-out-Kontakte werden beim erneuten Anlegen und bei Lead-Zuordnung blockiert.
- Firmen und Kontakte erhalten bei Quellenangabe ein Recherche-Datum.
- Aktivitäten wie Notizen, Anrufe, Termine und E-Mails können dokumentiert werden.

- Recherche und Textgenerierung erzeugen nur Entwürfe.
- Kein automatischer Massenversand.
- Vor dem Versand stehen Empfänger, Quelle, Rechtsgrundlage/Einwilligungsstatus und Opt-out-Status sichtbar im Datensatz.
- E-Mail-Versand bleibt eine manuelle Benutzeraktion.
