"""End-to-end chatbot/API flow: answers are built from real tool outputs, not model text."""

import json
import shutil

import pytest

from dealdesk import agent as agent_module
from dealdesk import llm
from dealdesk.config import LOCAL_MODEL, is_local_endpoint
from dealdesk.costs import FEEDS_DIR, load_deal
from dealdesk.documents import load_corpus


def chat(client, message):
    response = client.post("/api/chat", json={"message": message})
    assert response.status_code == 200, response.text
    return response.json()


def assert_citations_are_real(reply):
    passages = {p.passage_id: p.text for p in load_corpus()}
    for citation in reply["citations"]:
        assert passages[citation["passage_id"]] == citation["text"]
        assert citation["doc_id"] and citation["section"] and citation["title"]


def test_index_and_status(client):
    page = client.get("/")
    assert page.status_code == 200 and "Reset demo" in page.text and "Apply supplier cost increase" in page.text
    status = client.get("/api/status").json()
    assert status["mode"] == "scripted" and status["mode_label"] == "Scripted demo mode"
    assert status["synthetic_data"] is True and status["single_user_demo"] is True
    assert status["active_feed"]["feed_version"] == "synthetic-costs-v1"


def test_full_demo_flow_then_reset_and_repeat(client):
    tools = client.app.state.tools
    for _ in range(2):
        # 1-3: recommendation with numbers bound to the engine's structured output.
        reply = chat(client, "Recommend a price for the demo customer.")["reply"]
        quote = reply["quote"]
        direct = tools.appraise("144000.00", 1)
        for key in ("offer_revenue", "discount_percent", "stress_margin_percent", "economic_floor",
                    "base_costs", "stress_costs", "approval_outcome"):
            assert quote[key] == direct[key]
        assert quote["approval_outcome"] == "representative_authority"
        assert reply["mode"] == "scripted"
        assert "price_deal" in [t["tool"] for t in reply["tool_calls"]]
        assert reply["citations"]
        assert_citations_are_real(reply)

        # 4-5: the $136,000 concession needs director approval and becomes quote v2.
        state = chat(client, "Can we offer $136,000?")
        quote = state["reply"]["quote"]
        assert (quote["offer_revenue"], quote["discount_percent"], quote["stress_margin_percent"]) == \
            ("136000.00", "15.00", "28.24")
        assert quote["approval_outcome"] == "director_approval_required" and quote["release_allowed"] is False
        assert [v["version"] for v in state["state"]["quote_versions"]] == [1, 2]

        # 6: forecast is the real forecast tool output.
        forecast = chat(client, "Show the supply and delivery cost forecast.")["reply"]["forecast"]
        assert forecast == tools.forecast_costs()

        # 7-8: supplier increase keeps the quote and adds a separate appraisal + review event.
        before = client.get("/api/state").json()["quote_versions"]
        applied = client.post("/api/cost-update").json()
        result = applied["result"]
        assert result["original"]["offer_revenue"] == "136000.00"
        assert result["original"]["stress_margin_percent"] == "28.24"
        revised = result["revised"]
        assert (revised["offer_revenue"], revised["stress_costs"]["total"], revised["stress_margin_percent"],
                revised["economic_floor"]) == ("136000.00", "105600.00", "22.35", "140800.00")
        assert revised["approval_outcome"] == "below_margin_floor"
        assert revised["review_required"] is True and revised["release_allowed"] is False
        assert revised["preserved_quote"]["stress_cost"] == "97600.00"
        assert result["event"]["source"] == "manual"
        assert applied["state"]["quote_versions"] == before  # original quote versions untouched
        assert applied["state"]["status"]["active_feed"]["feed_version"] == "synthetic-costs-v2"
        again = client.post("/api/cost-update").json()
        assert again["result"]["already_applied"] is True
        assert len(again["state"]["review_events"]) == 1

        # 9: reset restores the initial feed, quote context, and chat.
        reset = client.post("/api/reset").json()
        assert reset["messages"] == [] and reset["quote_versions"] == [] and reset["review_events"] == []
        assert reset["status"]["active_feed"]["feed_version"] == "synthetic-costs-v1"


def test_cost_shock_question_is_a_preview_only(client):
    chat(client, "Can we offer $136,000?")
    reply = chat(client, "What happens if supplier costs increase?")
    update = reply["reply"]["cost_update"]
    assert update["preview"] is True
    assert update["revised"]["stress_margin_percent"] == "22.35"
    assert "apply_cost_update" in reply["reply"]["actions"]
    assert reply["state"]["review_events"] == []
    assert reply["state"]["status"]["active_feed"]["feed_version"] == "synthetic-costs-v1"


