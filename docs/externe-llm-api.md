# Externe LLM-API (Nova)

Stand: 01.10.2026. Vom Benutzer bereitgestellte Schnittstellenbeschreibung. AboroDesk-Anbindung und aktueller Prüfstand sind im letzten Abschnitt dokumentiert; nicht alle hier beschriebenen Endpunkte und Grenzen wurden separat überprüft.

## Basis und Authentifizierung

Die API läuft im bestehenden Flask-/FastAPI-Webserver. Über den vorhandenen HTTPS-Reverse-Proxy lautet die Basis-URL `https://ki.ml-projekt.de/v1`. Der llama.cpp-Port bleibt auf localhost. API-Aufrufe benötigen keine Browser-Session und kein CSRF-Token.

Alle Endpunkte benötigen `Authorization: Bearer <NOVA_API_KEY>`.

## Aktivierung auf dem Nova-Server

Mit `openssl rand -hex 32` einen eigenen Key erzeugen. `NOVA_API_KEY=<key>` in der vom Dienst geladenen Datei `/home/user/.config/nova/server.env` setzen und `sudo systemctl restart nova-web.service` ausführen. Eine `.env`-Datei wird vom Startskript nicht automatisch geladen.

Ohne Key mit mindestens 32 Zeichen bleibt die API deaktiviert (503). Den Key wie ein Passwort behandeln; er erlaubt Zugriffe auf beide Backends und kostenpflichtige Bedrock-Aufrufe. Bedrock verwendet die vorhandenen AWS-Zugangsdaten, Region und Modellkonfiguration des Nova-Servers.

## Aufrufe

`NOVA_API_KEY` im aufrufenden Terminal setzen. Beispiele:

```bash
curl https://ki.ml-projekt.de/v1/models \
  -H "Authorization: Bearer $NOVA_API_KEY"

curl https://ki.ml-projekt.de/v1/chat/completions \
  -H "Authorization: Bearer $NOVA_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"local","messages":[{"role":"user","content":"Hallo!"}],"max_tokens":512}'

curl -N https://ki.ml-projekt.de/v1/chat/completions \
  -H "Authorization: Bearer $NOVA_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"bedrock","messages":[{"role":"user","content":"Erkläre mir MQTT."}],"stream":true}'
```

`local` wählt Qwen über llama.cpp; `bedrock` wählt das konfigurierte AWS-Modell. Es gibt keinen automatischen Wechsel des Backends.

- `GET /v1/models` liefert die tatsächlichen Backend-Modellnamen.
- `GET /v1/openapi.json` liefert die maschinenlesbare Beschreibung (ebenfalls Bearer-geschützt).

## Request und Antwort

Erforderlich sind `model` und `messages`. Jede Nachricht enthält `role` und textuelles `content`.

Optionale Systemnachrichten stehen am Anfang und ersetzen den Nova-Systemprompt. Danach wechseln sich `user` und `assistant` ab; die letzte Nachricht muss `user` sein. Ohne Systemnachricht gilt der vorhandene Nova-Prompt.

Der gesamte Verlauf wird vom Aufrufer übergeben. Die API speichert keine Chats und bindet keine persönlichen Erinnerungen, Recherche oder Werkzeuge ein.

| Parameter | Bereich / Standard |
| --- | --- |
| `stream` | Boolean, `false` |
| `max_tokens` | 1–4096; lokal 1024, Bedrock 700 |
| `temperature` | 0–1; lokal 0,55, Bedrock 0,5 |
| `top_p` | größer 0 bis 1; lokal 0,9, Bedrock ohne Vorgabe |

Die JSON-Antwort enthält `id`, `object`, `created`, `model` und `choices[0].message.content`.

SSE liefert `chat.completion.chunk` mit `choices[0].delta.content`, Abschlusschunk und `data: [DONE]`. Nach Beginn eines Streams werden Fehler als JSON-`error`-Event übertragen. Der Client muss diese prüfen.

Die Adapter liefern keine Tokenstatistik und keinen genauen Abbruchgrund. `finish_reason: stop` kennzeichnet das Streamende und garantiert nicht, dass kein Tokenlimit erreicht wurde.

Die Formate orientieren sich an Chat Completions. Der unterstützte Umfang ist Textchat mit den hier genannten Parametern. Weitere Felder werden ausdrücklich abgewiesen. Bilder, Tool Calls, Embeddings und andere Endpunkte sind nicht Bestandteil dieser API.

## Grenzen und Fehler

Maximal 100 Nachrichten, 64 KiB Nachrichtentext, 256 KiB Request und vier gleichzeitige API-Aufrufe pro Serverprozess. Das lokale Modell ist zusätzlich gegen parallele Generierung gesperrt. Seine tatsächliche Kontextgrenze bleibt die konfigurierte llama.cpp-Kontextgröße.

