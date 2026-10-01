# Externe LLM-API (Nova)

Stand: 01.10.2026. Vom Benutzer bereitgestellte Schnittstellenbeschreibung; in dieser Sitzung nicht am API-Server überprüft. Als Referenz für eine mögliche AboroDesk-Anbindung gespeichert. Die Anbindung ist noch nicht implementiert.

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

Eine spätere Anbindung benötigt eine eigene Providerkonfiguration und einen Adapter für die bestehenden KI-Aufgaben. Backendwahl (`local` oder `bedrock`) muss ausdrücklich konfiguriert werden; kein stiller Fallback. Noch kein Nova-Key für AboroDesk hinterlegt und keine Serverkonfiguration geändert.
