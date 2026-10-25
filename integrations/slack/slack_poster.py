"""Post DealDesk review cards to Slack.

Slack only ever sees an opaque review ID (e.g. R-7F3A). The deal data stays local:
the review ID -> deal mapping is written to REVIEW_MAP_PATH on this machine, and
nothing from the deal (customer, price, discount, margin, win rate, scores) is
put in the message.

Integration contract (shared with the pricing engine and the agent):

    {
      "deal_id": "acme-expansion",
      "health_score": 62,
      "stage": "Negotiation",
      "risk_summary": "...",
      "recommended_action": "Generate battle card",
      "needs_approval": true
    }

Usage:
    from slack_poster import post_deal_card
    post_deal_card(data)            # posts to DEAL_ROOM_CHANNEL
"""
import json
import os
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from slack_sdk import WebClient

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

REVIEW_MAP_PATH = os.environ.get("DEALDESK_REVIEW_MAP", os.path.join(HERE, "runtime", "reviews.json"))
VIEWER_URL = os.environ.get("DEALDESK_VIEWER_URL", "http://127.0.0.1:4321/")
FOOTER = "Details stay on the local DealDesk viewer."

_client = None


def get_client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    return _client


def _load_reviews() -> dict:
    try:
        with open(REVIEW_MAP_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def new_review_id(existing=()) -> str:
    """Random, non-derivable ID such as R-7F3A."""
    while True:
        rid = f"R-{secrets.token_hex(2).upper()}"
        if rid not in existing:
            return rid


def register_review(deal_id: str) -> str:
    """Create a review ID for a deal and record the mapping locally only."""
    reviews = _load_reviews()
    rid = new_review_id(reviews)
    reviews[rid] = {"deal_id": deal_id, "created": datetime.now(timezone.utc).isoformat()}
    os.makedirs(os.path.dirname(REVIEW_MAP_PATH), exist_ok=True)
    with open(REVIEW_MAP_PATH, "w") as f:
        json.dump(reviews, f, indent=2)
    return rid


def lookup_review(review_id: str) -> str | None:
    """Local deal_id for a review ID, or None."""
    entry = _load_reviews().get(review_id)
    return entry["deal_id"] if entry else None


def review_text(review_id: str) -> str:
    return f"A DealDesk quote review is ready (review ID: {review_id}). Open your local DealDesk viewer."


def build_review_blocks(review_id: str) -> list:
    """Card blocks. Takes only the opaque ID so deal data can't end up in Slack."""
    link = f"{VIEWER_URL}?review={review_id}"
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"A DealDesk quote review is ready (review ID: {review_id}). "
                        f"Open your <{link}|local DealDesk viewer>.",
            },
        },
        {
            "type": "actions",
            "block_id": f"approval:{review_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "deal_approve",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "value": review_id,
                },
                {
                    "type": "button",
                    "action_id": "deal_reject",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "value": review_id,
                },
            ],
        },
        {"type": "context", "elements": [{"type": "mrkdwn", "text": FOOTER}]},
    ]


def post_deal_card(data: dict, channel: str | None = None) -> dict:
    """Post a review card for a deal. Returns {"channel", "ts", "review_id"}."""
    if "deal_id" not in data:
        raise ValueError("deal card missing field: deal_id")
    channel = channel or os.environ.get("DEAL_ROOM_CHANNEL", "#deal-room")
    review_id = register_review(data["deal_id"])
    resp = get_client().chat_postMessage(
        channel=channel,
        text=review_text(review_id),
        blocks=build_review_blocks(review_id),
        unfurl_links=False,
    )
    return {"channel": resp["channel"], "ts": resp["ts"], "review_id": review_id}


SAMPLE_DEAL = {
    "deal_id": "acme-expansion",
    "health_score": 62,
    "stage": "Negotiation",
    "risk_summary": "Proposed 22% discount is 8 points above historical win average",
    "recommended_action": "Generate battle card",
    "needs_approval": True,
}

if __name__ == "__main__":
    print(post_deal_card(SAMPLE_DEAL))
