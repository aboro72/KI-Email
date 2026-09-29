# KI-Email – aktueller Projektstand und Verbesserungsideen

Stand: 29.09.2026  
Geprüfter Projektordner: `C:\Users\aborowczak\PycharmProjects\KI-Email`

## Kurzfazit

KI-Email ist aktuell ein funktionsfähiger, serverseitiger FastAPI-Arbeitsplatz für mehrere E-Mail-Konten. Der Schwerpunkt liegt auf einem sicheren, vom Menschen freigegebenen KI-Workflow: Nachrichten können analysiert werden, die KI kann Antwortentwürfe erzeugen, aber der Versand bleibt eine ausdrückliche Benutzeraktion.

Zusätzlich ist bereits ein CRM-Bereich für Firmen, Kontakte, Leads, Aktivitäten und öffentliche KI-Recherche vorhanden. Die technische Basis ist für einen internen Prototypen gut geeignet. Der größte nächste Qualitätssprung liegt weniger in weiteren Einzelaktionen, sondern in einer klareren Informationsarchitektur, einem echten E-Mail-Arbeitsfluss und einer belastbaren Produktionshärtung.

Ein geplantes weiteres Kernmodul ist ein Helpdesk. Dieses soll nicht fest mit CRM oder Vertrieb verschmolzen werden, sondern als optionales Modul mit eigenen Daten, Berechtigungen, Ansichten und Einstellungen ergänzt werden können.

## Aktuell vorhanden

### E-Mail und KI

- Login, Sessions, Rollen und Berechtigungen
- Mehrere IMAP/SMTP-Konten mit Benutzer-Zuordnung
- Posteingang mit manueller Synchronisierung beim Öffnen/Aktualisieren
- Speicherung von Nachrichten mit Duplikatprüfung
- Lesen, Antworten und Weiterleiten
- Neue E-Mails mit An, CC, BCC und Anhängen
- Text- und HTML-Modus mit einfacher Formatierung
- KI-Analyse mit Kategorie, Priorität, Zusammenfassung und Antwortentwurf
- KI-Aktionen zum Kürzen sowie freundlicheren oder professionelleren Formulieren
- sichtbare KI-Seitenleiste im Nachrichtenfenster
- Audit-Protokollierung für relevante Benutzer-, KI- und Versandaktionen
- Human-in-the-loop-Versandfreigabe als technisches Sicherheitsprinzip

### CRM

- Firmen, Kontakte und Leads
- Vertriebsrolle und `CRM_MANAGE`-Berechtigung
- Quellen-URL, Recherchezeitpunkt, Opt-out, Lead-Status und Score
- öffentliche Website-Recherche im Hintergrund
- Recherche-Status `pending`, `running`, `completed`, `failed`
- Duplikatprüfung für Firmen und Kontakte
- Aktivitäten wie Notiz, Anruf, Termin und E-Mail
- KI-generierte Verkaufstexte bleiben als überprüfbare Entwürfe gespeichert

### Geplantes Helpdesk-Modul

Das Helpdesk soll eingehende Anfragen in Tickets überführen und Supportteams bei der Bearbeitung unterstützen. Es ist ausdrücklich als optionales Modul vorgesehen, da nicht jeder Benutzer und nicht jede Installation Supportfunktionen benötigt.

Vorgesehene Funktionen:

- Tickets aus E-Mails, Formularen und manueller Anlage
- Ticketnummer, Betreff, Beschreibung, Status, Priorität und Kategorie
- Zuordnung zu Benutzer, Team, Firma und Kontakt
- öffentliche Antworten und interne Notizen
- Verlauf aller Nachrichten und Statusänderungen als Timeline
- Anhänge und relevante E-Mail-Referenzen
- SLA-Zeiten, Fälligkeit, Wiedervorlage und Eskalation
- Vorlagen und Makros für wiederkehrende Antworten
- KI-Unterstützung für Klassifikation, Zusammenfassung und Antwortentwürfe
- Wissensdatenbank bzw. verlinkte Lösungshilfen
- Auswertungen zu offenen Tickets, Antwortzeit, Lösungszeit und SLA-Einhaltung
- Auditierbarkeit sowie klarer manueller Versand durch Mitarbeitende

### Technik und Qualität

- FastAPI mit serverseitig gerenderten Jinja-Templates
- SQLAlchemy mit SQLite in der Entwicklung und vorbereiteter PostgreSQL-Perspektive
- Argon2id für Passwörter, HttpOnly-Sessions und verschlüsselte Mailbox-Passwörter
- responsive, helle Oberfläche mit gemeinsamer CSS-Basis
- aktueller Teststand: **4 Tests erfolgreich** (`pytest -q`)

