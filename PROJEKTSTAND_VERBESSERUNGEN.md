# KI-Email – Projektstand, Risiken und nächster Ausbau

Stand: 29.09.2026  
Codebasis geprüft: `C:\\Users\\User\\PycharmProjects\\KI-Email`

## Kurzfazit

KI-Email ist ein funktionierender, serverseitiger FastAPI-Prototyp für mehrere E-Mail-Konten, KI-gestützte Entwürfe und einfache CRM-Arbeit. Die wichtigste Produktentscheidung ist bereits richtig umgesetzt: Die KI darf Inhalte analysieren und Entwürfe erzeugen, der Versand erfolgt nur durch eine ausdrückliche Benutzeraktion.

Die Anwendung sollte jetzt **nicht** zuerst um weitere große Fachbereiche wachsen. Der beste nächste Schritt ist, den vorhandenen Mail- und CRM-Kern verlässlich, sicher und im Alltag schnell nutzbar zu machen. Erst danach lohnt sich ein optionales Helpdesk-Modul.

Der aktuelle Code eignet sich für Entwicklung und kontrollierte interne Tests, aber noch nicht für einen ungehärteten Produktionsbetrieb.

## Tatsächlich vorhandener Funktionsumfang

### Anmeldung, Rechte und Konten

- Login mit signierter, HttpOnly-Session und Argon2id-Passwort-Hashes
- Rollen und serverseitige Berechtigungsprüfung
- Administratorverwaltung für Benutzer und E-Mail-Konten
- Mehrere Konten pro Benutzer; Zugriffe werden im Backend geprüft
- Schutz davor, den eigenen Benutzer oder den letzten Administrator zu löschen
- verschlüsselte Ablage der Zugangsdaten für IMAP/SMTP, abgeleitet vom Anwendungs-Secret

### E-Mail und KI

- manueller IMAP-Abruf im Posteingang mit Duplikatprüfung über die `Message-ID`
- gespeicherte Nachrichten mit Absender, Betreff, Text, Empfangszeit und Gelesen-Status
- Lesen, Antworten, Weiterleiten und neue E-Mails
- An, CC, BCC, Text-/HTML-Modus und Dateianhänge
- einfache WYSIWYG-Formatierung inklusive eingebetteter Bilder
- KI-Analyse mit Kategorie, Priorität, Zusammenfassung und Antwortentwurf
- KI-Aktionen zum Entwerfen, Kürzen sowie freundlicheren oder professionelleren Formulieren
- Entwürfe und manuell bestätigter SMTP-Versand
- Audit-Logs für relevante Benutzer-, KI- und Versandaktionen

### CRM

- Firmen, Kontakte, Leads und Aktivitäten
- Vertriebsrolle mit `CRM_MANAGE`
- Lead-Status, Score, nächste Aktion, Opt-out und Quellenangaben
- Duplikatprüfungen für Firmen und Kontakte
- öffentliche Website-Recherche; bei angegebener Website automatisch als FastAPI-Background-Task gestartet
- sichtbarer Recherche-Status: `pending`, `running`, `completed`, `failed` oder `skipped`
- KI-generierte Vertriebstexte bleiben Entwürfe; es gibt keinen automatischen Massenversand

## Wichtigste Lücken und Risiken

