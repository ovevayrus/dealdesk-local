"""Immutable quote versions and cost feed reappraisal for the scheduled watcher.

Suhas owns scheduling, the persisted cursor, and approval identity. This module
supplies the deterministic part: given open quotes and a new feed, which quotes
changed, by how much, whether policy is now breached, and what to propose.
A sent offer is never modified; the result asks for a new version instead.
"""
from decimal import Decimal

from .errors import QuantError
from .money import D, money, pct
from .pricing import (build_ledger, floors, list_revenue, validate_deal, _roles, evaluate_offer,
                      _alt_deal)
from .util import content_hash


def make_quote_version(quote_id, version, deal, price, feed, policy, price_book,
                       approval=None, state="sent"):
    """Freeze inputs and calculated fields. The hash binds an approval to exactly this version."""
    d, flags = validate_deal(deal, price_book, policy)
    bundle = price_book["bundles"][d["bundle"]]
    ledger = build_ledger(d, bundle, feed)
    rev = list_revenue(d, bundle)
    fl = floors(D(ledger["stress_cost"]), D(rev["total"]), policy)
    p = D(price)
    ev = evaluate_offer(p, ledger, rev, fl, policy, _roles(policy)[0][0], d["service"]["term_months"])
    frozen = {
        "quote_id": quote_id, "version": version, "deal": deal, "price": money(p),
        "feed_version": feed["version"], "feed_hash": content_hash(feed),
        "policy_version": policy["version"], "price_book_version": price_book["version"],
        "calculated": {
            "base_cost": ledger["base_cost"], "stress_cost": ledger["stress_cost"],
            "economic_floor": fl["economic_floor"], "list_revenue": rev["total"],
            "discount_pct": ev["discount_pct"], "stress_margin_pct": ev["stress_margin_pct"],
            "required_approval": ev["required_approval"],
            "ledger_lines": [{k: l[k] for k in ("line_id", "series_id", "month", "quantity",
                                                  "unit_cost_base", "unit_cost_stress", "base", "stress")}
                             for l in ledger["lines"]],
        },
    }
    qv = dict(frozen)
    qv["quote_hash"] = content_hash(frozen)
    qv["state"] = state
    qv["approval"] = approval
    return qv


def verify_quote_hash(qv) -> bool:
    frozen = {k: v for k, v in qv.items() if k not in ("quote_hash", "state", "approval")}
    return content_hash(frozen) == qv["quote_hash"]


def appraise_quote(qv, feed, policy, price_book) -> dict:
    if not verify_quote_hash(qv):
        raise QuantError("QUOTE_HASH_MISMATCH", f"quote {qv['quote_id']} v{qv['version']} was altered",
                         "quote_hash")
    d, _ = validate_deal(qv["deal"], price_book, policy)
    bundle = price_book["bundles"][d["bundle"]]
    ledger = build_ledger(d, bundle, feed)
    rev = list_revenue(d, bundle)
    fl = floors(D(ledger["stress_cost"]), D(rev["total"]), policy)
    price = D(qv["price"])
    margin = (price - D(ledger["stress_cost"])) / price
    return {"ledger": ledger, "rev": rev, "floors": fl, "price": price, "stress_margin": margin,
            "deal": d, "feed": feed}


def review_open_quotes(quotes, new_feed, policy, price_book) -> dict:
    """Compare each open quote's frozen appraisal with the new feed.

    Returns one deduplicable review event per affected quote. Unaffected quotes
    produce nothing, so an unchanged feed emits no events.
    """
    m_min = D(policy["min_gross_margin"])
    new_hash = content_hash(new_feed)
    events, unaffected = [], []
    for qv in quotes:
        if qv.get("state") not in ("sent", "approved", "draft"):
            continue
        a = appraise_quote(qv, new_feed, policy, price_book)
        old_lines = {l["line_id"]: l for l in qv["calculated"]["ledger_lines"]}
        changed = []
        for l in a["ledger"]["lines"]:
            o = old_lines.get(l["line_id"])
            if o and (o["unit_cost_base"] != l["unit_cost_base"]
                      or o["unit_cost_stress"] != l["unit_cost_stress"]):
                changed.append({
                    "line_id": l["line_id"], "series_id": l["series_id"], "month": l["month"],
                    "quantity": l["quantity"],
                    "unit_cost_base": [o["unit_cost_base"], l["unit_cost_base"]],
                    "unit_cost_stress": [o["unit_cost_stress"], l["unit_cost_stress"]],
                    "stress_delta": money(D(l["stress"]) - D(o["stress"])),
                    "source": l["source"],
                })
        if not changed:
            unaffected.append(qv["quote_id"])
            continue

        price = a["price"]
        old_margin = (price - D(qv["calculated"]["stress_cost"])) / price
        breach = a["stress_margin"] < m_min
        prev = {"stress_cost": qv["calculated"]["stress_cost"],
                "stress_margin_pct": pct(old_margin),
                "economic_floor": qv["calculated"]["economic_floor"],
                "feed_version": qv["feed_version"]}
        new = {"stress_cost": a["ledger"]["stress_cost"],
               "stress_margin_pct": pct(a["stress_margin"]),
               "economic_floor": a["floors"]["economic_floor"],
               "feed_version": new_feed["version"]}
        event = {
            "event_type": "quote_review_required" if breach else "quote_cost_changed",
            "severity": "breach" if breach else "info",
            "quote_id": qv["quote_id"], "quote_version": qv["version"], "quote_hash": qv["quote_hash"],
            "account_id": qv["deal"]["account_id"],
            "price": money(price),
            "previous": prev, "new": new,
            "changed_lines": changed,
            "original_offer_preserved": True,
            "original_approval_preserved": qv.get("approval"),
            "approval_still_valid_for_original": True,
            "requires_new_version": breach,
            "dedup_key": content_hash({"q": qv["quote_id"], "v": qv["version"], "h": qv["quote_hash"],
                                       "feed": new_hash}),
            "recommended_responses": _responses(qv, a, policy, price_book) if breach else [],
            "summary": _summary(qv, prev, new, changed, breach, policy),
        }
        events.append(event)
    return {"feed_version": new_feed["version"], "feed_hash": new_hash,
            "events": events, "unaffected_quotes": unaffected,
            "counts": {"checked": len(quotes), "breach": sum(e["severity"] == "breach" for e in events),
                       "info": sum(e["severity"] == "info" for e in events),
                       "unaffected": len(unaffected)}}


