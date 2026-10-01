# Projektplanung: Umsetzung und Übergabe

## Fertiggestellt

Das eigenständige Modul ist unter `/projects` erreichbar, im Dashboard verlinkt und in der Benutzerhilfe erklärt.

- Mehrere unabhängige Projekte mit Namen und Zielen.
- Genau eine Projektleitung pro Projekt und beliebig viele zugeordnete Mitarbeiter.
- Rollen gelten pro Projekt, nicht pro Benutzerkonto: Alice kann Projekt A leiten und in B mitarbeiten, während Bob B leitet und in A mitarbeitet.
- Projektleitung und Administration verwalten Team, Projektdaten und Archivierung. Mitarbeiter können Karten und Kommentare ihres Projekts bearbeiten, aber keine Projektleitung oder Teams ändern.
- Normale Mitarbeiter sehen nur Projekte mit eigener Teamzuordnung. Personen mit `ADMIN_SETTINGS` und Modulrecht dürfen alle Projekte verwalten.
- Ein Kanban-Board je Projekt: Backlog → Geplant → In Arbeit → Prüfung → Erledigt. Verschieben per Drag-and-drop oder per Formular, auch ohne JavaScript/Maus.
- Karten als User Story, Fehler oder Aufgabe, mit Zuständigkeit, Priorität, Termin, Story Points und Abnahmekriterien.
- Kartenfilter und projektübergreifende Liste eigener offener Karten (bis zu 50, nach Termin).
- WIP-Limit für „In Arbeit“, standardmäßig 3; 0 bedeutet unbegrenzt. Zählt alle Karten des Projekts, unabhängig vom sichtbaren Filter.
- Kommentare, interne Benachrichtigungen bei Zuordnung und Kommentaren sowie Auditprotokoll. Kein automatischer E-Mail-Versand.
- Leitungsübergabe: bisherige Leitung bleibt Mitarbeiter und kann anschließend gezielt entfernt werden.
- Beim Entfernen eines Mitarbeiters bleiben dessen Karten erhalten und werden ohne Zuständigkeit gespeichert. Andere Projekte sind unberührt.
- Archivierung statt Datenlöschung: archivierte Projekte bleiben lesbar und können wieder geöffnet werden.
- Revisionsprüfung gegen veraltete Karten-/Projekteinstellungen. Eine eigene Dateisperre wird vor dem Laden einer frischen Sitzung erworben; Moduländerungen auf demselben Server werden serialisiert, unabhängig von der KI-Sperre.

## Rechte und Einrichtung

1. Als Administrator im Dashboard „Projektplanung öffnen“ oder `/projects` aufrufen.
2. Unter Administration → Rollen & Rechte für die gewünschten Teamrollen **Projektplanung benutzen** (`PROJECT_VIEW`) freigeben. **Projekte anlegen** (`PROJECT_CREATE`) nur Personen geben, die neue Projekte erstellen sollen. Beide Rechte sind für die Administration eingerichtet.
3. Ein Projekt anlegen, genau eine Projektleitung und die Mitarbeiter auswählen. Auswahl enthält aktive Benutzer mit `PROJECT_VIEW`.
4. Bei anderer Projektleitung den Ersteller ebenfalls als Mitarbeiter auswählen, falls er Teamzugriff benötigt: reine Erstellberechtigung gewährt keinen Zugriff auf fremde Projekte.
5. Karten anlegen und Abnahmekriterien festhalten. Nach erfolgreicher Prüfung in „Erledigt“ verschieben.

Die Modulrechte schalten den Zugang frei; die konkrete Leitungs-/Mitarbeiterrolle entsteht aus der jeweiligen Projektzuordnung. Es wird keine globale Rolle „Projektleiter“ eingeführt.

## Modularität und Betrieb

`PROJECTS_ENABLED=false` deaktiviert alle Projektrouten und blendet den Dashboardzugriff aus, ohne gespeicherte Projekte zu löschen. Standard ist `true`; normale Benutzer erhalten nicht automatisch neue Modulrechte.