def test_apply_supplier_increase_from_chat(client):
    chat(client, "Can we offer $136,000?")
    first = chat(client, "Apply supplier cost increase")
    reply = first["reply"]
    assert reply["intent"] == "apply_cost_update"
    update = reply["cost_update"]
    assert update["preview"] is False and update["event"]["source"] == "manual"
    assert update["original"]["offer_revenue"] == update["revised"]["offer_revenue"] == "136000.00"
    assert (update["revised"]["stress_margin_percent"], update["revised"]["economic_floor"]) == ("22.35", "140800.00")
    assert "stays at $136,000.00, unchanged" in reply["text"]
    assert [v["offer_revenue"] for v in first["state"]["quote_versions"]] == ["136000.00"]
    again = chat(client, "Apply supplier cost increase")
    assert again["reply"]["cost_update"]["already_applied"] is True
    assert len(again["state"]["review_events"]) == 1
    preview = chat(client, "What happens if supplier costs increase?")["reply"]["cost_update"]
    assert preview["already_applied"] is True and preview["revised"]["stress_margin_percent"] == "22.35"


def test_apply_with_no_quote_uses_standard_recommendation(client):
    reply = chat(client, "Apply supplier cost increase")["reply"]
    update = reply["cost_update"]
    assert update["created_standard_quote"] is True
    assert update["original"]["offer_revenue"] == "144000.00"
    assert update["revised"]["stress_margin_percent"] == "26.67"  # (144,000 - 105,600) / 144,000
    assert update["revised"]["approval_outcome"] == "representative_authority"
    assert update["revised"]["review_required"] is True and update["revised"]["release_allowed"] is False


def test_scheduled_watcher_applies_dropped_feed_once(client, settings):
    chat(client, "Can we offer $136,000?")
    settings.incoming_feed_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FEEDS_DIR / "synthetic-costs-v2.json", settings.incoming_feed_dir / "feed.json")
    tools = client.app.state.tools
    first = tools.poll_incoming_feeds()
    assert len(first) == 1 and first[0]["event"]["source"] == "scheduled_watcher"
    assert first[0]["revised"]["stress_margin_percent"] == "22.35"
    assert tools.poll_incoming_feeds() == []
    assert len(client.get("/api/state").json()["review_events"]) == 1
    client.post("/api/reset")
    assert list(settings.incoming_feed_dir.glob("*.json")) == []


def test_follow_up_context_and_new_versions(client):
    chat(client, "Recommend a price for the demo customer.")
    chat(client, "Can we offer 140k?")
    justify = chat(client, "Why is this price justified?")
    assert justify["reply"]["quote"]["offer_revenue"] == "140000.00"
    assert [v["offer_revenue"] for v in justify["state"]["quote_versions"]] == ["144000.00", "140000.00"]
    same = chat(client, "Can we offer $140,000?")
    assert len(same["state"]["quote_versions"]) == 2  # unchanged terms do not create a version
    below = chat(client, "What about $125,000?")["reply"]["quote"]
    assert below["approval_outcome"] == "below_margin_floor"


def test_unsupported_currency_and_missing_information(client):
    eur = chat(client, "Can you quote it in EUR?")["reply"]
    assert eur["text"].startswith("Unsupported currency: EUR; USD only. No FX conversion.")
    assert eur["quote"] is None
    missing = chat(client, "Price a deal for Granite Peak")["reply"]
    assert {"delivery_date", "hardware", "list_revenue"} <= set(missing["sections"]["missing"])
    unknown = chat(client, "What is the weather on Mars?")["reply"]
    assert "do not answer" in unknown["text"] and unknown["citations"] == []


def test_research_answer_cites_documents_and_ignores_planted_instruction(client):
    reply = chat(client, "What do we know about this customer and competitor?")["reply"]
    doc_ids = {c["doc_id"] for c in reply["citations"]}
    assert "CUST-001" in doc_ids and {"COMP-A", "COMP-B"} & doc_ids
    assert_citations_are_real(reply)
    assert any("instruction-like text" in w for w in reply["warnings"])
    assert not any("30%" in item["text"] for item in reply["sections"]["documents"])
    quote = chat(client, "Recommend a price for the demo customer.")["reply"]["quote"]
    assert quote["offer_revenue"] == "144000.00"  # planted text changed nothing


