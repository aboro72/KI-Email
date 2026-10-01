from types import SimpleNamespace

import httpx
import pytest

from app import nova


@pytest.fixture(autouse=True)
def nova_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(nova, "get_settings", lambda: SimpleNamespace(nova_api_key="test-key", nova_model="local", nova_base_url="https://example.invalid/v1", nova_request_timeout=180, nova_max_retries=3, nova_request_lock_file=str(tmp_path / "nova.lock")))


def test_nova_maps_prompt_and_response_without_unsupported_fields(monkeypatch):
    def post(url, **kwargs):
        assert url == "https://example.invalid/v1/chat/completions"
        assert kwargs["timeout"].read >= 180
        assert kwargs["timeout"].connect >= 180
        assert kwargs["json"] == {"model": "local", "messages": [{"role": "system", "content": "System"}, {"role": "user", "content": "Prompt"}], "stream": False, "max_tokens": 700, "temperature": 0.2}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"summary":"OK"}'}}]})
    monkeypatch.setattr(nova.httpx, "post", post)
    result = nova.NovaClient().converse(modelId="ignored", system=[{"text":"System"}], messages=[{"role":"user","content":[{"text":"Prompt"}]}], inferenceConfig={"maxTokens":700,"temperature":0.2})
    assert result["output"]["message"]["content"][0]["text"] == '{"summary":"OK"}'


def test_nova_auth_error_does_not_expose_backend_message(monkeypatch):
    monkeypatch.setattr(nova.httpx, "post", lambda *args, **kwargs: httpx.Response(401, json={"error":{"message":"secret"}}))
    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        nova.NovaClient().converse(modelId="",system=[],messages=[],inferenceConfig={})
    assert "secret" not in str(error.value)


def test_capacity_retries_are_limited_and_honor_retry_after(monkeypatch):
    calls, waits = [], []
    def post(*args, **kwargs):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After":"7"})
    monkeypatch.setattr(nova.httpx, "post", post)
    monkeypatch.setattr(nova.time, "sleep", waits.append)
    with pytest.raises(RuntimeError, match="HTTP 429"):
        nova.NovaClient().converse(modelId="",system=[],messages=[],inferenceConfig={})
    assert len(calls) == 4
    assert waits == [7, 7, 7]


def test_capacity_retry_can_succeed(monkeypatch):
    replies = iter([httpx.Response(429, headers={"Retry-After":"5"}), httpx.Response(200,json={"choices":[{"message":{"content":"OK"}}]})])
    waits=[]
    monkeypatch.setattr(nova.httpx, "post", lambda *a, **k: next(replies))
    monkeypatch.setattr(nova.time, "sleep", waits.append)
    result=nova.NovaClient().converse(modelId="",system=[],messages=[],inferenceConfig={})
    assert result["output"]["message"]["content"][0]["text"] == "OK"
    assert waits == [5]


def test_concurrent_clients_are_serialized(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    active, maximum = 0, 0
    guard=threading.Lock()
    def post(*a, **k):
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
        threading.Event().wait(.03)
        with guard:
            active -= 1
        return httpx.Response(200,json={"choices":[{"message":{"content":"OK"}}]})
    monkeypatch.setattr(nova.httpx,"post",post)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _: nova.NovaClient().converse(modelId="",system=[],messages=[],inferenceConfig={}),range(3)))
    assert len(results)==3
    assert maximum==1