| Priorität | Beobachtung | Warum das zählt | Konkrete Maßnahme |
| --- | --- | --- | --- |
| P0 | `bedrock-long-term-api-key.csv` liegt im Arbeitsverzeichnis. Sie ist aktuell ignoriert und nicht als untracked Git-Datei sichtbar, bleibt aber ein sensibles lokales Secret. | Zugangsdaten können über Backups, Freigaben oder Fehlbedienung abfließen. | Inhalt und Berechtigungen prüfen. Bei echtem Schlüssel: rotieren; danach Secret-Store oder Umgebungsvariable verwenden. Keine Secrets in CSV, `.env`, Logs, Tests oder Dokumentation ablegen. |
| P0 | Standardwerte für `secret_key` und Admin-Zugangsdaten sind entwicklungsgeeignet. | Ein versehentlicher Produktionsstart wäre angreifbar. | Start in Produktion ohne starke, gesetzte Secrets ablehnen; sichere Cookie- und Proxy-Konfiguration dokumentieren und testen. |
| P0 | Zustandsändernde Formulare haben keinen erkennbaren CSRF-Schutz; Login, Versand, Admin- und CRM-Aktionen sind betroffen. | Fremde Seiten könnten Aktionen in einer bestehenden Sitzung auslösen. | CSRF-Middleware/Token für alle schreibenden Routen einführen und durch Tests absichern. |
| P0 | HTML-Inhalte und eingebettete Bilder werden angenommen, ohne dass eine zentrale Sanitization-Strategie sichtbar ist. | XSS, sehr große Mails und riskante Inhalte können Benutzer oder System belasten. | Eingehendes und ausgehendes HTML mit Allowlist bereinigen; Data-URLs, Größe und MIME-Typ begrenzen; HTML in der Anzeige isolieren. |
| P1 | `_fetch_public_website` sperrt nur einige lokale Adressen. Redirects, IPv6-Sonderbereiche, weitere private Netze und DNS-Rebinding sind nicht vollständig abgedeckt. | Die Recherche kann für SSRF missbraucht werden. | URL nach jedem Redirect auflösen und gegen vollständige private/reservierte IP-Bereiche prüfen; nur HTTP(S), kurze Timeouts, Größenlimits und ausgehenden Netzwerkzugriff einschränken. |
| P1 | IMAP, KI-Recherche und KI-Analyse laufen synchron bzw. als prozesslokale `BackgroundTasks`. | Web-Worker können blockieren; Jobs gehen bei Neustart verloren und haben keinen Retry. | Persistente Job-Queue mit Status, Retry, Backoff, Abbruch und Fehleranzeige einführen. |
| P1 | Schemaänderungen werden beim Start per SQLite-`ALTER TABLE` erledigt. | Das ist nicht versionssicher, schwer prüfbar und nicht PostgreSQL-tauglich. | Alembic-Migrationen einführen; Startcode nur noch für Initialdaten verwenden. |
| P1 | Uploads haben zwar einen Hinweis auf 10 MB pro Datei, aber keine zentral erzwingbare Richtlinie für Anzahl, Gesamtgröße, Inhalt und Malware-Prüfung. | Speicherverbrauch und schädliche Anhänge sind nicht ausreichend kontrolliert. | Serverseitige Limits, Quarantäne/Scan, sichere Dateinamen und kontrollierte Download-Auslieferung ergänzen. |
| P1 | Es gibt weder Rate-Limits noch ein einheitliches Fehler-/Validierungskonzept. | Brute Force, Kostenrisiko bei KI und schwer nachvollziehbare Fehler. | Limits für Login, Versand, Synchronisierung, Recherche und KI; strukturierte Logs mit Korrelations-ID und ohne Geheimnisse. |
| P2 | `document.execCommand` ist veraltet. | Der Editor wird langfristig schwer wartbar und unsicherer zu kapseln. | Editor hinter einer klaren Komponente abstrahieren; erst dann gezielt ersetzen. |

## Produktlücken mit dem größten Nutzen

### E-Mail zum täglichen Arbeitsplatz machen

Der Posteingang ist technisch vorhanden, aber noch keine leistungsfähige Arbeitsansicht. Vor dem Ausbau um neue Module sollten diese Fähigkeiten kommen:

1. Suche und Filter nach Konto, Absender, Betreff, ungelesen, Zeitraum, KI-Priorität und Anhängen.
2. Konversationsansicht über `Message-ID`, `In-Reply-To` und `References`; gesendete Antworten, Anhänge und Entwürfe in einer Timeline.
3. Klare Bearbeitungszustände: gelesen/ungelesen, wichtig, archiviert, gelöscht und Follow-up.
4. Entwurfsautosave mit sichtbarem Speicherzeitpunkt sowie Wiederaufnahme abgebrochener Antworten.
5. Serverseitig validierte Empfänger-Chips; Warnung für externe Empfänger und Versand-Review mit Konto, Empfängern, Inhalt und Anhängen.
6. Echte Dashboard-Kennzahlen statt Platzhalter: ungelesene Nachrichten, fehlgeschlagene Synchronisierungen, offene Entwürfe und überfällige Aufgaben.

### CRM vom Datensatz zur Arbeitssteuerung entwickeln

