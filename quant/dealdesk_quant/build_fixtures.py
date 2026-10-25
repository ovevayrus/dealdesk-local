"""Build fixtures/open_quotes.json: five sent quotes, all priced against cost feed v1."""
import copy
import json
from pathlib import Path

from .repricing import make_quote_version
from .util import load_json

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"


def _deal(base, **kw):
    d = copy.deepcopy(base)
    d.pop("proposed_price", None)
    d.update(kw)
    return d


def build():
    demo = load_json(FIX / "deal_demo.json")
    feed = load_json(FIX / "cost_feed_v1.json")
    policy = load_json(FIX / "policy.json")
    pb = load_json(FIX / "price_book.json")

    specs = [
        # the demo quote: 15% concession approved by a director against feed v1
        ("Q-1001", _deal(demo), "136000.00",
         {"actor": "director:dana.lee", "role": "director", "exception": "discount 15.00%",
          "approved_at": "2026-10-25T10:42:00-07:00", "expires": "2026-11-24"}),
        ("Q-1002", _deal(demo, deal_id="D-1002", account_id="ACC-BLUEPEAK"), "144000.00", None),
        ("Q-1003", _deal(demo, deal_id="D-1003", account_id="ACC-CEDAR", quantity=50,
                         procurement=[{"month": "2026-12", "units": 50}],
                         shipments=[{"month": "2026-12", "units": 50}],
                         service={"start_month": "2027-01", "term_months": 12}), "76000.00", None),
        ("Q-1004", _deal(demo, deal_id="D-1004", account_id="ACC-BLUEPEAK", quantity=40,
                         procurement=[{"month": "2027-02", "units": 40}],
                         shipments=[{"month": "2027-02", "units": 40}],
                         service={"start_month": "2027-03", "term_months": 12}), "60000.00", None),
        ("Q-1005", _deal(demo, deal_id="D-1005", account_id="ACC-CEDAR", quantity=80,
                         procurement=[{"month": "2026-12", "units": 80}],
                         shipments=[{"month": "2026-12", "units": 40}, {"month": "2026-12", "units": 40}],
                         service={"start_month": "2027-01", "term_months": 12}), "104960.00",
         {"actor": "director:dana.lee", "role": "director", "exception": "discount 18.00%",
          "approved_at": "2026-10-20T15:10:00-07:00", "expires": "2026-11-19"}),
    ]
    quotes = []
    for qid, deal, price, approval in specs:
        qv = make_quote_version(qid, 1, deal, price, feed, policy, pb, approval=None)
        if approval:
            approval = dict(approval, quote_hash=qv["quote_hash"], quote_version=1)
        qv["approval"] = approval
        quotes.append(qv)
    out = FIX / "open_quotes.json"
    out.write_text(json.dumps({"synthetic": True, "priced_with_feed": feed["version"],
                               "quotes": quotes}, indent=2) + "\n")
    return quotes


if __name__ == "__main__":
    for q in build():
        c = q["calculated"]
        print(q["quote_id"], q["price"], c["discount_pct"], c["stress_cost"], c["stress_margin_pct"],
              c["required_approval"], q["quote_hash"])
