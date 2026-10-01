# AboroDesk – Übergabe für die Weiterarbeit zu Hause

Stand: 30.09.2026, Europe/Berlin. Dieses Dokument ist der Einstieg für die nächste Arbeitssitzung. Es enthält keine Passwörter, Datenbank-Zugangsdaten oder API-Schlüssel.

**Aktueller Nachtrag 01.10.2026:** Der API-/Serverabgleich ist in [SERVER-ABGLEICH-2026-10-01.md](SERVER-ABGLEICH-2026-10-01.md) dokumentiert. Qwen-Auswertungen für E-Mail, Helpdesk und CRM wurden erfolgreich geprüft, einschließlich Worker, gespeicherter Produktwerte und Webanzeige. Persistenzüberschreibungen und der bekannte Firmenlöschbefehl wurden korrigiert. Die folgenden älteren Offen-Punkte sind als historische Bestandsaufnahme zu lesen; für die nächsten Schritte zuerst den neuen Serverbericht verwenden.

## Ziel und verbindliche Entscheidungen

Aktualisierung 01.10.2026: Auf Wunsch des Benutzers wurde Nova/Qwen vorübergehend aktiviert (`AI_PROVIDER=nova`, `NOVA_MODEL=local`). Adapter `app/nova.py` bedient die bisherigen KI-Aufgaben; Schlüssel nur in der Serverkonfiguration. Authentifizierte Modellabfrage erfolgreich (HTTP 200); Generierung bisher durch HTTP 429 blockiert. Details und Rückwechsel in `docs/externe-llm-api.md`. Die nachfolgende ältere Aussage „noch nicht implementiert“ beschreibt den Stand vor dieser Umstellung.

Nachtrag vom 01.10.2026: Die vom Benutzer bereitgestellte Nova-Schnittstelle ist in [externe-llm-api.md](externe-llm-api.md) dokumentiert. Basis `https://ki.ml-projekt.de/v1`, Bearer-Authentifizierung mit eigenem Nova-Key, explizite Backends `local` (Qwen) und `bedrock`. Diese zusätzliche KI-Anbindung ist noch nicht implementiert. Der direkte AboroDesk-Bedrock-Test vom 01.10.2026 konnte die Schlüsseldatei lesen, wurde von AWS aber mit 403 / `AccessDeniedException` und „Authentication failed: Please make sure your API Key is valid.“ abgelehnt.

- AboroDesk soll Arbeit erleichtern und wiederkehrende Abläufe automatisieren.
- Einzelkundeninstallation, **keine Mandantenlösung**. Jede Kundeninstallation erhält eigene Daten und Konfiguration.
- Modular bleiben: E-Mail, CRM, Helpdesk, Marketing und weitere Funktionen sollen unabhängig aktivierbar sein. Rollenrechte existieren; vollständig unabhängige Modulabschaltung bleibt zu überprüfen.
- Langfristig verkaufbare Software mit einfacher Installation, dokumentierten Updates, Backups und Wiederherstellung.
- ABoroOffice fällt als Vertriebsprodukt vorerst weg. Die Firmenrecherche berücksichtigt **AboroDesk, ABoroLMS, CloudShare und HelpDesk**.
- KI erstellt Vorschläge. Recherche löst keinen automatischen E-Mail-Versand aus. Kontakte und Inhalte werden vor Verwendung geprüft.

## Projekt und Server

| Bereich | Stand |
|---|---|
| Lokaler Projektordner | `C:\Users\aborowczak\PycharmProjects\KI-Email` |
| GitHub | https://github.com/aboro72/KI-Email.git |
| Entwicklungsbranch | `master` |
| Server | `212.44.166.238` |
| SSH-Benutzer | `aboro72_11`, sudo ohne Passwort konfiguriert |
| Laufende App | `/opt/aborodesk` |
| App-Benutzer / Gruppe | `web29` / `client2` |
| App-Dienst | `aborodesk.service`, intern Port `8011` |
| Hintergrunddienst | `aborodesk-worker.service` |
| Serverkonfiguration | `/etc/aborodesk/aborodesk.env` |
| Bedrock-Schlüsseldatei | `/etc/aborodesk/bedrock-long-term-api-key.csv` |
| Produktionsdatenbank | MongoDB, Datenbank `aborodesk` |
| Backups | `/var/backups/aborodesk/mongodb/` |

FTP-Dateien wurden ursprünglich nach `/web/app/` kopiert. Die aktuell laufende Serverinstallation liegt unter `/opt/aborodesk`; diese beiden Pfade nicht verwechseln. Zugangsdaten separat aus der vorhandenen Konfiguration beziehungsweise dem Passwortspeicher beziehen.

