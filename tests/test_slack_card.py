"""Slack review cards carry an opaque review ID and nothing from the deal."""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations" / "slack"))
import slack_poster  # noqa: E402

DEALS = [
    slack_poster.SAMPLE_DEAL,
    {
        "deal_id": "globex-corporation-renewal",
        "customer_name": "Globex Corporation",
        "health_score": 41,
        "stage": "Proposal",
        "risk_summary": "Offer of $1,250,000 at 18.5% discount leaves 9% margin; win rate 34%",
        "recommended_action": "Escalate to Initech pricing desk",
        "needs_approval": True,
    },
    {"deal_id": "q-seed-acme-7", "account_id": "SYN-ACCOUNT-001", "offer_revenue": 98000, "needs_approval": True},
]

CUSTOMER_NAMES = ("acme", "globex", "initech", "syn-account")
DOLLARS = re.compile(r"\$|USD|\b\d{1,3}(,\d{3})+\b")
PERCENT = re.compile(r"%|\bpercent\b", re.IGNORECASE)


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat_postMessage(self, **kwargs):
        self.calls.append(kwargs)
        return {"channel": "C-TEST", "ts": "1.0"}


@pytest.fixture
def posted(monkeypatch, tmp_path):
    """Post each deal through post_deal_card and capture exactly what Slack would receive."""
    client = FakeClient()
    monkeypatch.setattr(slack_poster, "_client", client)
    monkeypatch.setattr(slack_poster, "REVIEW_MAP_PATH", str(tmp_path / "reviews.json"))
    results = [slack_poster.post_deal_card(deal, channel="C-TEST") for deal in DEALS]
    return list(zip(DEALS, results, client.calls))


def _payload_text(call) -> str:
    return json.dumps({"text": call["text"], "blocks": call["blocks"]})


def test_card_has_no_customer_names_dollars_or_percentages(posted):
    for deal, _, call in posted:
        payload = _payload_text(call).lower()
        for name in CUSTOMER_NAMES:
            assert name not in payload, f"customer name {name!r} leaked"
        assert not DOLLARS.search(payload), "dollar amount leaked"
        assert not PERCENT.search(payload), "percentage leaked"


def test_card_contains_no_deal_values(posted):
    for deal, _, call in posted:
        payload = _payload_text(call)
        for key, value in deal.items():
            if isinstance(value, bool):
                continue
            assert str(value) not in payload, f"deal field {key!r} leaked"


def test_card_is_only_the_review_notice_and_buttons(posted):
    for _, result, call in posted:
        rid = result["review_id"]
        assert re.fullmatch(r"R-[0-9A-F]{4}", rid)
        assert call["text"] == (
            f"A DealDesk quote review is ready (review ID: {rid}). Open your local DealDesk viewer."
        )
        types = [block["type"] for block in call["blocks"]]
        assert types == ["section", "actions", "context"]
        assert [e["value"] for e in call["blocks"][1]["elements"]] == [rid, rid]
        assert call["blocks"][2]["elements"][0]["text"] == "Details stay on the local DealDesk viewer."


def test_review_id_maps_back_to_deal_locally(posted):
    for deal, result, _ in posted:
        assert slack_poster.lookup_review(result["review_id"]) == deal["deal_id"]


def test_no_data_left_the_box_claim_is_gone():
    for path in (Path(slack_poster.__file__).parent).glob("*.py"):
        assert "no data left the box" not in path.read_text(encoding="utf-8").lower(), path
