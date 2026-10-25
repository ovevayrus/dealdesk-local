"""Deterministic pricing: dated cost ledger, floors, authority, packages, sensitivity.

The LLM never produces an authoritative number. Every amount here comes from
validated inputs, the price book, the policy, and the dated cost feed.
"""
from decimal import Decimal

from .errors import QuantError
from .money import D, ZERO, ceil_cent, round_cent, money, pct, ratio
from .util import (add_months, check_date, check_month, content_hash, days_between,
                   month_index)

REQUIRED_FIELDS = ["deal_id", "account_id", "bundle", "quantity", "currency", "destination",
                   "procurement", "shipments", "service", "payment_terms", "quote_date",
                   "quote_expiry"]

ASSUMPTIONS = [
    "All amounts in USD. Gross margin = (revenue - cost) / revenue, never markup.",
    "Policy margin test uses the stress cost ledger (margin_basis = stress).",
    "Hardware is costed at the procurement month, freight at each shipment month, service per active month.",
    "Stress is one named joint scenario applied to every line at once; the reserve is not added a second time.",
    "Discount is applied evenly across upfront and recurring list lines.",
]
EXCLUSIONS = ["taxes", "FX", "financing", "returns", "working capital effects"]


# ---------------------------------------------------------------- validation

def validate_deal(deal: dict, price_book: dict, policy: dict) -> tuple[dict, list]:
    """Return a normalized deal and a list of review flags. Raise QuantError on hard errors."""
    if not isinstance(deal, dict):
        raise QuantError("INVALID_INPUT", "deal must be a JSON object")
    for f in REQUIRED_FIELDS:
        if f not in deal or deal[f] in (None, "", []):
            raise QuantError("MISSING_INPUT", f"required field missing: {f}", f)

    if deal["currency"] != price_book["currency"]:
        raise QuantError("INVALID_CURRENCY",
                         f"only {price_book['currency']} is supported, got {deal['currency']!r}",
                         "currency")
    bundle = price_book["bundles"].get(deal["bundle"])
    if bundle is None:
        raise QuantError("UNSUPPORTED_SKU", f"unknown bundle {deal['bundle']!r}", "bundle")
    lane = price_book["lanes"].get(deal["destination"])
    if lane is None:
        raise QuantError("UNSUPPORTED_DESTINATION", f"no freight lane for {deal['destination']!r}",
                         "destination")

    qty = deal["quantity"]
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise QuantError("INVALID_QUANTITY", "quantity must be a positive integer", "quantity")

    def schedule(name):
        rows = deal[name]
        if not isinstance(rows, list):
            raise QuantError("INVALID_INPUT", f"{name} must be a list", name)
        out = []
        for i, r in enumerate(rows):
            m = check_month(r.get("month"), f"{name}[{i}].month")
            u = r.get("units")
            if not isinstance(u, int) or isinstance(u, bool) or u <= 0:
                raise QuantError("INVALID_QUANTITY", f"{name}[{i}].units must be a positive integer",
                                 f"{name}[{i}].units")
            out.append({"month": m, "units": u})
        if sum(r["units"] for r in out) != qty:
            raise QuantError("SCHEDULE_MISMATCH", f"{name} units must sum to quantity {qty}", name)
        return sorted(out, key=lambda r: r["month"])

    procurement = schedule("procurement")
    shipments = schedule("shipments")
    max_ship = bundle["max_units_per_shipment"]
    for i, s in enumerate(shipments):
        if s["units"] > max_ship:
            raise QuantError("SHIPMENT_TOO_LARGE",
                             f"shipments[{i}] has {s['units']} units; max per shipment is {max_ship}",
                             f"shipments[{i}].units")
    # cannot ship units before they are procured
    cum_proc, cum_ship = 0, 0
    for s in shipments:
        cum_ship += s["units"]
        cum_proc = sum(p["units"] for p in procurement if p["month"] <= s["month"])
        if cum_ship > cum_proc:
            raise QuantError("INFEASIBLE_SCHEDULE",
                             f"shipment in {s['month']} exceeds units procured by then", "shipments")

    svc = deal["service"]
    start = check_month(svc.get("start_month"), "service.start_month")
    term = svc.get("term_months")
    if not isinstance(term, int) or isinstance(term, bool) or term <= 0:
        raise QuantError("INVALID_INPUT", "service.term_months must be a positive integer",
                         "service.term_months")
    if month_index(start) < month_index(shipments[0]["month"]):
        raise QuantError("INFEASIBLE_SCHEDULE", "service cannot start before the first shipment",
                         "service.start_month")

    qd = check_date(deal["quote_date"], "quote_date")
    qe = check_date(deal["quote_expiry"], "quote_expiry")
    if days_between(qd, qe) <= 0:
        raise QuantError("INVALID_DATE", "quote_expiry must be after quote_date", "quote_expiry")

    proposed = None
    if deal.get("proposed_price") not in (None, ""):
        try:
            proposed = D(deal["proposed_price"])
        except (TypeError, ValueError) as exc:
            raise QuantError("INVALID_PRICE", str(exc), "proposed_price")
        if proposed <= ZERO or proposed != round_cent(proposed):
            raise QuantError("INVALID_PRICE", "proposed_price must be positive with at most 2 decimals",
                             "proposed_price")

    flags = []
    if term != policy["standard_service_term_months"]:
        flags.append(_flag("NONSTANDARD_TERM", "review",
                           f"service term {term} months is not the standard "
                           f"{policy['standard_service_term_months']}; needs finance review"))
    if deal["payment_terms"] not in price_book["approved_payment_terms"]:
        flags.append(_flag("NONSTANDARD_PAYMENT_TERMS", "review",
                           f"payment terms {deal['payment_terms']!r} are not pre-approved; "
                           "their financing cost is not modeled"))

    norm = {
        "deal_id": deal["deal_id"], "account_id": deal["account_id"], "bundle": deal["bundle"],
        "quantity": qty, "currency": deal["currency"], "destination": deal["destination"],
        "lane_series": lane, "procurement": procurement, "shipments": shipments,
        "service": {"start_month": start, "term_months": term},
        "payment_terms": deal["payment_terms"], "quote_date": qd, "quote_expiry": qe,
        "proposed_price": proposed, "evidence_refs": list(deal.get("evidence_refs", [])),
        "alternative": deal.get("alternative") or {},
    }
    return norm, flags