## Beobachtungen zur aktuellen Nutzung

### Stärken

- Die zentrale Sicherheitsidee ist verständlich und sichtbar: KI erstellt Vorschläge, der Mensch entscheidet.
- Multi-Account-Zugriffe werden serverseitig geprüft.
- Die Kernbereiche Dashboard, Posteingang, E-Mail-Verfassen, CRM und Administration sind bereits als End-to-End-Flows angelegt.
- Recherche und Verkaufstexte sind nachvollziehbar mit Quelle und Status versehen.
- Die Oberfläche ist leichtgewichtig, schnell verständlich und auf kleinen Bildschirmen grundsätzlich nutzbar.

### Aktuelle Reibungspunkte

- Lange Seiten bündeln viele Formulare und Listen. Besonders CRM und Administration wirken dadurch eher wie technische Verwaltungsseiten als wie tägliche Arbeitsoberflächen.
- Im Posteingang fehlen sichtbare Filter, Suche, Sortierung, Ordner/Labels, ungelesene Hervorhebung und Sammelaktionen.
- E-Mail-Threads, Anhänge und gesendete Nachrichten sind noch nicht als zusammenhängender Gesprächsverlauf dargestellt.
- Erfolgs- und Fehlermeldungen erscheinen überwiegend nur nach einem Seitenwechsel; bei KI-Recherche und Synchronisierung fehlt ein stärkeres Live-Feedback.
- Das Dashboard zeigt teilweise feste Platzhalterwerte, zum Beispiel `0` für ungelesene Nachrichten und KI-Kosten.
- Entwürfe aus Antworten und neue Nachrichten sind funktional vorhanden, aber noch nicht als dauerhafte, automatisch gespeicherte Entwurfsverwaltung ausgebaut.
- Die Navigation ist je nach Template nicht vollständig einheitlich; CRM und Administration sollten als klarer Hauptbereich bzw. Einstellungsbereich erkennbar sein.
- Die HTML-Editor-Interaktion basiert auf `document.execCommand`, was langfristig durch einen robusteren Editor oder eine sauber gekapselte Editor-Komponente ersetzt werden sollte.

## Optische Verbesserungen

### Priorität A – Orientierung und Dichte

1. **Einheitliches App-Layout:** gemeinsame Shell mit Sidebar oder kompakter Hauptnavigation, Breadcrumbs, Seitenkopf und kontextabhängigen Aktionen.
2. **E-Mail-Zweispaltenansicht:** links Ordner/Konten, mittig Nachrichtenliste, rechts Vorschau bzw. KI-Kontext. Auf Mobilgeräten wird daraus eine klare Schrittfolge.
3. **Visuelle Zustände:** ungelesen, wichtig, Fehler, in Bearbeitung, erfolgreich und KI-Entwurf mit konsistenten Farben, Icons und Textlabels darstellen.
4. **Bessere Listen:** Tabellen oder kompakte Karten mit festen Spalten für Absender, Betreff, Zeit, Status und Aktionen; lange Inhalte nicht unkontrolliert in den Vordergrund rücken.
5. **Formulare gruppieren:** Mailkonto, Benutzer, Sicherheit und Audit im Admin-Bereich als Tabs oder einklappbare Abschnitte organisieren. CRM entsprechend in Firmen, Kontakte, Leads und Aktivitäten gliedern.

### Priorität B – Lesbarkeit und Vertrauen

1. Typografie für Betreff, Absender, Vorschautext und Zeit stärker hierarchisieren.
2. Primäre Aktionen pro Seite auf eine klare Hauptaktion reduzieren; destruktive Aktionen räumlich und farblich eindeutig absetzen.
3. Für KI-Inhalte ein eigenes, ruhiges Farbsystem mit Kennzeichnung „Vorschlag – bitte prüfen“ verwenden.
4. Leere Zustände informativer gestalten, jeweils mit kurzer Erklärung und nächster sinnvollen Aktion.
5. Toasts bzw. Inline-Rückmeldungen ergänzen und Fehler direkt am betroffenen Formular anzeigen.
6. Tastaturfokus, Kontrast, sichtbare Fokusrahmen, Labels und Fehlermeldungen nach WCAG-Grundsätzen prüfen.

### Priorität C – Politur

- konsistente Icons für Posteingang, Entwurf, KI, CRM und Einstellungen
- Skeleton- oder Ladezustände bei Synchronisierung und Recherche
- Avatar bzw. Initialen für Absender und Benutzer
- Dark Mode als optionale Benutzereinstellung
- kompakte Schnellaktionen mit Tooltips
- zentrale Design-Tokens für Farben, Abstände, Radien und Schatten statt Einzelwerte in Templates