def test_tool_endpoint_returns_engine_output_and_logs_the_call(client):
    response = client.post("/api/tools/price_deal", json={"arguments": {"offer_revenue": "136000.00"}},
                           headers={"X-DealDesk-Caller": "OpenClaw"})
    body = response.json()
    assert body["result"]["approval_outcome"] == "director_approval_required"
    assert body["result"]["stress_margin_percent"] == "28.24" and body["caller"] == "openclaw"
    hits = client.post("/api/tools/search_documents", json={"arguments": {"query": "director approval"}}).json()
    assert hits["result"] and all("passage_id" in h for h in hits["result"])
    assert client.post("/api/tools/run_shell", json={"arguments": {}}).status_code == 404
    state = client.get("/api/state").json()
    assert state["status"]["external_agent"]["tool_calls_observed"] == 2
    assert state["status"]["external_agent"]["verified_on_device"] is False
    calls = [m for m in state["messages"] if m.get("kind") == "tool_call"]
    assert [c["tool"] for c in calls] == ["price_deal", "search_documents"]
    assert calls[0]["result"]["offer_revenue"] == "136000.00"
    assert state["quote_versions"][-1]["offer_revenue"] == "136000.00"  # the viewer sees the agent's quote


def test_cli_tool_runner(settings, monkeypatch, capsys):
    import sys

    from dealdesk import __main__ as cli

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["dealdesk", "tool", "price_deal", '{"offer_revenue": "144000.00"}'])
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert output["result"]["approval_outcome"] == "representative_authority"
    assert output["caller"] == "cli-agent"


@pytest.fixture
def local_mode(settings, monkeypatch):
    settings.mode = LOCAL_MODEL
    settings.llm_model = "test-local-model"
    return settings


def test_local_model_wording_is_used_when_numbers_match(client, local_mode, monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "The $136,000.00 offer needs director approval [1].")
    reply = chat(client, "Can we offer $136,000?")["reply"]
    assert reply["mode"] == "local_model" and reply["model"] == "test-local-model"
    assert reply["quote"]["stress_margin_percent"] == "28.24"


def test_local_model_invented_number_falls_back_to_scripted(client, local_mode, monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "Offer $121,500 at a 31% margin.")
    reply = chat(client, "Can we offer $136,000?")["reply"]
    assert reply["mode"] == "scripted_fallback"
    assert any("not in the tool results" in w for w in reply["warnings"])
    assert reply["text"].startswith("Possibly, but not on your authority")


def test_local_model_unreachable_is_labeled(client, local_mode, monkeypatch):
    def fail(*args, **kwargs):
        raise llm.LocalModelError("connection refused")

    monkeypatch.setattr(llm, "chat", fail)
    reply = chat(client, "Recommend a price for the demo customer.")["reply"]
    assert reply["mode"] == "scripted_fallback"
    assert any("Local model unavailable" in w for w in reply["warnings"])


def test_cloud_endpoints_are_refused(settings):
    assert is_local_endpoint("http://127.0.0.1:11434/v1")
    assert is_local_endpoint("http://192.168.1.40:8000/v1")
    assert is_local_endpoint("http://gb10.local:8000/v1")
    assert not is_local_endpoint("https://api.openai.com/v1")
    assert is_local_endpoint("http://spark-01:8000/v1", ("spark-01",))
    settings.mode, settings.llm_model = LOCAL_MODEL, "m"
    settings.llm_base_url = "https://api.example.com/v1"
    assert "cloud endpoints are refused" in settings.llm_endpoint_error()
    with pytest.raises(llm.LocalModelError):
        llm.chat(settings, "s", "u")


def test_unsupported_number_guard():
    source = json.dumps({"calc": ["Offer $136,000.00, discount 15.00%, margin 28.24%"]})
    assert agent_module.unsupported_numbers("Offer $136,000 is 15% off with 28.24% margin.", source) == []
    assert agent_module.unsupported_numbers("Try $129,000 instead.", source) == ["$129,000"]


def test_offer_parsing():
    list_price = load_deal()["list_revenue"]
    assert agent_module.parse_offer("Can we offer $136,000?", list_price) == "136000.00"
    assert agent_module.parse_offer("what about 140k", list_price) == "140000.00"
    assert agent_module.parse_offer("give them 15% off", list_price) == "136000.00"
    assert agent_module.parse_offer("delivery on 2026-12-01", list_price) is None
