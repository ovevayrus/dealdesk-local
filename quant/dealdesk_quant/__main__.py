"""Command line entry point. Every command prints one JSON envelope:

  {"ok": true,  "tool": "...", "run_id": "...", "result": {...}}
  {"ok": false, "tool": "...", "run_id": "...", "error": {"code", "message", "field"}}

Exit code is 0 on success, 2 on a QuantError. Suhas wraps these as agent tools.
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

from .errors import QuantError
from .util import load_json

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"


def _common(p):
    p.add_argument("--feed", default=str(FIX / "cost_feed_v1.json"))
    p.add_argument("--policy", default=str(FIX / "policy.json"))
    p.add_argument("--price-book", default=str(FIX / "price_book.json"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dealdesk_quant")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("price", help="price_deal: ledger, floors, packages, sensitivity")
    p.add_argument("deal")
    p.add_argument("--actor-role", required=True, help="from the trusted session, never the model")
    _common(p)

    p = sub.add_parser("sensitivity", help="stress margin grid for the viewer sliders")
    p.add_argument("deal")
    p.add_argument("--price", required=True)
    p.add_argument("--hardware", default="-10,-5,0,5,10,15,20")
    p.add_argument("--freight", default="0,10,20")
    _common(p)

    p = sub.add_parser("forecast", help="forecast_costs for one series")
    p.add_argument("--series", required=True)
    p.add_argument("--history", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--horizon", type=int, default=6)
    p.add_argument("--targets", default="", help="comma separated YYYY-MM months the quote uses")

    p = sub.add_parser("review", help="watch_quotes repricing: open quotes vs a new feed")
    p.add_argument("--quotes", default=str(FIX / "open_quotes.json"))
    _common(p)

    sub.add_parser("generate-data", help="regenerate the seeded synthetic history")

    a = ap.parse_args(argv)
    run_id = str(uuid.uuid4())
    tool = {"price": "price_deal", "sensitivity": "sensitivity", "forecast": "forecast_costs",
            "review": "watch_quotes_reprice", "generate-data": "generate_data"}[a.cmd]
    try:
        if a.cmd == "price":
            from .pricing import price_deal
            res = price_deal(load_json(a.deal), load_json(a.feed), load_json(a.policy),
                             load_json(a.price_book), a.actor_role)
        elif a.cmd == "sensitivity":
            from .pricing import sensitivity
            res = sensitivity(load_json(a.deal), load_json(a.feed), load_json(a.policy),
                              load_json(a.price_book), a.price,
                              [int(x) for x in a.hardware.split(",")],
                              [int(x) for x in a.freight.split(",")])
        elif a.cmd == "forecast":
            from .forecast import forecast_costs
            targets = [t for t in a.targets.split(",") if t] or None
            res = forecast_costs(a.history, a.series, a.as_of, targets, a.horizon)
        elif a.cmd == "review":
            from .repricing import review_open_quotes
            res = review_open_quotes(load_json(a.quotes)["quotes"], load_json(a.feed),
                                     load_json(a.policy), load_json(a.price_book))
        else:
            from .data_gen import generate
            res = generate(str(ROOT / "data"))
        out = {"ok": True, "tool": tool, "run_id": run_id, "result": res}
        code = 0
    except QuantError as e:
        out = {"ok": False, "tool": tool, "run_id": run_id, "error": e.to_dict()}
        code = 2
    except (json.JSONDecodeError, FileNotFoundError, TypeError, ValueError) as e:
        out = {"ok": False, "tool": tool, "run_id": run_id,
               "error": {"code": "INVALID_INPUT", "message": str(e), "field": None}}
        code = 2
    print(json.dumps(out, indent=2, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