## Verbesserungen der Handhabung

### E-Mail-Arbeitsablauf

- Volltextsuche über Betreff, Absender und Nachrichtentext
- Filter für ungelesen, Priorität, Kategorie, Zeitraum, Konto und Anhänge
- Markieren als gelesen/ungelesen, wichtig, archiviert und gelöscht
- Favoriten bzw. Follow-up-Markierung
- Sammelauswahl für mehrere Nachrichten
- echte Ordner- und Label-Unterstützung
- Konversationen über `Message-ID`, `In-Reply-To` und `References` zu Threads zusammenfassen
- Anhänge anzeigen, herunterladen, weiterleiten und sicher speichern
- gesendete E-Mails und lokale Entwürfe im gleichen Arbeitsbereich auffindbar machen
- automatische Entwurfsspeicherung mit „zuletzt gespeichert um …“
- Empfänger-Chips statt Freitext; Adressvalidierung sowie sichtbare Warnung bei externen Empfängern
- Versanddialog mit Zusammenfassung von Konto, Empfängern, Anhängen und finaler Bestätigung

### Helpdesk-Arbeitsablauf

- Ticketliste mit Suche, Filtern, Status, Priorität, Zuständigkeit und Fälligkeit
- Ticketdetailseite mit vollständiger Timeline, internen Notizen und Antworteditor
- Ticketstatus wie `neu`, `offen`, `wartet_auf_kunde`, `in_bearbeitung`, `gelöst` und `geschlossen`
- automatische Erkennung von Antworten anhand von Ticketnummer und E-Mail-Referenzen
- Zusammenführen und Aufteilen von Tickets mit nachvollziehbarer Historie
- „Übernehmen“, „zuweisen“, „eskalieren“ und „zurückstellen“ als eindeutige Aktionen
- Kundenantwort vor dem Versand prüfen und bei Bedarf durch KI vorbereiten lassen
- SLA-Warnungen und Wiedervorlagen im Dashboard anzeigen
- CRM-Verknüpfung nur optional: ein Ticket kann, muss aber nicht, einer Firma oder einem Kontakt zugeordnet sein

### KI-Bedienung

- KI-Aktionen als Dropdown oder Aktionsleiste bündeln, damit die Seitenleiste nicht überladen wird
- gewünschte Tonalität, Sprache, Länge und Zielgruppe als Auswahl anbieten
- Änderungen des KI-Entwurfs gegenüber dem vorherigen Entwurf visualisieren
- Antwortentwurf direkt im Editor einfügen, ersetzen oder als neue Variante übernehmen können
- Quellen und Unsicherheiten bei Rechercheergebnissen sichtbar machen
- KI-Ausgaben versionieren und wiederherstellen können
- Nutzung, Kosten, Modell und Laufzeit pro Anfrage nachvollziehbar anzeigen
- Abbruch, Retry und verständliche Fehlerzustände bei langen KI-Aufgaben

### CRM-Bedienung

- Listenansicht mit Suche, Filtern und gespeicherten Ansichten
- Firmen-Detailseite als zentrale 360°-Ansicht mit Kontakten, Leads, Aktivitäten und Recherche
- Pipeline/Kanban für Leads mit Drag-and-drop oder klaren Statusaktionen
- nächste Aktion und Fälligkeit als echte Aufgaben statt nur als Freitext
- Opt-out- und Sperrstatus an jeder Kontaktstelle prominent anzeigen
- Quellen, Abrufdatum und Vertrauens-/Prüfstatus an Rechercheergebnissen darstellen
- Kontakte aus einem Lead heraus direkt anschreiben, ohne Daten erneut einzugeben
- Import/Export mit Duplikatvorschau und Fehlerbericht

## Allgemeine Erweiterungsvorschläge

### Kurzfristig – hoher Nutzen

1. CSRF-Schutz für alle zustandsverändernden Formulare.
2. Rate-Limits für Login, KI-Aktionen, Recherche und Versand.
3. Serverseitige Validierung und einheitliches Fehlerformat für E-Mail-Adressen, Empfängerlisten, Uploads und HTML-Inhalte.
4. Zentrale Flash-/Toast-Komponente mit Erfolg, Warnung und Fehler.
5. Echte Dashboard-Kennzahlen aus der Datenbank statt Platzhalter.
6. Zusätzliche Tests für Berechtigungen, Versand-Gate, Opt-out-Sperren, Kontozuordnung und fehlerhafte Provider-Verbindungen.
7. Datenbankmigrationen mit Alembic anstelle von ad-hoc SQLite-Spaltenänderungen beim Start.
8. strukturierte Logs ohne Geheimnisse und mit Korrelations-ID pro Anfrage.