## Was umgesetzt wurde

### E-Mail, Rechte und Grundsystem

- Login, Benutzer, Rollen und Modulberechtigungen.
- IMAP/SMTP-Konten, Verbindungstest, Posteingang, Suche/Filter, Entwürfe, Versand, Papierkorb.
- KI-Analyse und Antwortvorschläge mit manueller Prüfung/Freigabe.
- Checkboxen im Benutzerformular korrigiert: Es ist nicht erforderlich, ein fremdes oder das erste Postfach auszuwählen.
- Postfachauswahl: Admin-Rolle sieht alle aktiven Konten; andere Benutzer sehen ihre zugewiesenen Konten.
- Postfach `admin@aborosoft.com` wurde dem betreffenden Benutzer zusätzlich zugewiesen.
- Position/Beschriftung des Filters „Nur ungelesen“ verbessert.

### CRM und automatische Firmenrecherche

- Firmen, Kontakte, Leads und Aktivitäten mit Detailseiten.
- Website-Recherche durch Bedrock; Zusammenfassung, Beobachtungen, Kontakte und Gesprächsvorschlag.
- Produktbewertung für alle vier Produkte in `app/prospect_scoring.py`.
- Speicherung in `Company.product_fit_json`, `best_product`, `best_product_score` und Firmennotizen.
- Bewertung erfolgt derzeit regelbasiert aus Website- und KI-Texten: Kernbegriffe 15 Punkte, Zusatzbegriffe 10 Punkte, maximal 100. Die KI-Zusammenfassung ist davon getrennt. Es handelt sich nicht um einen nachgewiesenen Kaufbedarf.
- Schwellen: 70–100 sehr gut, 45–69 interessant, 20–44 beobachten, 0–19 nicht priorisieren.
- Kandidatensuche in `scripts/discover_prospects.py`, DuckDuckGo mit Bing-Fallback und Domainprüfung gegen bestehende Firmen.
- Timer `aborodesk-prospect-discovery.timer`: ungefähr alle 12 Stunden, nach Boot ab 15 Minuten, zusätzlich bis 30 Minuten Zufallsverzögerung. Auf dem Server zwei Treffer pro Suchanfrage konfiguriert.
- Verschärfung: bekannte Verzeichnisse, Suchportale, soziale Netzwerke und einige Medienseiten ausgeschlossen; Startseite muss abrufbar sein und mindestens 20 Produktpunkte erreichen.
- Letzter dokumentierter Dry-Run der verschärften Suche: keine neuen Kandidaten; mehrere fachfremde Seiten verworfen.
- Firmenlöschbutton auf der Detailseite, Bestätigung und serverseitiges Recht `CRM_MANAGE`; Audit-Eintrag vorgesehen. **Bekannte Fehler hierzu siehe nächste Schritte.**

### Helpdesk und Marketing

- Helpdesk-Grundmodul: Tickets, Kundenangaben, Priorität, Status, Supportlevel, Agentenzuweisung, Kommentare, KI-Vorschläge, Wissensartikel.
- Teamleitung darf andere Agenten zuweisen; Artikelverwaltung hat ein eigenes Recht.
- Marketing-Grundmodul: Kampagnenentwurf, Absenderwahl, CRM-Empfänger, Opt-out-Prüfung, Vorschau, manuelle Versandbestätigung und Empfängerstatus.

### Automatisierung und Suche

- Ereignisse, Regeln und protokollierte Automationsläufe als Grundlage.
- Job-Warteschlange mit registrierten Handlern für Postfach-Synchronisation, CRM-Recherche und Helpdesk-KI.
- Aufgaben, Fälligkeiten und einmalige Erinnerungen durch den Worker.
- Benachrichtigungen und zentrale Suche einschließlich Firmen, Kontakte, E-Mails, Tickets, Kampagnen, Leads und Wissensartikeln.
- Eine ständig sichtbare Suchleiste in allen Hauptnavigationen ist noch offen.

### Installation, Updates, Backups

