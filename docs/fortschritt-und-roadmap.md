# AboroDesk – Fortschritt, Reihenfolge und nächste Schritte

Stand: 30.09.2026

Dieses Dokument ist die Arbeitsgrundlage für die weitere Entwicklung. Die Anwendung bleibt modular: Ein Modul kann deaktiviert werden, ohne dass E-Mail, CRM, Helpdesk, Marketing oder spätere Automationen gegenseitig zwingend benötigt werden.

## Bereits umgesetzt

- E-Mail-Postfächer, Posteingang, Entwürfe und Versandfreigabe
- KI-Vorschläge mit menschlicher Prüfung; kein stiller automatischer Versand
- CRM mit Firmen, Kontakten, Leads, Aktivitäten und Website-Recherche
- Helpdesk-Grundmodul mit Tickets, Prioritäten, Support-Leveln, KI-Arbeitsvorschlägen und Wissensbasis
- Marketing-Grundmodul mit Kampagnenentwürfen, Empfängerauswahl, Opt-out-Prüfung und manueller Versandbestätigung
- Rollen und Berechtigungen pro Modul
- MongoDB als Produktions-Persistenz mit SQLite-Kompatibilität für Entwicklung/Migration
- ISPConfig3- und Einzelserver-Installation inklusive MongoDB-Konfiguration
- Automatische GitHub-Updates alle 20 Minuten mit Backup, Healthcheck, Rollback und Statusanzeige im Dashboard
- Einheitliche Bezeichnungen und korrigierte E-Mail-Konto-Zuordnung im Benutzer-Dialog
- Erste gemeinsame Automatisierungsbasis: Regeln, Ereignisse und protokollierte Läufe in `automation_rules` und `automation_runs`

## Reihenfolge der Umsetzung

### 1. Automatisierungs-Engine – begonnen

Vorhanden sind jetzt ein gemeinsames Ereignismodell, einfache Bedingungen, registrierbare Modul-Aktionen und ein Audit-fähiger Laufstatus. Als Nächstes müssen CRM-, Helpdesk- und E-Mail-Ereignisse angeschlossen werden. Automatische Aktionen mit Außenwirkung bleiben zunächst freigabepflichtig.

### 2. Hintergrundaufgaben

Noch offen: langlebige Worker für E-Mail-Synchronisierung, KI-Recherche, Kampagnenvorbereitung, Erinnerungen und Updates. Für den Einzelserver sollte zunächst eine einfache Datenbank-/Systemd-Queue möglich sein; Redis/RQ oder Celery bleiben optionale Skalierungsvarianten.

### 3. Aufgaben, Erinnerungen und Benachrichtigungen

Noch offen: zentrale Aufgabenliste mit Fälligkeit, Zuständigkeit, Priorität, Wiederholung und Benachrichtigung. Ereignisse aus allen Modulen sollen dort landen.

### 4. Globale Suche und einheitliche Oberfläche

Noch offen: Suche über E-Mails, Firmen, Kontakte, Leads, Tickets, Kampagnen und Wissensartikel sowie globale Schnellaktionen und verständliche Statusmeldungen.

### 5. Helpdesk ausbauen

Noch offen: E-Mail-zu-Ticket, automatische Zuordnung, SLA-Fristen, Eskalationen, Vorlagen, Kundenportal und vollständige Ticketantwort mit Freigabeschritt.

### 6. CRM ausbauen

Noch offen: Pipeline-Ansicht, nächste Aktion, Dublettenprüfung, Wiedervorlagen, Import/Export und automatische Lead-Bewertung mit erklärbarer Begründung.

### 7. Marketing ausbauen

Noch offen: Zielgruppen, personalisierte Vorlagen, geplante Einzelversände, Zustell-/Öffnungsstatistik, Abmeldelinks und DSGVO-konforme Nachweise. Kein automatischer Massenversand ohne ausdrückliche Freigabe.

### 8. Auswertungen

Noch offen: gemeinsame Kennzahlen für Antwortzeiten, offene Aufgaben, Helpdesk-SLAs, CRM-Pipeline, Kampagnen und Automationsfehler.

### 9. Betrieb und Sicherheit

Noch offen: automatisierte Backups mit Wiederherstellungstest, zentrale Fehlerüberwachung, Aufbewahrungsregeln, 2FA, feinere Audit-Auswertung und sichere Secret-Verwaltung.

## Optionale Erweiterungen

- Redis/RQ oder Celery für mehrere Worker und mehrere Server
- Microsoft-365-/Google-Integration mit Kalender und Kontakten
- Kundenportal mit Ticketstatus und Dokumenten
- Mobile/PWA-Ansicht
- Regel-Editor per Drag-and-drop
- KI-Unterstützung für Klassifikation, Zusammenfassung und Antwortentwürfe – immer mit konfigurierbarer Freigabe
- Mandantenfähigkeit für mehrere Firmen/Organisationen
- Plugin-Schnittstelle für zusätzliche Module

## Definition of Done je Modul

Ein Modul gilt erst als fertig, wenn es eigene Berechtigungen, deaktivierbare Navigation, Datenmodell/Migration, Tests, Audit-Einträge, Fehlerbehandlung, Installationshinweise und eine klare Freigabegrenze für automatische Aktionen besitzt.