### Mittelfristig – Arbeitsfähigkeit im Alltag

- Hintergrundjobs mit Queue, Retry, Backoff und Status für IMAP-Synchronisierung, KI und Recherche
- WebSocket oder Polling für Fortschritt und neue Nachrichten
- OAuth für unterstützte Mailanbieter statt ausschließlich Benutzername/Passwort
- PostgreSQL, Backup-/Restore-Konzept und Aufbewahrungsregeln
- Benutzereinstellungen für Signatur, Zeitzone, Sprache, Standardkonto und KI-Tonalität
- Vorlagen für wiederkehrende Antworten und Vertriebsnachrichten
- Kalender-/Terminmodul und Wiedervorlagen
- Benachrichtigungen für neue Nachrichten, fehlgeschlagene Synchronisierung und fällige Leads
- Export von Audit-Logs und revisionssichere Aufbewahrungsregeln
- Helpdesk-Modul mit Ticketing, Zuständigkeiten, SLA, Vorlagen und Support-Dashboard

### Langfristig – Plattformperspektive

- Provider-Abstraktion mit mehreren KI-Modellen und Fallbacks
- Modell-/Prompt-Verwaltung mit Freigabeprozess und Testfällen
- Mandantenfähigkeit, falls mehrere Firmen getrennt verwaltet werden sollen
- feinere Rollen wie Support, Vertrieb, Prüfer und Administrator
- Spam-/Phishing-Hinweise mit erklärbaren Signalen
- automatische Zusammenfassung längerer Threads
- Reporting zu Antwortzeit, Lead-Konversion, KI-Nutzung und Versandvolumen
- Helpdesk-Kanäle wie Webformular, E-Mail, später Chat oder Telefonnotiz
- Mandanten- und Teamregeln für getrennte Supportbereiche
- API für Integrationen sowie Webhooks
- revisionssichere Archivierung und definierte Datenschutz-/Löschkonzepte

## Sicherheits- und Betriebsrisiken

### Dringend prüfen

- Im Projektordner liegt eine Datei `bedrock-long-term-api-key.csv`. Da sie laut Git-Status als neue Datei erkannt wird, muss geprüft werden, ob darin ein echter Schlüssel enthalten ist. Falls ja: Schlüssel sofort widerrufen/rotieren, Datei aus Git und Arbeitskopie entfernen und die Historie auf Secret-Leaks prüfen. Zugangsdaten niemals in CSV, `.env`-Dateien oder Logs versionieren.
- Produktionsbetrieb sollte nicht auf SQLite und dem Entwicklungsserver basieren.
- CSRF, Rate-Limits, Secret-Management und sichere Cookie-/Proxy-Konfiguration fehlen noch als klar abgeschlossene Produktionsmaßnahmen.
- HTML-E-Mail-Inhalte und eingebettete Bilder brauchen eine strenge Sanitization- und Größenstrategie.
- Website-Recherche sollte zusätzlich SSRF-Schutz für DNS-Rebinding, Redirects und weitere private Adressbereiche erhalten.
- Anhänge benötigen Allow-/Deny-Regeln, Größenlimits insgesamt, Malware-Prüfung und sichere Auslieferung.

## Empfohlene Reihenfolge

### Etappe 1 – Stabilität und Sicherheit

CSRF, Rate-Limits, Secret-Bereinigung, einheitliche Validierung, Fehlerbehandlung, Datenbankmigrationen und Tests für sicherheitsrelevante Flows.

### Etappe 2 – E-Mail als täglicher Arbeitsplatz

Threads, Suche, Filter, ungelesene Zustände, Ordner/Labels, Anhänge, Entwurfsautosave und echte Dashboard-Kennzahlen.

### Etappe 3 – Bedienoberfläche neu strukturieren

Gemeinsames Layout, Zweispalten-Posteingang, bessere Listen, klare Statusdarstellung, kompakte Formulare und mobile Detailansichten.

### Etappe 4 – Hintergrundverarbeitung und Transparenz

Job-Queue, Fortschrittsanzeige, Retry, Kosten-/Tokenübersicht, Modell-/Prompt-Versionierung und nachvollziehbare KI-Historie.

### Etappe 5 – CRM vom Datensatz zur Pipeline

Firmen-Detailseite, Lead-Kanban, Aufgaben/Wiedervorlagen, Aktivitäten-Timeline, Import/Export und Vertriebs-Dashboard.