- Installationsscripts und manuelle Anleitungen für ISPConfig3 und Einzelserver vorhanden; FTP-Pfad `/web/app/` berücksichtigt.
- Vorprüfung, Worker-Installation, Update-Timer und Backup-Timer vorhanden.
- Updateprüfung ursprünglich alle 20 Minuten eingerichtet, mit Sicherung, Healthcheck, Rollback und Dashboard-Anzeige.
- Updater um Eigentümer-/Gruppenbehandlung ergänzt, nachdem Dateirechte Dienststarts behinderten.
- MongoDB Database Tools auf dem Server installiert; täglicher Backup-Timer eingerichtet.
- Backup und echter Restore-Test in separater Datenbank erfolgreich: 14 Collections, 106 Dokumente. Testdatenbank anschließend entfernt. Dieser Test bestätigt den damaligen Backupstand, nicht sämtliche aktuellen Daten.
- Bedrock-Schlüsseldatei auf den Server übertragen, Eigentümer `root:client2`, Rechte `0640`. Zuvor scheiterten Firmenrecherchen am Dateizugriff.

### Hilfe für Benutzer und Administratoren

- Neue, angemeldeten Benutzern zugängliche Seite `/help`.
- Hilfe-Link in 28 vorhandenen Navigationen ergänzt.
- Anleitungen entsprechend Modulberechtigungen: E-Mail/KI, CRM/Recherche, Helpdesk, Marketing, Aufgaben, Suche und häufige Fragen.
- Verwaltungs- und Betriebshinweise nur für Benutzer mit `ADMIN_SETTINGS`.
- Datei `app/templates/help.html`; Route in `app/main.py`.
- Lokal als Commit `40c0b98` gespeichert und auf dem Server installiert.
- Prüfung: beide Rollenansichten erfolgreich gerendert; vorhandene Tests **9 bestanden**. Serverdienst aktiv, Healthcheck erfolgreich, `/help` ohne Anmeldung liefert 401.

## Aktueller Stand und Grenzen der Prüfung

Die letzte Serverprüfung nach Installation der Hilfeseite bestätigte eine erreichbare Anwendung. Sie war kein vollständiger Funktionstest sämtlicher Module.

Bei der letzten separaten Prüfung der Recherche standen 39 Firmen auf `pending`, ein Job auf `running`, 37 Jobs auf `queued` und eine Firma auf `completed`. Dieser Stand blieb bei mehreren Abfragen unverändert. Die frühere Aussage, dies sei lediglich eine normale Wartezeit von 20–40 Minuten, ist nicht ausreichend belegt. **Die Recherche darf noch nicht als zuverlässig funktionierend gelten.**

Die erste Suche erzeugte auch unpassende Treffer wie Medienseiten, Verzeichnisse und Lexware. Vorhandene Firmen wurden bei der Filterverschärfung nicht gelöscht. Lexware wurde nicht nachweislich entfernt; der Benutzer soll dies über die Löschfunktion tun können, sobald diese korrekt getestet ist.

## Wichtigster nächster Schritt: Datenpersistenz und Worker korrigieren

### Nachtrag: Bedrock-Dateizugriff korrigiert

Am 30.09.2026 wurde der erneut gemeldete `Permission denied` geprüft: `/etc/aborodesk` hatte `root:root` und `0750`, während die App unter `web29:client2` läuft. Die Schlüsseldatei war bereits `root:client2` mit `0640`. Die Verzeichnisgruppe wurde auf `client2` korrigiert, der Modus blieb `0750`. Ein Öffnungstest als `web29:client2` war erfolgreich. Die Webanwendung wurde neu gestartet. Diese Rechtekorrektur behebt den Dateizugriff; sie bestätigt weder die Bedrock-Anmeldung noch eine funktionierende Recherchequeue. Die Installationsscripts setzen die Verzeichnisgruppe bereits korrekt; die Ursache des abweichenden Serverstands ist nicht geklärt.

1. **Zuerst ein aktuelles Backup erstellen und prüfen.** Danach parallele Schreibprozesse für Diagnose/Umstellung kontrolliert anhalten.
2. `app/db.py` überarbeiten: Jeder Prozess lädt MongoDB beim Start in eine eigene SQLite-In-Memory-Datenbank. Jeder Commit löscht die MongoDB-Collections und schreibt den gesamten lokalen Bestand zurück. Webapp, Worker und Suchscript können dadurch gegenseitig neuere Daten überschreiben. Das ist anhand des Codes bestätigt; welche Daten bereits betroffen sind, muss untersucht werden.
3. Ziel: MongoDB atomar und direkt für produktive Daten/Queue verwenden, ohne vollständiges Löschen/Neuschreiben bei jedem Commit. Mehrere Prozesse müssen denselben aktuellen Zustand sehen. Eine vollständige Umstellung braucht durchgängige Prüfung der bisher SQLAlchemy-basierten Zugriffe.
4. Worker prüfen: Job atomar beanspruchen, Zeitlimits für externe Aufrufe, aussagekräftige Logs, Wiederholungen mit Abstand, Wiederaufnahme verwaister `running`-Jobs nach Neustart.
5. `research_company_background()` verschluckt Exceptions nach Setzen des Firmenstatus. Dadurch kann der Job als `completed` gelten, obwohl die Firma `failed` ist. Fehlerstatus und Jobstatus konsistent machen.
6. Mit einer einzelnen geeigneten Testfirma prüfen: `pending → running → completed`, Produktwerte gespeichert und gleichzeitig im Web sichtbar. Fehlerfall und Neustart separat testen; erst dann übrige Recherchejobs wieder starten.