- Firmen-Detailseite als 360°-Ansicht für Kontakte, Leads, Quellen, Recherche und Aktivitäten.
- Aufgaben mit Eigentümer, Fälligkeit, Erinnerung und Abschluss statt eines Freitextfelds „nächste Aktion“.
- Listen mit Suche, Filtern und gespeicherten Ansichten; danach eine einfache Kanban-Pipeline.
- Opt-out-/Sperrstatus beim Kontakt, beim Lead und unmittelbar vor einer Ansprache prominent anzeigen.
- Import/Export erst nach Duplikatvorschau, Fehlerbericht und klaren Berechtigungen ergänzen.
- Bei KI-Recherche Quellen, Abrufzeit, Unsicherheit und menschlichen Prüfstatus getrennt speichern.

### Bedienoberfläche fokussieren

- Gemeinsame App-Shell mit konsistenter Hauptnavigation, Seitenkopf und einer klaren primären Aktion pro Seite.
- Dreispaltiger Mail-Arbeitsbereich: Konto/Ordner, Nachrichtenliste, Detail/KI-Kontext; mobil als aufeinanderfolgende Ansichten.
- Einheitliche Status-Badges für Fehler, laufende Jobs, Erfolg, KI-Vorschlag und Opt-out.
- Formulare in überschaubare Abschnitte oder Tabs teilen; Fehler direkt am Feld anzeigen.
- Zugänglichkeit als Akzeptanzkriterium: Labels, Tastaturbedienung, sichtbarer Fokus, ausreichender Kontrast und verständliche Fehlermeldungen.

## Empfohlener Umsetzungsplan

### Etappe 0 – Sicherheitsbasis (vor einem breiteren Testbetrieb)

- Secret-Datei prüfen und gegebenenfalls Schlüssel rotieren.
- produktionssichere Konfiguration verpflichtend machen.
- CSRF-Schutz, Rate-Limits und serverseitige Eingabevalidierung ergänzen.
- HTML-/Anhangsrichtlinie und SSRF-Schutz umsetzen.
- Tests für Berechtigungen, Konto-Zuordnung, Versand-Gate, Opt-out, CSRF und fehlerhafte Provider-Verbindungen ergänzen.

**Fertig, wenn:** Ein nicht berechtigter Benutzer weder Daten eines fremden Kontos sieht noch sendet; schreibende Browser-Anfragen ohne CSRF-Token scheitern; Geheimnisse werden nicht protokolliert.

### Etappe 1 – Betriebssicherheit und Beobachtbarkeit

- Alembic-Migrationen, PostgreSQL-Konfiguration, Backup-/Restore-Test und Aufbewahrungsregeln.
- Persistente Job-Queue für Synchronisierung, Recherche und KI mit Retry/Backoff.
- strukturierte Logs, Korrelations-IDs, Fehlerstatus sowie ein kleines Betriebs-Dashboard.
- Zeitüberschreitungen, Abbruch und nachvollziehbare Fehlermeldungen für externe Dienste.

**Fertig, wenn:** Ein Neustart keinen laufenden Job unbemerkt verliert und ein fehlgeschlagener Job gezielt erneut gestartet werden kann.

### Etappe 2 – Mail-Workflow

- Suche, Filter, Sortierung, ungelesene Zustände und Sammelaktionen.
- Thread-Modell, Anhänge und Versandhistorie.
- Entwurfsautosave, Empfängerprüfung und finaler Versanddialog.
- echte Kennzahlen im Dashboard.

**Fertig, wenn:** Eine neue Nachricht binnen Sekunden gefunden, verstanden, beantwortet und sicher versendet werden kann, ohne zwischen unverbundenen Seiten zu wechseln.

### Etappe 3 – CRM-Workflow und UI-Konsolidierung

- Firmen- und Lead-Detailansichten, Aufgaben/Wiedervorlagen und Aktivitäten-Timeline.
- konsistente Navigation und Listen; mobile Detailansichten.
- Quellen- und Opt-out-Prüfung im gesamten Kontaktprozess.

**Fertig, wenn:** Vertrieb einen Lead vom Rechercheergebnis bis zur nächsten geprüften Aktion durchgehend bearbeiten kann.

### Etappe 4 – KI-Transparenz

- Tonalität, Sprache und Länge als kontrollierte Auswahl.
- Varianten und Versionen von KI-Entwürfen; Übernahme, Vergleich und Wiederherstellung.
- Modell, Laufzeit, Kosten/Token und Fehlerzustand pro Anfrage erfassen.
- zentral versionierte Prompts mit Tests und Freigabeprozess.

