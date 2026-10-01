# Abgleich AboroDesk und Nova – 01.10.2026

## Ergebnis der tatsächlichen Tests

Die Verbindung zwischen AboroDesk (`212.44.166.238`) und Nova/Qwen (`212.44.166.235`, `https://ki.ml-projekt.de/v1`) wurde über HTTPS mit dem hinterlegten Bearer-Key geprüft. Keine Zugangsdaten in dieser Datei.

- Kurzer Textaufruf: HTTP 200.
- Strukturierte E-Mail-Analyse über den AboroDesk-Adapter: erfolgreich.
- Recherche mit ursprünglich etwa 30.000 Zeichen Quelltext: zunächst HTTP 502 wegen des lokalen Kontextlimits; nach Begrenzung erfolgreich, vollständiges JSON mit sechs Signalen (etwa 58 Sekunden im Test).
- Echter CRM-Auftrag für die bereits vorhandene Firma `comcave.de`: Worker-Job 47 und Firma 2 anschließend `completed`, `best_product=aborolms`, `best_product_score=100`.
- Ergebnis über die Webroute `/crm/companies/2` sichtbar; Dashboard, Hilfeseite und Firmendetail mit authentifiziertem Aufruf jeweils HTTP 200.
- Strukturierte Helpdesk-Analyse: erfolgreich.
- Lokale AboroDesk-Tests: 19 bestanden. Nova-API-/Local-LLM-Tests auf dem Jetson: 19 bestanden.

Die Produktbewertung bleibt eine Hypothese zur manuellen Prüfung, keine bestätigte Kaufabsicht. Der Test verwendete bestehende CRM-Daten und erzeugte keinen E-Mail-Versand.

## Änderungen am Nova-Server

Projekt: `/home/user/PycharmProjects/AI-System/jetson-avatar-assistant` (Schreibweise `PycharmProjects`, nicht `PyCharmProjects`).

- `app/llm/local.py`: interner llama.cpp-HTTP-Timeout von 120 auf 180 Sekunden erhöht. Stream-Fehler werden erkannt; `data: [DONE]` beendet den Stream.
- `tests/test_local_llm.py`: Timeout und Stream-Fehler ergänzt und geprüft.
- Nginx-Website `ki.ml-projekt.de`: `proxy_read_timeout` und `proxy_send_timeout` auf 300 Sekunden, Konfiguration getestet und neu geladen.
- Dienst `nova-web.service` neu gestartet. llama.cpp bleibt auf localhost (`18080`), Nova auf localhost (`5000`), externer Zugang über HTTPS.
- Bestehende API: vier Slots; lokales Modell wartet höchstens 30 Sekunden auf die gemeinsame Generation-Sperre, anschließend 429 mit `Retry-After: 5`. Diese Grenze bleibt erhalten.
- Der bestätigte SSH-Hostfingerabdruck wurde übernommen. Server hatte bereits umfangreiche uncommitted Änderungen; diese wurden erhalten. Die beiden angepassten Projektdateien wurden nicht zusammen mit den fremden Änderungen pauschal committed.

Rücksicherungen vor der Änderung:

- `app/llm/local.py.before-aborodesk-20261001`
- `tests/test_local_llm.py.before-aborodesk-20261001`
- `/etc/nginx/ki.ml-projekt.de.before-aborodesk-20261001`

## Änderungen am AboroDesk-Server