## Danach: Firmenlöschung reparieren und vollständig testen

- In `app/main.py`, Funktion `delete_company()`, steht `delete(MarketingRecipient)...values(contact_id=None)`. `DELETE` unterstützt kein `.values()`. Erforderlich ist hier ein `UPDATE`, um die optionale Kontaktverknüpfung zu lösen. Der Fehler tritt bei Firmen mit Kontakten auf.
- Aktivitäten nicht nur anhand `company_id`, sondern auch anhand zugehöriger `contact_id` und `lead_id` berücksichtigen.
- Referenzen aus anderen Leads/Kampagnen auf entfernte Kontakte prüfen; Kampagnenhistorie wie zugesagt erhalten.
- Löschung parallel zu aktiver Recherche absichern. Derzeit wird ein laufender Job entfernt, aber sein Handler kann noch mit einem alten Firmenobjekt arbeiten. Neustarts können außerdem Jobs in `running` belassen.
- Gelöschte/abgelehnte Domains als Ausschluss merken, damit Lexware oder andere unpassende Firmen nicht beim nächsten Suchlauf wieder angelegt werden. Diese Funktion existiert noch nicht.
- Bestehende neun Tests decken die Löschfunktion nicht ab. Verifizieren: Firma ohne Kontakte, mit Kontakten/Leads/Aktivitäten, mit Kampagnenhistorie, laufender Recherche, fehlender Berechtigung.

## Weitere nächste Schritte in sinnvoller Reihenfolge

1. GitHub und Serverstand abgleichen, danach reproduzierbar aus Git deployen. Direkt kopierte Serverdateien können bei einem Update durch ältere Git-Dateien ersetzt werden.
2. Suchqualität verbessern: ausschließlich tatsächliche Suchresultate parsen statt beliebiger Seitenlinks; Firmenname und Herkunft sauber erfassen; productbezogene Branchen-/Bedarfssignale verlangen; Konkurrenten/Portale ausschließen. Die aktuelle 20-Punkte-Regel prüft den besten beliebigen Produktwert, nicht zwingend das gesuchte Produkt. Domain-Normalisierung und Ablehnungslisten erweitern.
3. Recherchefortschritt im CRM verständlich anzeigen: „Wartet“, „In Bearbeitung“, „Abgeschlossen“, „Fehlgeschlagen“, Zeitstempel und konkrete Fehler; Administratoransicht für Queue und manuelle Wiederholung.
4. Produkt-Fit separat lesbar darstellen, KI-Vermutung von belegten Website-Signalen trennen, Kontakte/Lead-Erzeugung an ausreichenden Fit binden. Der bisherige Prompt und nächste Aktionen sind noch teilweise LMS-orientiert.
5. Ereignis-Benachrichtigungen für die wesentlichen CRM-/Helpdesk-/E-Mail-Vorgänge vervollständigen; Automationsregeln nutzbar verwalten.
6. Dauerhafte Suchleiste; einheitliche Navigation und Benennung. In einzelnen Templates stehen noch „AboroDesk Developer“ oder alte Produktnamen.
7. Helpdesk: E-Mail-zu-Ticket, Antwortworkflow, SLA-Fristen, Eskalationen und Vorlagen.
8. CRM: Pipeline, Wiedervorlagen, Import/Export und bessere Dublettenbehandlung.
9. Marketing: Zielgruppen, Vorlagen, Abmeldelinks, geplante freigegebene Versände und Auswertungen.
10. Verkaufsreife: unabhängige Modulabschaltung prüfen, frische ISPConfig3-/Einzelserverinstallation testen, Migration/Upgrade absichern, Installations- und Betriebsanleitungen aktualisieren.

Optional danach: grafischer Installationsassistent, 2FA, Kundenportal, PWA, Kalender-/Microsoft-365-/Google-Anbindung, Regel-Editor, Lizenzaktivierung nach Geschäftsmodell.

## GitHub und Weiterarbeit zu Hause

