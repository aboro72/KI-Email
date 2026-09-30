# AboroDesk – Fortschritt, Reihenfolge und nächste Schritte

Stand: 30.09.2026

Dieses Dokument ist die Arbeitsgrundlage für die weitere Entwicklung. Die Anwendung bleibt modular: Ein Modul kann deaktiviert werden, ohne dass E-Mail, CRM, Helpdesk, Marketing oder spätere Automationen gegenseitig zwingend benötigt werden.

## Produktziel

AboroDesk ist eine Einzelkundenlösung: Jede Installation gehört zu einem Kunden und läuft als eigene Umgebung mit eigener Datenbank, eigenen E-Mail-Konten und eigenen Benutzern. Eine Mandantenlösung innerhalb einer gemeinsamen Installation ist ausdrücklich nicht vorgesehen.

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

### 2. Hintergrundaufgaben – begonnen

Eine dauerhafte Datenbank-Warteschlange mit Wiederholungsversuchen, Fehlerstatus und registrierbaren Modul-Handlern ist jetzt vorhanden. Noch offen: ein produktiver systemd-Worker, der die Queue regelmäßig abarbeitet, sowie die Anbindung der konkreten E-Mail-, KI- und Erinnerungsaufgaben. Für mehrere Server bleiben Redis/RQ oder Celery optionale Skalierungsvarianten.

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
- Installationsassistent mit geführter Einrichtung für Datenbank, Admin, E-Mail und Backups
- Plugin-Schnittstelle für zusätzliche Module

## Anforderungen für die spätere Verkaufs-Version

- Ein klarer Installationsweg für ISPConfig3 und Einzelserver
- Konfiguration über eine verständliche `.env`- oder Web-Oberfläche statt manueller Codeänderungen
- Prüfung der Systemvoraussetzungen vor der Installation
- Ein eigener Installations- und Update-Status mit verständlichen Fehlermeldungen
- Sichere Ersteinrichtung für Admin-Konto, SECRET_KEY, MongoDB und E-Mail-Konten
- Backup- und Wiederherstellungsassistent pro Kundeninstallation
- Lizenzschlüssel oder Aktivierung nur dann, wenn das Geschäftsmodell dies später benötigt
- Deaktivierbare Module, damit Kunden nur die benötigten Funktionen betreiben
- Dokumentierte Upgrade- und Rollback-Möglichkeit
- Keine zentrale Kundendatenbank und keine Vermischung von Kundendaten

## Definition of Done je Modul

Ein Modul gilt erst als fertig, wenn es eigene Berechtigungen, deaktivierbare Navigation, Datenmodell/Migration, Tests, Audit-Einträge, Fehlerbehandlung, Installationshinweise und eine klare Freigabegrenze für automatische Aktionen besitzt.
