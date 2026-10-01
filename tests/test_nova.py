from types import SimpleNamespace

import httpx
import pytest

from app import nova


def test_nova_maps_prompt_and_response_without_unsupported_fields(monkeypatch):
    monkeypatch.setattr(nova, "get_settings", lambda: SimpleNamespace(nova_api_key="test-key", nova_model="local", nova_base_url="https://example.invalid/v1"))
    def post(url, **kwargs):
        assert url == "https://example.invalid/v1/chat/completions"
        assert kwargs["json"] == {"model": "local", "messages": [{"role": "system", "content": "System"}, {"role": "user", "content": "Prompt"}], "stream": False, "max_tokens": 700, "temperature": 0.2}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"summary":"OK"}'}}]})
    monkeypatch.setattr(nova.httpx, "post", post)
    result = nova.NovaClient().converse(modelId="ignored", system=[{"text":"System"}], messages=[{"role":"user","content":[{"text":"Prompt"}]}], inferenceConfig={"maxTokens":700,"temperature":0.2})
    assert result["output"]["message"]["content"][0]["text"] == '{"summary":"OK"}'


def test_nova_auth_error_does_not_expose_backend_message(monkeypatch):
    monkeypatch.setattr(nova, "get_settings", lambda: SimpleNamespace(nova_api_key="secret", nova_model="local", nova_base_url="https://example.invalid/v1"))
    monkeypatch.setattr(nova.httpx, "post", lambda *args, **kwargs: httpx.Response(401, json={"error":{"message":"secret"}}))
    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        nova.NovaClient().converse(modelId="",system=[],messages=[],inferenceConfig={})
    assert "secret" not in str(error.value)