### Etappe 6 – Optionales Helpdesk-Modul

Ticketmodell, Ticketliste und Detail-Timeline als eigenständigen Bereich umsetzen. Danach E-Mail-Import, Zuständigkeiten, SLA/Wiedervorlagen, Vorlagen und Helpdesk-Auswertungen ergänzen. CRM-Verknüpfungen und KI-Funktionen werden über optionale Integrationen aktiviert.

## Modulare Produktarchitektur

Damit Installationen schlank bleiben und Benutzer nur benötigte Funktionen sehen, sollte jedes Fachmodul unabhängig aktivierbar sein.

### Empfohlene Modulgrenzen

| Modul | Kernaufgabe | Abhängigkeiten |
| --- | --- | --- |
| Core | Login, Benutzer, Rollen, Berechtigungen, Einstellungen, Audit | keine |
| Mail | Konten, Synchronisierung, Posteingang, Versand, Entwürfe | Core |
| KI | Provider, Modelle, Prompts, KI-Anfragen, Kosten | Core; Mail/CRM/Helpdesk optional |
| CRM | Firmen, Kontakte, Leads, Aktivitäten | Core; Mail/KI optional |
| Helpdesk | Tickets, Teams, SLA, Support-Timeline, Wissensbasis | Core; Mail/KI/CRM optional |
| Reporting | Kennzahlen, Exporte und Auswertungen | Core; ausgewählte Fachmodule optional |

### Regeln für die Modularität

- Module erhalten eigene Python-Pakete, Templates, Styles und Routen; `main.py` sollte nur die Module registrieren.
- Jedes Modul definiert eigene Datenmodelle und Migrationen, statt Tabellen ungeordnet im Kern zu verteilen.
- Aktivierte Module werden zentral in Konfiguration oder Datenbank verwaltet.
- Navigation, Dashboard-Karten, Berechtigungen und Einstellungen zeigen nur aktivierte Module.
- Berechtigungen werden je Modul gruppiert, zum Beispiel `HELPDESK_VIEW`, `HELPDESK_MANAGE`, `HELPDESK_ASSIGN` und `HELPDESK_ADMIN`.
- Optionale Verknüpfungen laufen über klar definierte Services oder Events, nicht über direkte Querzugriffe auf interne Tabellen.
- Das Abschalten eines Moduls blendet die Oberfläche aus und verhindert neue Aktionen; vorhandene Daten bleiben erhalten, bis eine ausdrücklich geplante Archivierungs- oder Löschroutine ausgeführt wird.
- Abhängigkeiten werden beim Aktivieren geprüft. Beispielsweise kann Helpdesk ohne CRM laufen, während eine optionale CRM-Verknüpfung erst bei aktiviertem CRM erscheint.
- KI bleibt eine Fähigkeit, die ein Modul verwenden kann, aber keine Voraussetzung für die Nutzung des Moduls ist.

### Beispiel für optionale Installationen

- **Klein:** Core + Mail
- **E-Mail mit KI:** Core + Mail + KI
- **Vertrieb:** Core + Mail + CRM + KI
- **Support:** Core + Mail + Helpdesk
- **Support und Vertrieb:** Core + Mail + CRM + Helpdesk + KI

So bleibt die Anwendung für einfache Installationen übersichtlich, kann aber bei Bedarf zu einer umfassenden Kommunikations- und Supportplattform wachsen.

## Definition of Done für den nächsten größeren Meilenstein

- Ein Benutzer findet eine neue Nachricht innerhalb weniger Sekunden über Konto, Suche oder Filter.
- Ein Thread zeigt Original, Antworten, Anhänge und Status vollständig zusammenhängend.
- Ein KI-Vorschlag ist eindeutig als Vorschlag markiert, versionierbar und vor dem Versand editierbar.
- Jeder Versand zeigt Empfänger, Konto, Inhalt und Anhänge in einer finalen Bestätigung.
- Fehlgeschlagene Synchronisierungen und KI-Aufgaben sind sichtbar, wiederholbar und auswertbar.
- CRM-Nutzer können einen Lead vom Erstkontakt bis zur nächsten Aufgabe ohne Umwege bearbeiten.
- Sicherheitskritische Aktionen sind geschützt, protokolliert und durch automatisierte Tests abgedeckt.

## Technischer Prüfstand

Zum Erstellungszeitpunkt wurden die vorhandenen Tests ausgeführt:

```text
4 passed in 1.20s
```

Diese Datei ist eine fachliche Bestandsaufnahme und kein Ersatz für eine vollständige Sicherheitsprüfung oder einen Usability-Test mit echten Anwendern.