- Nova/Qwen bleibt aktiviert: `AI_PROVIDER=nova`, `NOVA_MODEL=local`.
- `NOVA_REQUEST_TIMEOUT=300` auf dem Server, weiterhin Mindestgrenze 180 im Adapter. Das längere Client-/Proxy-Limit berücksichtigt Modellwartezeit und Generierung.
- Höchstens drei Wiederholungen zusätzlich zum ersten Versuch bei 429. `Retry-After` beachtet, mindestens fünf Sekunden Pause, gemeinsame Dateisperre für Worker und Webapp.
- `app/nova.py`: lokale Quelltexte auf höchstens ungefähr 4500 Zeichen Gesamteingabe begrenzt, bei großer Ausgabeanforderung entsprechend weniger. Aufgaben-/JSON-Anweisungen stehen am Textanfang; Kürzung wird im Quelltext markiert. Das ist eine konservative Zeichenbegrenzung, keine exakte Tokenzählung. Direktes Bedrock und Nova-Backend `bedrock` werden nicht gekürzt.
- `app/db.py`: jede MongoDB-Sitzung erhält einen eigenen aktuellen Arbeitsbereich. Commits übertragen nur geänderte Felder, neue Zeilen und explizit entfernte Zeilen statt sämtliche Collections zu löschen. IDs werden über atomare MongoDB-Sequenzen reserviert. Späte Ergebnisse können einen bereits gelöschten Datensatz nicht wieder anlegen.
- Diese Persistenz bleibt ein SQLAlchemy-Kompatibilitätsadapter. Mehrere Dokumentänderungen eines Commit sind noch keine gemeinsame MongoDB-Transaktion; echte Transaktionen und Konfliktprüfung bei Änderungen desselben Feldes bleiben weitere Härtungspunkte.
- `app/main.py`: Startup verwendet eine korrekt gehaltene Sitzung; Rechercheexceptions werden nach Speichern des Fehlerstatus weitergereicht. Firmenlöschung löst Kampagnenverknüpfungen per UPDATE und entfernt auch indirekt zugehörige Aktivitäten.
- `app/worker.py`: neue Sitzung pro Zyklus, Wiederaufnahme unterbrochener `running`-Jobs beim Start des einzigen Workers, Statuslogging und Behandlung von Zyklusfehlern. Diese Wiederaufnahme ist für genau einen Worker ausgelegt.
- Testabdeckung ergänzt für gleichzeitige Sitzungen, Erhalt fremder Änderungen/neuer Datensätze, Verhinderung einer Wiederbelebung gelöschter Firmen, Startup, Firmenlöschung und lange Nova-Eingaben.

Backup vor der Persistenzänderung:

`/var/backups/aborodesk/mongodb/20261001T075108Z/aborodesk.archive.gz`

Vorherige AboroDesk-Dateien wurden zusätzlich unter `/tmp/db.py.before-abgleich-20261001`, `/tmp/main.py.before-abgleich-20261001`, `/tmp/worker.py.before-abgleich-20261001` und `/tmp/nova.py.before-abgleich-20261001` gesichert. `/tmp` ist kein dauerhafter Backup-Ort; das MongoDB-Archiv bleibt die Datensicherung.

## Noch zu verfolgen

29 frühere fehlgeschlagene Firmenrecherchen mit Bedrock-/Nova-Zugangsfehlern wurden erneut eingereiht. Erfolgreicher Testauftrag bedeutet nicht, dass bereits alle Firmen fertig recherchiert sind. Unzugängliche Websites und dauerhafte Fehler müssen weiterhin im CRM geprüft werden.

Die aktuelle Suche filtert bekannte Portale und Produktbegriffe, ist aber noch kein präziser Firmenfinder. Als nächste Produktverbesserungen: abgelehnte Domains merken, Ergebnislinks statt beliebiger Suchseitenlinks auslesen, gezielte Branchen-/Produktzuordnung und verständliche Fortschrittsanzeige.

GitHub-Push dieser Änderungen wurde erneut mit HTTP 403 abgelehnt (angemeldetes Konto `ML-PIT`, Repository `aboro72/KI-Email`). Code ist lokal committed und auf dem Server installiert. Direkt installierte Änderungen mit dem GitHub-Stand abgleichen, bevor ein späteres Update sie ersetzt. Nova-Änderungen separat im zugehörigen Projekt sichern; sie liegen nicht im AboroDesk-Repository.
