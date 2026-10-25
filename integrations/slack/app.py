"""DealDesk Slack app (Socket Mode). Run: .venv/bin/python app.py

Handles the Approve / Reject buttons on review cards posted by slack_poster.post_deal_card.
Button values are opaque review IDs; the deal they map to is looked up locally.
"""
import logging
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import slack_poster  # loads .env

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

app = App(token=os.environ["SLACK_BOT_TOKEN"])


def _resolve(body, client, verdict: str):
    review_id = body["actions"][0]["value"]
    user = body["user"]["id"]
    channel = body["channel"]["id"]
    ts = body["message"]["ts"]
    # Swap the buttons for a record of who decided
    blocks = [b for b in body["message"]["blocks"] if b.get("type") != "actions"]
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"*{verdict}* by <@{user}>"}]})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"Review {review_id} {verdict.lower()}")
    # Local log only: the deal behind the review ID never goes to Slack
    logging.info("review %s (deal %s) %s by %s", review_id, slack_poster.lookup_review(review_id), verdict, user)


@app.action("deal_approve")
def handle_approve(ack, body, client):
    ack()
    _resolve(body, client, "Approved")


@app.action("deal_reject")
def handle_reject(ack, body, client):
    ack()
    _resolve(body, client, "Rejected")


if __name__ == "__main__":
    print("⚡️ Bolt app is running!")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
