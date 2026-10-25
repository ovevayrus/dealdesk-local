"""DealDesk Slack CLI. Run: .venv/bin/python slack_cli.py <command>

Commands:
    auth                         check the bot token and show workspace / bot identity
    post TEXT [-c CHANNEL]       post a plain message
    card [FILE|-] [-c CHANNEL]   post a review card (opaque ID only) for a deal JSON
                                 file, stdin (-), or the sample deal
    card --dry-run ...           print the card's Block Kit JSON without posting
    history [-c CHANNEL] [-n N]  show the last N messages (needs a channel ID like C0123...)

CHANNEL defaults to DEAL_ROOM_CHANNEL from .env.
"""
import argparse
import json
import os
import sys

from slack_sdk.errors import SlackApiError

import slack_poster  # loads .env


def default_channel() -> str:
    return os.environ.get("DEAL_ROOM_CHANNEL", "#deal-room")


def cmd_auth(args):
    resp = slack_poster.get_client().auth_test()
    print(f"connected: team={resp['team']} ({resp['team_id']}) bot={resp['user']} ({resp['user_id']})")
    print(f"workspace: {resp['url']}")
    scopes = resp.headers.get("x-oauth-scopes")
    if scopes:
        print(f"scopes:    {scopes}")


def cmd_post(args):
    resp = slack_poster.get_client().chat_postMessage(channel=args.channel, text=args.text)
    print(json.dumps({"channel": resp["channel"], "ts": resp["ts"]}))


def cmd_card(args):
    if args.file is None:
        data = slack_poster.SAMPLE_DEAL
    elif args.file == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.file) as f:
            data = json.load(f)

    if args.dry_run:
        # Preview with a throwaway ID; nothing is recorded or posted
        print(json.dumps(slack_poster.build_review_blocks(slack_poster.new_review_id()), indent=2))
        return
    print(json.dumps(slack_poster.post_deal_card(data, channel=args.channel)))


def cmd_history(args):
    resp = slack_poster.get_client().conversations_history(channel=args.channel, limit=args.limit)
    for msg in reversed(resp["messages"]):
        who = msg.get("user") or msg.get("bot_id") or "?"
        print(f"{msg['ts']}  {who:<12} {msg.get('text', '')}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slack_cli", description="DealDesk Slack CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth", help="check the bot token").set_defaults(func=cmd_auth)

    p = sub.add_parser("post", help="post a plain message")
    p.add_argument("text")
    p.add_argument("-c", "--channel", default=default_channel())
    p.set_defaults(func=cmd_post)

    p = sub.add_parser("card", help="post a deal card")
    p.add_argument("file", nargs="?", help="deal JSON file, or - for stdin (default: sample deal)")
    p.add_argument("-c", "--channel", default=default_channel())
    p.add_argument("--dry-run", action="store_true", help="print blocks instead of posting")
    p.set_defaults(func=cmd_card)

    p = sub.add_parser("history", help="show recent messages")
    p.add_argument("-c", "--channel", default=default_channel())
    p.add_argument("-n", "--limit", type=int, default=10)
    p.set_defaults(func=cmd_history)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SlackApiError as e:
        err = e.response.get("error")
        hint = ""
        if err == "missing_scope":
            hint = f" (needs scope: {e.response.get('needed')})"
        elif err == "channel_not_found":
            hint = " (use a channel ID for history, or invite the bot to the channel)"
        elif err == "not_in_channel":
            hint = " (invite the bot: /invite @<bot> in the channel)"
        sys.exit(f"slack error: {err}{hint}")
    except ValueError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