`PROJECT_LOCK_FILE` legt die Sperrdatei fest, Standard `.project-planning.lock` im Dienst-Arbeitsverzeichnis. Alle Webprozesse auf einem Host müssen denselben Pfad und Schreibzugriff haben. Auf mehreren Hosts reicht diese Dateisperre nicht; die aktuelle Installation ist ausdrücklich eine Einzelserverlösung. Ein gemeinsamer Datenbank-Transaktionsmechanismus wäre für eine verteilte Installation nötig.

Neue Tabellen/Collections: `projects`, `project_members`, `project_cards`, `project_comments`. Leitung steht verbindlich in `projects.leader_user_id`; die Mitgliedertabelle hat einen zusammengesetzten Schlüssel aus Projekt und Benutzer und verhindert doppelte Mitgliedschaften. Bestehende CRM-/Helpdesk-/Marketingdaten werden nicht migriert oder umgeschrieben. Die vorhandene Datenbankinitialisierung erstellt die neuen Tabellen; MongoDB übernimmt sie beim ersten Speichern.

Implementierung ist in einem eigenen Router `app/projects.py`, eigener Sitzungsverwaltung `app/project_db.py`, eigenen Templates und `projects.css`/`projects.js` gekapselt. Kleine Einbindungen in Hauptanwendung, Modellkatalog, Dashboard und Hilfe bleiben erforderlich.

## Prüfung und Serverstand

- Gesamte lokale Testsuite: 58 Tests erfolgreich, einschließlich 22 neuer Projekt-/Persistenzprüfungen.
- Linux-Server: 26 gezielte Projekt-/Mongo-Sitzungstests erfolgreich. Eine bestehende Testclient-Abkündigungswarnung ist kein Testfehler.
- Browserprüfung mit ausschließlich lokalen Beispieldaten: Desktop, Handyansicht, fünf Spalten, Drag-and-drop mit persistiertem Statuswechsel und mobile Projekteinstellungen erfolgreich; Screenshots visuell geprüft.
- Live-MongoDB-Prüfung auf dem Server: Projekt und Karten anlegen, Termin/Story Points speichern, Karten verschieben, WIP-Limit, Kommentare und Archivierung erfolgreich. Nur die exakt für diesen Prüflauf erzeugten Daten wurden anschließend entfernt; es bleibt kein Demo-Projekt zurück und keine Testbenachrichtigung wurde an andere Personen gesendet.
- Backup vor Installation: `/var/backups/aborodesk/mongodb/20261001T091705Z/aborodesk.archive.gz`.
- Sicherung geänderter Bestandsdateien: `/opt/aborodesk/deploy/rollback-projects-20261001/`.
- Webdienst neu gestartet, Worker nicht wegen des Moduls unterbrochen. Die Projektplanung braucht keine KI-Aufrufe und keine neuen Hintergrunddienste.
- Lokal gesichert in Git-Commit `ce0d862`. GitHub-Push wurde erneut mit HTTP 403 abgewiesen (`ML-PIT` hat keine Schreibberechtigung). Das Modul ist trotzdem auf dem Linux-Server installiert. Für zu Hause liegt zusätzlich `KI-Email-Projektplanung-2026-10-01.bundle` im SSH-Benutzerverzeichnis, zusammen mit dieser Anleitung; es enthält den vollständigen master-Verlauf.

## Nächste Schritte / optionale Erweiterungen

Direkt nötig: Mitarbeiterrollen freigeben, echte Projekte anlegen, Team und WIP-Limits festlegen. Automatische Termin-Erinnerungen für Projektkarten sind noch **nicht** angebunden; allgemeine Aufgaben und Projektkarten bleiben getrennte Datentypen.

Optional: Sprints und Meilensteine, frei konfigurierbare Spalten, manuelle Reihenfolge innerhalb einer Spalte, Checklisten und Anhänge, Abhängigkeiten, Zeiterfassung, Burndown/Cycle-Time, GitHub-Verknüpfung, Ticket-/CRM-Verknüpfung, getrennte Leserechte und Benachrichtigungseinstellungen. Das aktuelle Modul ist Kanban, kein vollständiges Scrum-/Gantt-System.