Am Beginn dieser Übergabeprüfung enthielt GitHub `master` bereits Commit `b630269` (Firmenlöschung). Der lokale Stand war mit `40c0b98` (Hilfeseite) einen Commit voraus. Frühere Pushversuche scheiterten mit 403; dieser ältere Fehler bedeutet nicht, dass alle älteren Änderungen noch fehlen. Die Erreichbarkeit des Repositories wurde jetzt mit `git ls-remote` bestätigt. Ein erfolgreicher Push dieser Übergabe ist erst nach tatsächlicher Ausführung bestätigt.

Zu Hause nach erfolgreichem Push:

```bash
git clone https://github.com/aboro72/KI-Email.git
cd KI-Email
git log -5 --oneline
```

**Push-Ergebnis dieser Sitzung:** `git push origin master` ist erneut mit HTTP 403 gescheitert: Schreibzugriff für das angemeldete Konto `ML-PIT` auf `aboro72/KI-Email` verweigert. Hilfeseite und diese Übergabe sind lokal committed, aber noch nicht auf GitHub. Vor Weiterarbeit am Heim-PC entweder GitHub-Anmeldung/Schreibrechte korrigieren und erneut pushen oder den lokalen Projektstand separat mitnehmen. Diese Übergabe wird zusätzlich im SSH-Benutzerverzeichnis des Servers hinterlegt, damit sie von zu Hause abrufbar ist; sie allein ersetzt nicht den aktuellen Quellcode.

Bei vorhandenem Checkout zuerst `git status` prüfen, eigene Änderungen erhalten, dann `git pull --ff-only`. Diese Datei lesen und beim Abschnitt „Datenpersistenz und Worker korrigieren“ fortsetzen. Produktionskonfiguration und Schlüsseldatei gehören nicht in Git und müssen separat verfügbar sein.

## Nützliche Serverprüfungen

```bash
ssh aboro72_11@212.44.166.238
sudo systemctl status aborodesk.service aborodesk-worker.service
sudo journalctl -u aborodesk-worker.service -n 100 --no-pager
sudo systemctl list-timers --all
curl -fsS http://127.0.0.1:8011/health
```

Während der ungeklärten Persistenzprobleme keine zusätzlichen schreibenden Diagnoseprozesse starten und nicht pauschal alle Jobs neu einreihen. Konfiguration und Schlüsseldateien nicht in Ausgaben oder Dokumente kopieren.

## Wichtige Dateien

- `app/main.py`: Webrouten, Rechteprüfung, Firmenrecherche, Firmenlöschung, Hilfe.
- `app/models.py`: Datenmodelle und Produkt-Fit-Felder.
- `app/db.py`: aktuelle MongoDB-/SQLite-Persistenz; zuerst korrigieren.
- `app/jobs.py`, `app/worker.py`, `app/job_handlers.py`: Queue und Verarbeitung.
- `app/bedrock.py`: KI-Zugang und Prompts.
- `app/prospect_scoring.py`: Produktkriterien und Scores.
- `scripts/discover_prospects.py`: automatische Kandidatensuche.
- `app/templates/help.html`: Benutzer-/Administratorhilfe.
- `deploy/ispconfig3/installation.md`, `deploy/single-server/installation.md`: Installationsanleitungen.
- `deploy/install-worker.sh`, `deploy/install-prospect-discovery-timer.sh`: Hintergrunddienste.
- `deploy/update.sh`, `deploy/install-update-timer.sh`: Updates.
- `deploy/backup-mongodb.sh`, `deploy/restore-mongodb.sh`, `deploy/install-backup-timer.sh`: Backup/Restore.
- `docs/produkt-recherche-kriterien.md`: Produktrecherche.
- `docs/fortschritt-und-roadmap.md`: ältere Roadmap; teils überholte Offen-Punkte.
- `docs/architecture.md`: ursprünglicher Entwurf, kein verlässlicher aktueller Betriebsstand.

## Startauftrag für die nächste Sitzung

> Lies docs/UEBERGABE-2026-09-30.md vollständig. Arbeite an AboroDesk als modularer Einzelkundenlösung weiter. Sichere zuerst den aktuellen Produktionsstand, behebe die prozessübergreifende MongoDB-Persistenz und prüfe den Worker mit einer einzelnen Firma. Danach repariere und teste die Firmenlöschung einschließlich Kampagnenreferenzen, aktiver Recherche und Domain-Ausschluss. Gleiche GitHub und Serverdateien ab. Melde nur Funktionen als fertig, deren tatsächlicher Ablauf geprüft wurde.
