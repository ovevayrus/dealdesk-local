"""Optional Slack review acknowledgements. No quote approval or release occurs."""
import logging
import os

import slack_poster


def _resolve(body, client, verdict: str):
    try:
        review_id = body["actions"][0]["value"]
        user = body["user"]["id"]
        channel = body["channel"]["id"]
        ts = body["message"]["ts"]
    except (KeyError, IndexError, TypeError):
        return False
    if not slack_poster.resolve_review(review_id, user, channel, ts, verdict):
        logging.warning("Slack review acknowledgement refused")
        return False
    blocks = [b for b in slack_poster.build_review_blocks(review_id) if b.get("type") != "actions"]
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text":
                   f"*{verdict}* by <@{user}>. This does not approve or release a quote."}]})
    client.chat_update(channel=channel, ts=ts, blocks=blocks, text=f"Review {review_id}: {verdict}")
    logging.info("Slack review acknowledgement recorded")
    return True


def create_app():
    # Importing this module for tests does not initialize Bolt or call Slack.
    from slack_bolt import App

    if not os.environ.get("DEALDESK_SLACK_REVIEWERS") or not os.environ.get("DEAL_ROOM_CHANNEL"):
        raise ValueError("Configure DEALDESK_SLACK_REVIEWERS and DEAL_ROOM_CHANNEL before starting Slack.")
    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    @app.action("deal_approve")
    def handle_approve(ack, body, client):
        ack()
        _resolve(body, client, "Review acknowledged")

    @app.action("deal_reject")
    def handle_reject(ack, body, client):
        ack()
        _resolve(body, client, "Changes requested")

    return app


if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    SocketModeHandler(create_app(), os.environ["SLACK_APP_TOKEN"]).start()