def _summary(qv, prev, new, changed, breach, policy):
    series = sorted({c["series_id"] for c in changed})
    months = sorted({c["month"] for c in changed})
    s = (f"Quote {qv['quote_id']} v{qv['version']} at {qv['price']}: stress cost moved from "
         f"{prev['stress_cost']} to {new['stress_cost']} ({', '.join(series)}; {', '.join(months)}). "
         f"Stress margin {prev['stress_margin_pct']}% -> {new['stress_margin_pct']}%.")
    if breach:
        s += (f" Below the {pct(D(policy['min_gross_margin']))}% policy minimum. New economic floor "
              f"{new['economic_floor']}. The sent offer and its approval are unchanged; revised terms "
              "need a new quote version and a fresh approval.")
    return s


def _responses(qv, a, policy, price_book):
    """Concrete commercial options, all recomputed from the new feed."""
    out = []
    rev, fl = a["rev"], a["floors"]
    L = D(rev["total"])
    floor = D(fl["economic_floor"])
    term = a["deal"]["service"]["term_months"]
    if floor <= L:
        ev = evaluate_offer(floor, a["ledger"], rev, fl, policy, _roles(policy)[0][0], term)
        out.append({
            "option": "reprice_to_new_floor",
            "price": money(floor),
            "price_change": money(floor - a["price"]),
            "discount_pct": ev["discount_pct"],
            "stress_margin_pct": ev["stress_margin_pct"],
            "required_approval": ev["required_approval"],
            "note": "Lowest price that meets policy under the new feed. Needs a new version and approval.",
        })
    else:
        out.append({"option": "infeasible_under_current_terms",
                    "note": f"New floor {money(floor)} exceeds list {money(L)}."})

    # phased: commit the first shipment now, costed against the same new feed
    d = a["deal"]
    bundle = price_book["bundles"][d["bundle"]]
    alt = _alt_deal(d, bundle, a["feed"])
    if alt:
        alt_ledger = build_ledger(alt, bundle, a["feed"])
        alt_rev = list_revenue(alt, bundle)
        alt_fl = floors(D(alt_ledger["stress_cost"]), D(alt_rev["total"]), policy)
        pr = D(alt_fl["authorization"][_roles(policy)[0][0]]["lowest_authorized_offer"])
        if pr <= D(alt_rev["total"]):
            ev = evaluate_offer(pr, alt_ledger, alt_rev, alt_fl, policy, _roles(policy)[0][0], term)
            out.append({
                "option": "phase_first_shipment",
                "quantity": alt["quantity"], "price": money(pr),
                "discount_pct": ev["discount_pct"], "stress_margin_pct": ev["stress_margin_pct"],
                "required_approval": ev["required_approval"],
                "note": "Commit the first shipment now; quote the remainder when supply costs settle.",
            })

    hw = [l for l in a["ledger"]["lines"] if l["category"] == "hardware"]
    units = sum((D(l["quantity"]) for l in hw), Decimal(0))
    if units:
        allowed = a["price"] * (1 - D(policy["min_gross_margin"]))
        other = D(a["ledger"]["stress_cost"]) - sum((D(l["stress"]) for l in hw), Decimal(0))
        out.append({
            "option": "hardware_cost_adjustment_clause",
            "keep_price": money(a["price"]),
            "max_hardware_stress_per_unit_at_this_price": money((allowed - other) / units),
            "note": "Keep the price but pass hardware cost above this level through to the customer. "
                    "Nonstandard clause: needs finance and legal review.",
        })
    return out

