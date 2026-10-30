import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from dealdesk import llm
from dealdesk.app import create_app
from dealdesk.boundary import LocalDemoBoundary, MAX_BODY_BYTES
from dealdesk.config import LOCAL_MODEL, Settings
from dealdesk.state import CHAT_RETENTION


def test_only_loopback_bindings(settings):
    settings.host = "0.0.0.0"
    with pytest.raises(ValueError, match="loopback"):
        create_app(settings)


def test_browser_origin_and_host_before_state_change(client):
    navigation = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate",
                  "Sec-Fetch-Dest": "document"}
    assert client.get("/", headers=navigation).status_code == 200
    assert client.post("/api/reset", headers=navigation).status_code == 403
    client.post("/api/chat", json={"message": "Recommend a price"})
    before = client.get("/api/state").json()
    assert client.post("/api/reset", headers={"Origin": "https://outside.invalid"}).status_code == 403
    assert client.post("/api/reset", headers={"Host": "outside.invalid"}).status_code == 400
    assert client.post("/api/reset", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/api/state").json() == before
    assert client.post("/api/reset", headers={"Origin": "http://127.0.0.1"}).status_code == 200
    assert client.post("/api/tools/forecast_costs", json={"arguments": {"horizon": 1}}).status_code == 200


@pytest.mark.parametrize("name,arguments", [
    ("forecast_costs", {"horizon": 1_000_000}),
    ("forecast_costs", {"horizon": True}),
    ("search_documents", {"limit": 21}),
    ("search_documents", {"query": "x" * 2001}),
    ("search_documents", {"doc_types": ["x"] * 11}),
    ("price_deal", {"offer_revenue": "1" * 65}),
    ("price_deal", {"unrecognized": "value"}),
])
def test_tool_bounds_before_persistence(client, name, arguments):
    assert client.post(f"/api/tools/{name}", json={"arguments": arguments}).status_code == 422
    assert client.get("/api/state").json()["messages"] == []


def test_http_body_bound_including_chunked_requests():
    called, sent = [], []

    async def app(*args):
        called.append(True)

    async def run():
        chunks = iter([{ "type": "http.request", "body": b"x" * 9000, "more_body": True},
                       { "type": "http.request", "body": b"x" * 9000, "more_body": False}])
        async def receive():
            return next(chunks)
        async def send(message):
            sent.append(message)
        await LocalDemoBoundary(app, "127.0.0.1")(
            {"type": "http", "scheme": "http", "headers": [(b"host", b"127.0.0.1")]}, receive, send)
    asyncio.run(run())
    assert not called
    assert sent[0]["status"] == 413


def test_transient_retention_preserves_quote_audit(client):
    client.post("/api/chat", json={"message": "Recommend a price"})
    store = client.app.state.store
    quotes = store.quote_versions("SYN-REFERENCE-001")
    for i in range(CHAT_RETENTION + 10):
        store.add_message("user", {"text": str(i)})
    assert len(store.messages()) == CHAT_RETENTION
    assert store.quote_versions("SYN-REFERENCE-001") == quotes
    assert quotes


def test_model_response_bound_and_slots_released(settings, monkeypatch):
    settings.mode, settings.llm_model = LOCAL_MODEL, "mock"
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, count): return b"x" * count
    monkeypatch.setattr(llm._OPENER, "open", lambda *a, **kw: Response())
    for _ in range(3):
        with pytest.raises(llm.LocalModelError, match="1 MiB"):
            llm._request(settings, "GET", "/models")


def test_model_concurrency_limit(settings, monkeypatch):
    settings.mode, settings.llm_model = LOCAL_MODEL, "mock"
    started = threading.Barrier(3)
    release = threading.Event()
    class Response:
        def __enter__(self):
            started.wait(timeout=5)
            release.wait(timeout=5)
            return self
        def __exit__(self, *args): pass
        def read(self, count): return b'{}'
    monkeypatch.setattr(llm._OPENER, "open", lambda *a, **kw: Response())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(llm._request, settings, "GET", "/models") for _ in range(2)]
        started.wait(timeout=5)
        try:
            with pytest.raises(llm.LocalModelError, match="busy"):
                llm._request(settings, "GET", "/models")
        finally:
            release.set()
        assert [f.result() for f in futures] == [{}, {}]