def _flag(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


# ---------------------------------------------------------------- cost feed

def feed_cost(feed: dict, series_id: str, month: str):
    s = feed["series"].get(series_id)
    if s is None:
        raise QuantError("COST_INPUT_MISSING", f"cost feed {feed['version']} has no series {series_id}",
                         series_id)
    if "flat" in s:
        entry = s["flat"]
    else:
        entry = s["months"].get(month)
        if entry is None:
            raise QuantError("COST_INPUT_MISSING",
                             f"cost feed {feed['version']} has no {series_id} value for {month}",
                             series_id)
    return D(entry["base"]), D(entry["stress"]), s["unit"], s.get("source", "")


# ---------------------------------------------------------------- ledger

def build_ledger(d: dict, bundle: dict, feed: dict) -> dict:
    cs = bundle["cost_series"]
    lines = []

    def add(category, month, qty, series_id, label):
        base_u, stress_u, unit, source = feed_cost(feed, series_id, month)
        q = D(qty)
        lines.append({
            "line_id": f"{category}:{month}" if category != "installation" else "installation",
            "category": category, "label": label, "month": month,
            "quantity": str(q), "unit": unit,
            "unit_cost_base": money(base_u), "unit_cost_stress": money(stress_u),
            "base": money(q * base_u), "stress": money(q * stress_u),
            "series_id": series_id, "source": source,
            "feed_version": feed["version"],
        })

    for p in d["procurement"]:
        add("hardware", p["month"], p["units"], cs["hardware"], f"{p['units']} units procured")
    for i, s in enumerate(d["shipments"]):
        add("freight", s["month"], 1, d["lane_series"], f"shipment {i + 1} ({s['units']} units)")
    hours = D(d["quantity"]) * D(bundle["installation_hours_per_unit"])
    add("installation", d["shipments"][0]["month"], hours, cs["installation"],
        f"{hours.normalize()} installation hours")
    for k in range(d["service"]["term_months"]):
        m = add_months(d["service"]["start_month"], k)
        add("service", m, d["quantity"], cs["service"], f"service month {k + 1}")

    totals = {}
    for cat in ("hardware", "freight", "installation", "service"):
        b = sum((D(l["base"]) for l in lines if l["category"] == cat), ZERO)
        s = sum((D(l["stress"]) for l in lines if l["category"] == cat), ZERO)
        totals[cat] = {"base": money(b), "stress": money(s)}
    base_cost = sum((D(t["base"]) for t in totals.values()), ZERO)
    stress_cost = sum((D(t["stress"]) for t in totals.values()), ZERO)
    return {
        "lines": lines,
        "totals": totals,
        "base_cost": money(base_cost),
        "stress_cost": money(stress_cost),
        "reserve": money(stress_cost - base_cost),
        "stress_scenario": "joint: every line at its stress value",
    }


def list_revenue(d: dict, bundle: dict) -> dict:
    q = D(d["quantity"])
    hw = q * D(bundle["hardware_list_per_unit"])
    inst = q * D(bundle["installation_hours_per_unit"]) * D(bundle["installation_list_per_hour"])
    svc = q * D(bundle["service_list_per_unit_month"]) * D(d["service"]["term_months"])
    return {"hardware": money(hw), "installation": money(inst), "service": money(svc),
            "upfront": money(hw + inst), "recurring": money(svc), "total": money(hw + inst + svc)}


# ---------------------------------------------------------------- floors and authority

def _roles(policy):
    return sorted(((r, D(v)) for r, v in policy["discount_authority"].items()), key=lambda x: x[1])


def floors(stress_cost: Decimal, L: Decimal, policy: dict) -> dict:
    m = D(policy["min_gross_margin"])
    economic_floor = ceil_cent(stress_cost / (Decimal(1) - m))
    auth = {}
    for role, dmax in _roles(policy):
        auth_floor = round_cent(L * (Decimal(1) - dmax))
        lowest = max(economic_floor, auth_floor)
        feasible = lowest <= L
        auth[role] = {
            "max_discount_pct": pct(dmax),
            "authorization_floor": money(auth_floor),
            "lowest_authorized_offer": money(lowest),
            "feasible": feasible,
            "range": [money(lowest), money(L)] if feasible else None,
        }
    return {"min_gross_margin_pct": pct(m), "margin_basis": policy["margin_basis"],
            "economic_floor": money(economic_floor), "authorization": auth}


def evaluate_offer(price: Decimal, ledger: dict, rev: dict, fl: dict, policy: dict,
                   actor_role: str, term_months: int) -> dict:
    L = D(rev["total"])
    base_cost, stress_cost = D(ledger["base_cost"]), D(ledger["stress_cost"])
    econ_floor = D(fl["economic_floor"])
    out = {"price": money(price), "list_revenue": money(L)}
    reasons = []
    if price > L:
        out.update(policy_status="invalid_above_list", required_approval=None,
                   within_actor_authority=False,
                   reasons=["price above list revenue is not a valid offer in this MVP"])
        return out

    discount = (L - price) / L
    upfront = round_cent(price * D(rev["upfront"]) / L)
    recurring = price - upfront
    out.update({
        "discount_pct": pct(discount),
        "upfront": money(upfront),
        "recurring_total": money(recurring),
        "recurring_monthly": money(recurring / D(term_months)),
        "base_margin_pct": pct((price - base_cost) / price),
        "stress_margin_pct": pct((price - stress_cost) / price),
        "stress_margin": ratio((price - stress_cost) / price),
        "base_cost": money(base_cost), "stress_cost": money(stress_cost),
    })

    required = "finance_exception"
    for role, dmax in _roles(policy):
        if discount <= dmax:
            required = role
            break
    authority = dict(_roles(policy))
    actor_max = authority.get(actor_role)
    if actor_max is None:
        raise QuantError("UNKNOWN_ROLE", f"role {actor_role!r} has no discount authority defined",
                         "actor_role")

    if price < econ_floor:
        status = "blocked_below_floor"
        required = "finance_exception"
        reasons.append(f"price is below the economic floor {money(econ_floor)} "
                       f"({fl['min_gross_margin_pct']}% minimum stress margin)")
    elif required == "finance_exception":
        status = "blocked_discount_exceeds_authority"
        reasons.append(f"discount {pct(discount)}% exceeds every role's authority")
    elif required == actor_role or discount <= actor_max:
        status = "compliant"
    else:
        status = f"requires_{required}_approval"
        reasons.append(f"discount {pct(discount)}% exceeds {actor_role} authority "
                       f"({pct(actor_max)}%); needs {required}")
    out.update(policy_status=status, required_approval=required,
               within_actor_authority=(status == "compliant"), reasons=reasons)
    return out


# ---------------------------------------------------------------- packages

def _alt_deal(d: dict, bundle: dict, feed: dict) -> dict | None:
    """Phased alternative: commit only the first shipment's units now, same lane and term."""
    first = d["shipments"][0]
    units = int(d["alternative"].get("phase1_units", first["units"]))
    cap = feed.get("capacity", {}).get(d["bundle"], {}).get("months", {}).get(first["month"])
    if cap is not None:
        units = min(units, cap)
    units = min(units, bundle["max_units_per_shipment"])
    if units <= 0 or units >= d["quantity"]:
        return None
    proc_month = min(d["procurement"][0]["month"], first["month"])
    alt = dict(d)
    alt.update(quantity=units,
               procurement=[{"month": proc_month, "units": units}],
               shipments=[{"month": first["month"], "units": units}])
    return alt


def _package(name, desc, price, ledger, rev, fl, policy, actor_role, term):
    ev = evaluate_offer(price, ledger, rev, fl, policy, actor_role, term)
    return {"package": name, "description": desc, **ev}


def price_deal(deal: dict, feed: dict, policy: dict, price_book: dict, actor_role: str) -> dict:
    """The price_deal tool. actor_role comes from the trusted session, never from the model."""
    if actor_role not in policy["discount_authority"]:
        raise QuantError("UNKNOWN_ROLE", f"role {actor_role!r} has no discount authority defined",
                         "actor_role")
    d, flags = validate_deal(deal, price_book, policy)
    bundle = price_book["bundles"][d["bundle"]]
    term = d["service"]["term_months"]

    age = days_between(feed["as_of"], d["quote_date"])
    if age > policy["max_feed_age_days"]:
        flags.append(_flag("STALE_COST_FEED", "review",
                           f"cost feed {feed['version']} is {age} days old "
                           f"(limit {policy['max_feed_age_days']})"))

    capacity_ok = True
    caps = feed.get("capacity", {}).get(d["bundle"], {}).get("months", {})
    for p in d["procurement"]:
        cap = caps.get(p["month"])
        if cap is not None and p["units"] > cap:
            capacity_ok = False
            flags.append(_flag("CAPACITY_SHORTFALL", "block",
                               f"{p['units']} units needed in {p['month']} but only {cap} are "
                               "available; a higher price cannot fix this, phase the delivery"))

    ledger = build_ledger(d, bundle, feed)
    rev = list_revenue(d, bundle)
    L = D(rev["total"])
    fl = floors(D(ledger["stress_cost"]), L, policy)

    rep_role = _roles(policy)[0][0]
    top_role = _roles(policy)[-1][0]
    econ_floor = D(fl["economic_floor"])

    if not capacity_ok:
        feasibility = {"status": "infeasible_capacity",
                       "reason": "supply capacity cannot cover the requested procurement schedule"}
    elif econ_floor > L:
        feasibility = {"status": "infeasible_under_current_terms",
                       "reason": f"economic floor {money(econ_floor)} is above list revenue "
                                 f"{money(L)}; change scope, timing, or contract terms"}
        flags.append(_flag("INFEASIBLE_UNDER_CURRENT_TERMS", "block", feasibility["reason"]))
    else:
        feasibility = {"status": "feasible", "reason": None}

    packages = []
    if feasibility["status"] == "feasible":
        std_price = D(fl["authorization"][rep_role]["lowest_authorized_offer"])
        packages.append(_package(
            "standard", "Standard scope and terms at the lowest price within rep authority.",
            std_price, ledger, rev, fl, policy, actor_role, term))
        if d["proposed_price"] is not None:
            neg_price, neg_desc = d["proposed_price"], "Requested concession as proposed by the rep."
        else:
            neg_price = D(fl["authorization"][top_role]["lowest_authorized_offer"])
            neg_desc = f"Deepest concession {top_role} authority allows above the economic floor."
        packages.append(_package("negotiated", neg_desc, neg_price, ledger, rev, fl, policy,
                                 actor_role, term))

    alt = _alt_deal(d, bundle, feed)
    if alt is not None:
        alt_ledger = build_ledger(alt, bundle, feed)
        alt_rev = list_revenue(alt, bundle)
        alt_fl = floors(D(alt_ledger["stress_cost"]), D(alt_rev["total"]), policy)
        a = alt_fl["authorization"][rep_role]
        if a["feasible"]:
            pkg = _package(
                "alternative",
                f"Phased delivery: commit {alt['quantity']} units now with the same service term; "
                f"the remaining {d['quantity'] - alt['quantity']} units become a separate option "
                "priced at the time. Costs recomputed for the reduced scope.",
                D(a["lowest_authorized_offer"]), alt_ledger, alt_rev, alt_fl, policy, actor_role, term)
            pkg.update(quantity=alt["quantity"], economic_floor=alt_fl["economic_floor"],
                       ledger_totals=alt_ledger["totals"])
            packages.append(pkg)

    sens_price = None
    for p in packages:
        if p["package"] == "negotiated":
            sens_price = D(p["price"])
    if sens_price is None and packages:
        sens_price = D(packages[0]["price"])
    sens = sensitivity_from_ledger(ledger, sens_price, policy) if sens_price else None

    review = any(f["severity"] in ("review", "block") for f in flags)
    result = {
        "deal_id": d["deal_id"], "account_id": d["account_id"], "bundle": d["bundle"],
        "quantity": d["quantity"], "currency": d["currency"], "actor_role": actor_role,
        "inputs": {
            "price_book_version": price_book["version"], "policy_version": policy["version"],
            "feed_version": feed["version"], "feed_as_of": feed["as_of"],
            "feed_hash": content_hash(feed), "deal_hash": content_hash(deal),
        },
        "schedule": {"procurement": d["procurement"], "shipments": d["shipments"],
                     "service": d["service"], "quote_date": d["quote_date"],
                     "quote_expiry": d["quote_expiry"]},
        "ledger": ledger,
        "list_revenue": rev,
        "floors": fl,
        "feasibility": feasibility,
        "packages": packages,
        "sensitivity": sens,
        "flags": flags,
        "status": "pending_review" if review else "ready_for_review",
        "assumptions": ASSUMPTIONS,
        "exclusions": EXCLUSIONS,
        "evidence_refs": d["evidence_refs"],
    }
    return result


# ---------------------------------------------------------------- sensitivity

def sensitivity_from_ledger(ledger: dict, price: Decimal, policy: dict,
                            hardware_changes=(-10, -5, 0, 5, 10, 15, 20),
                            freight_changes=(0, 10, 20)) -> dict:
    """Stress margin at a fixed price when stress hardware and freight costs move by x%."""
    t = ledger["totals"]
    H, F = D(t["hardware"]["stress"]), D(t["freight"]["stress"])
    O = D(ledger["stress_cost"]) - H - F
    m = D(policy["min_gross_margin"])
    hw_units = sum((D(l["quantity"]) for l in ledger["lines"] if l["category"] == "hardware"), ZERO)
    n_ship = sum(1 for l in ledger["lines"] if l["category"] == "freight")

    grid = []
    for fc in freight_changes:
        row = {"freight_change_pct": fc, "cells": []}
        for hc in hardware_changes:
            cost = H * (1 + D(hc) / 100) + F * (1 + D(fc) / 100) + O
            margin = (price - cost) / price
            row["cells"].append({"hardware_change_pct": hc, "stress_cost": money(cost),
                                 "stress_margin_pct": pct(margin), "meets_policy": margin >= m})
        grid.append(row)

    allowed = price * (1 - m)
    out = {"price": money(price), "min_gross_margin_pct": pct(m), "grid": grid}
    if hw_units > 0:
        out["breakeven_hardware_stress_per_unit"] = money((allowed - F - O) / hw_units)
    if n_ship > 0:
        out["breakeven_freight_stress_per_shipment"] = money((allowed - H - O) / n_ship)
    return out


def sensitivity(deal, feed, policy, price_book, price, hardware_changes=None, freight_changes=None):
    """Standalone tool for the viewer's two sliders."""
    d, _ = validate_deal(deal, price_book, policy)
    ledger = build_ledger(d, price_book["bundles"][d["bundle"]], feed)
    kw = {}
    if hardware_changes is not None:
        kw["hardware_changes"] = tuple(hardware_changes)
    if freight_changes is not None:
        kw["freight_changes"] = tuple(freight_changes)
    return sensitivity_from_ledger(ledger, D(price), policy, **kw)
