"""Textadapter für Nova; vorhandene KI-Aufgaben behalten ihr Ausgabeformat."""

import httpx

from app.config import get_settings


class NovaClient:
    def converse(self, *, modelId, system, messages, inferenceConfig):
        settings = get_settings()
        if not settings.nova_api_key:
            raise RuntimeError("Nova-API-Key fehlt")
        if settings.nova_model not in {"local", "bedrock"}:
            raise RuntimeError("Nova-Backend muss local oder bedrock sein")
        if not settings.nova_base_url.startswith("https://"):
            raise RuntimeError("Nova benötigt eine HTTPS-Adresse")
        chat = [{"role": "system", "content": "\n".join(item["text"] for item in system)}]
        chat.extend({"role": item["role"], "content": "\n".join(block["text"] for block in item["content"])} for item in messages)
        payload = {
            "model": settings.nova_model,
            "messages": chat,
            "stream": False,
            "max_tokens": inferenceConfig.get("maxTokens", 1024),
            "temperature": inferenceConfig.get("temperature", 0.2),
        }
        try:
            response = httpx.post(
                settings.nova_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.nova_api_key},
                json=payload,
                timeout=httpx.Timeout(180, connect=10),
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise RuntimeError("Nova-Zeitlimit erreicht; Anfrage später erneut starten") from None
        except httpx.HTTPError:
            raise RuntimeError("Nova-Verbindung fehlgeschlagen") from None
        if response.status_code != 200:
            reasons = {401: "Zugang abgelehnt", 429: "Kapazität belegt; später erneut versuchen", 502: "Backendfehler", 503: "API deaktiviert"}
            raise RuntimeError(f"Nova: {reasons.get(response.status_code, 'Anfrage fehlgeschlagen')} (HTTP {response.status_code})")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise RuntimeError("Nova lieferte ein ungültiges Antwortformat") from None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Nova lieferte keinen Antworttext")
        return {"output": {"message": {"content": [{"text": content}]}}}