Bei belegten Plätzen antwortet der Server mit 429 und `Retry-After: 5`.

Fehler enthalten `error.message`, `error.type` und `error.code`.

| Statuscode | Bedeutung |
| --- | --- |
| 400 | Validierung |
| 401 | Authentifizierung |
| 413 | Requestgröße |
| 429 | Kapazität |
| 502 | Backendfehler |
| 503 | deaktivierte API |

Zugangsdaten und interne Backendfehlermeldungen werden nicht ausgeliefert. Externe Aufrufe erfolgen über HTTPS. Für Keyrotation die Umgebungsvariable ersetzen und den Dienst neu starten.

## Einordnung für AboroDesk

Diese API bietet einen zusätzlichen möglichen KI-Zugang. Der Nova-API-Key ist unabhängig vom direkt in AboroDesk verwendeten Bedrock-Schlüssel. Ein funktionierender Nova-Zugang bestätigt nicht die Gültigkeit des AboroDesk-Bedrock-Schlüssels.

Am 01.10.2026 wurde die Anbindung in `app/nova.py` implementiert. Die bisherigen E-Mail-, Helpdesk- und Firmen-KI-Aufgaben verwenden bei `AI_PROVIDER=nova` diesen Adapter. Standard ohne Umstellung bleibt `bedrock`.

Auf dem AboroDesk-Server sind `AI_PROVIDER=nova`, `NOVA_BASE_URL=https://ki.ml-projekt.de/v1` und `NOVA_MODEL=local` gesetzt. Der vom Benutzer gelieferte Key wurde ausschließlich in `/etc/aborodesk/aborodesk.env` hinterlegt, nicht im Repository. Anwendung und Worker wurden neu gestartet und sind aktiv.

Die authentifizierte Modellabfrage lieferte HTTP 200 mit `local` und `bedrock`. Generierungstests erhielten bislang HTTP 429 (Kapazität belegt); eine erfolgreiche strukturierte Qwen-Auswertung ist noch nicht bestätigt. Der Adapter gibt verständliche Fehler ohne Zugangsdaten aus. Lokale Tests: 11 bestanden, einschließlich Request-/Antwortabbildung und Fehlerbehandlung.

Rückwechsel nach erfolgreicher Bedrock-Prüfung: `AI_PROVIDER=bedrock` in der Dienstkonfiguration setzen und Anwendung sowie Worker neu starten. Es gibt keinen automatischen Wechsel des Backends.

### Timeout, Wiederholungen und Reihenfolge (01.10.2026)

Nach erfolgreichem Serverabgleich gilt auf AboroDesk `NOVA_REQUEST_TIMEOUT=300`, intern llama.cpp 180 Sekunden und Nginx 300 Sekunden. Strukturierte E-Mail-, Helpdesk- und CRM-Auswertungen wurden erfolgreich getestet. Details: [SERVER-ABGLEICH-2026-10-01.md](SERVER-ABGLEICH-2026-10-01.md). Die früher dokumentierten 429-Tests beschreiben den Zustand vor diesem Abgleich.

- `NOVA_REQUEST_TIMEOUT=180`: HTTP-Timeout für Verbindungsaufbau, Lesen und Schreiben mindestens 180 Sekunden; höhere Werte sind konfigurierbar. Dies ist kein festes Gesamtlimit einschließlich Warteschlange und Wiederholungen.
- `NOVA_MAX_RETRIES=3`: bei 429 maximal drei Wiederholungen zusätzlich zum ersten Versuch. `Retry-After` wird beachtet, bei fehlendem/ungültigem Wert fünf Sekunden gewartet. Wartezeit mindestens fünf Sekunden; bei mehr als 60 Sekunden wird statt einer vorzeitigen Wiederholung ein Fehler zurückgegeben.
- `NOVA_REQUEST_LOCK_FILE=/var/lib/aborodesk/nova-request.lock`: gemeinsame Dateisperre auf dem Server für Webapp, Worker und weitere entsprechend konfigurierte Prozesse. Sie bleibt auch zwischen den Wiederholungen gehalten, damit nur eine Anfrage gleichzeitig läuft. Externe Nova-Nutzer sind nicht von dieser lokalen Sperre erfasst.
- Die Sperrdatei nicht während laufender Anfragen löschen oder ersetzen. Auf einem weiteren Server wäre eine serverübergreifende Sperre erforderlich.
- Lokale Tests: 14 bestanden, einschließlich Retry-Limit, Retry-After, erfolgreicher Wiederholung und serieller Ausführung.