**Fertig, wenn:** Jeder KI-Inhalt als überprüfbarer Vorschlag erkennbar, einem Modell/Prompt zuordenbar und vor Versand editierbar ist.

## Optionales Helpdesk-Modul – erst nach Etappe 2

Helpdesk sollte kein Umbau des CRM werden, sondern ein unabhängig aktivierbares Modul. Es darf CRM und Mail integrieren, aber nicht von ihnen abhängig sein.

### Startumfang

- Tickets aus E-Mail, Formular und manueller Anlage
- Ticketnummer, Status, Priorität, Kategorie, Team, Zuständigkeit, Fälligkeit und SLA
- Ticketdetail mit Timeline aus öffentlichen Antworten, internen Notizen, Anhängen und Statuswechseln
- eindeutige Aktionen: übernehmen, zuweisen, zurückstellen, eskalieren und schließen
- Suche und Filter nach Status, Priorität, Team, Bearbeiter und Fälligkeit
- KI nur für Klassifikation, Zusammenfassung und Antwortentwürfe; der Mensch bleibt Versandinstanz

### Späterer Ausbau

- Ticket-Zusammenführung/-Aufteilung mit vollständiger Historie
- SLA-Warnungen, Wiedervorlagen, Vorlagen/Makros und Wissensbasis
- Reporting zu Erstreaktion, Lösung, Backlog und SLA-Einhaltung
- weitere Kanäle wie Formular, Chat oder Telefonnotiz

## Modulare Architektur

| Modul | Aufgabe | Voraussetzung |
| --- | --- | --- |
| Core | Benutzer, Rollen, Berechtigungen, Einstellungen, Audit, Jobs | keine |
| Mail | Konten, Synchronisierung, Nachrichten, Entwürfe, Versand | Core |
| KI | Provider, Modelle, Prompts, Ausführungen und Kosten | Core; nutzbar durch Fachmodule |
| CRM | Firmen, Kontakte, Leads, Aufgaben, Aktivitäten | Core; Mail/KI optional |
| Helpdesk | Tickets, Teams, SLA, Support-Timeline, Wissensbasis | Core; Mail/KI/CRM optional |
| Reporting | Kennzahlen, Exporte, Aufbewahrung | Core; Daten aus aktiven Modulen |

Regeln dafür:

- Jedes Modul besitzt eigene Routen, Services, Modelle, Migrationen und Tests.
- Fachmodule greifen über klar definierte Services oder Events aufeinander zu, nicht direkt auf interne Tabellen.
- Konfiguration steuert aktivierte Module; Navigation, Berechtigungen und Dashboard-Karten folgen dieser Konfiguration.
- Beim Deaktivieren wird ein Modul ausgeblendet und neue Verarbeitung gestoppt. Daten bleiben erhalten, bis eine explizite Archivierungs- oder Löschregel greift.
- KI ist eine optionale Fähigkeit, keine Voraussetzung für Mail, CRM oder Helpdesk.

## Messbare Qualitätsziele für den nächsten Meilenstein

- Alle schreibenden Routen sind gegen CSRF geschützt und relevante Limits sind getestet.
- E-Mail- und CRM-Berechtigungen sind für erlaubte und verbotene Fälle automatisiert geprüft.
- Jede asynchrone Aufgabe hat Status, Fehlergrund, Retry und Audit-Spur.
- Ein Mail-Thread zeigt Original, Antworten, Anhänge und Entwürfe vollständig in einer Ansicht.
- Der Versandreview zeigt Absenderkonto, alle Empfänger, Betreff, Inhalt und Anhänge vor der finalen Bestätigung.
- Dashboard-Zahlen stammen aus der Datenbank und sind nicht statisch.
- Der Testbestand deckt die sicherheitskritischen Flows ab und läuft in der Projektumgebung reproduzierbar.

## Verifikation dieses Stands

Die vorhandene Testsuite wurde in der lokalen virtuellen Umgebung ausgeführt:

```text
4 passed in 2.41s
```

Die vier Tests sind ein guter Smoke-Test, aber noch kein Sicherheits-, Last- oder Usability-Nachweis. Vor einem Produktivbetrieb sind insbesondere die Punkte aus Etappe 0 und Etappe 1 zwingend.
