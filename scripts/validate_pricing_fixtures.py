#!/usr/bin/env python3
"""Check synthetic reference data, independently of the production pricing engine."""

import argparse
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CENT = Decimal("0.01")
ONE = Decimal("1")
HUNDRED = Decimal("100")
MIN_MARGIN = Decimal("0.25")
REP_DISCOUNT = Decimal("0.10")
DIRECTOR_DISCOUNT = Decimal("0.20")
POLICY = {
    "id": "synthetic-demo-v1",
    "currency": "USD",
    "minimum_gross_margin": "0.25",
    "representative_max_discount": "0.10",
    "director_max_discount": "0.20",
    "cost_rounding": "ROUND_HALF_UP",
    "floor_rounding": "ROUND_CEILING",
    "display_percentage_places": 2,
}
CASE_NAMES = {
    "standard_offer": "STANDARD OFFER",
    "negotiated_offer": "NEGOTIATED OFFER",
    "cost_shock": "COST SHOCK",
    "infeasible_deal": "INFEASIBLE DEAL",
    "recurring_service": "RECURRING SERVICE",
    "freight_units": "FREIGHT UNITS",
    "missing_delivery_date": "MISSING DELIVERY DATE",
    "unsupported_currency": "UNSUPPORTED CURRENCY",
}
MONEY_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2,6}\Z")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def decimal_value(value, label):
    check(isinstance(value, str), f"{label}: use a decimal string")
    check(re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,6})?", value),
          f"{label}: expected a nonnegative decimal, at most six fractional places")
    check(len(value) <= 24, f"{label}: exceeds this reference validator's precision range")
    return Decimal(value)


def money(value, label, contract=False):
    check(isinstance(value, str) and MONEY_PATTERN.fullmatch(value),
          f"{label}: money must be a nonnegative decimal string with 2-6 fractional places")
    number = decimal_value(value, label)
    if contract:
        check(number > 0 and number == number.quantize(CENT),
              f"{label}: contract revenue must be positive and cent-valued")
    return number


def count(value, label):
    check(type(value) is int and 0 < value <= 1_000_000,
          f"{label}: expected an integer count from 1 to 1000000")
    return Decimal(value)


def iso_date(value, label):
    check(isinstance(value, str), f"{label}: expected an ISO date")
    parsed = date.fromisoformat(value)
    check(parsed.isoformat() == value, f"{label}: expected YYYY-MM-DD")
    return parsed


def cents(value, rounding=ROUND_HALF_UP):
    return format(value.quantize(CENT, rounding=rounding), ".2f")


def validate_inputs(inputs):
    """Validate representations even when the intentional missing-date case blocks pricing."""
    check(isinstance(inputs, dict), "inputs must be an object")
    fields = (
        "quote_id", "quote_version", "account_id", "bundle_id", "currency", "list_revenue", "offer_revenue",
        "delivery_date", "quote_expires_on", "payment_terms", "cost_feed_version",
        "cost_as_of_date", "stress_scenario", "hardware", "freight", "installation", "service",
    )
    missing = sorted(key for key in fields if inputs.get(key) in (None, "", []))
    check(not (set(inputs) - set(fields) - {"cost_update"}), "unknown input fields")
    for key in ("quote_id", "account_id", "bundle_id", "currency", "cost_feed_version", "stress_scenario"):
        if key not in missing:
            check(isinstance(inputs[key], str) and inputs[key].strip(), f"{key}: expected text")
    if "quote_version" not in missing:
        count(inputs["quote_version"], "quote_version")
    for key in ("delivery_date", "quote_expires_on", "cost_as_of_date"):
        if key not in missing:
            iso_date(inputs[key], key)
    for key in ("list_revenue", "offer_revenue"):
        if key not in missing:
            money(inputs[key], key, contract=True)
    if not {"list_revenue", "offer_revenue"}.intersection(missing):
        check(Decimal(inputs["offer_revenue"]) <= Decimal(inputs["list_revenue"]),
              "premium prices above list are outside these demonstration fixtures")
    if "payment_terms" not in missing:
        check(inputs["payment_terms"] == "standard_upfront", "nonstandard payment terms need review")

    line_specs = {
        "hardware": ("procurement_date", ("units",), ("base_unit_cost", "stress_unit_cost")),
        "freight": ("shipment_date", ("shipments",),
                    ("base_cost_per_shipment", "stress_cost_per_shipment")),
        "installation": ("installation_date", (),
                         ("base_loaded_hourly_rate", "stress_loaded_hourly_rate")),
        "service": ("start_date", ("active_units", "applicable_months"),
                    ("base_monthly_cost_per_unit", "stress_monthly_cost_per_unit")),
    }
    for category, (date_key, counts, rates) in line_specs.items():
        if category in missing:
            continue
        lines = [inputs[category]] if category == "installation" else inputs[category]
        check(isinstance(lines, list) and lines, f"{category}: expected nonempty line items")
        for index, line in enumerate(lines):
            label = category if category == "installation" else f"{category}[{index}]"
            check(isinstance(line, dict), f"{label}: expected an object")
            keys = {date_key, *counts, *rates}
            if category == "installation":
                keys.add("hours")
            check(not set(line) - keys, f"{label}: unknown fields")
            for key in sorted(keys):
                path = f"{label}.{key}"
                if line.get(key) in (None, ""):
                    missing.append(path)
                elif key == date_key:
                    iso_date(line[key], path)
                elif key in counts:
                    count(line[key], path)
                elif key == "hours":
                    check(decimal_value(line[key], path) > 0, f"{path}: must be positive")
                else:
                    money(line[key], path)
    return sorted(missing)


def cost_totals(inputs, scenario):
    """Sum each category once, settle that category to cents, then total the ledger."""
    hardware = sum((Decimal(row["units"]) * Decimal(row[f"{scenario}_unit_cost"])
                    for row in inputs["hardware"]), Decimal("0"))
    freight = sum((Decimal(row["shipments"]) * Decimal(row[f"{scenario}_cost_per_shipment"])
                   for row in inputs["freight"]), Decimal("0"))
    installation = (Decimal(inputs["installation"]["hours"])
                    * Decimal(inputs["installation"][f"{scenario}_loaded_hourly_rate"]))
    service = sum((Decimal(row["active_units"]) * Decimal(row["applicable_months"])
                   * Decimal(row[f"{scenario}_monthly_cost_per_unit"])
                   for row in inputs["service"]), Decimal("0"))
    costs = dict(zip(("hardware", "freight", "installation", "service"),
                     map(cents, (hardware, freight, installation, service))))
    costs["total"] = cents(sum(map(Decimal, costs.values()), Decimal("0")))
    return costs


def preserved_quote(inputs):
    """Check the historical fixture snapshot; this does not test application persistence."""
    update = inputs["cost_update"]
    check(isinstance(update, dict) and set(update) == {"reason", "previous_quote"},
          "cost_update requires reason and previous_quote")
    check(update["reason"] == "new_cost_feed", "cost_update: unknown review reason")
    previous = update["previous_quote"]
    keys = {"quote_id", "quote_version", "currency", "list_revenue", "offer_revenue",
            "cost_feed_version", "stress_cost", "economic_floor", "approval"}
    check(isinstance(previous, dict) and set(previous) == keys, "invalid previous_quote shape")
    for key in ("quote_id", "quote_version", "currency", "list_revenue", "offer_revenue"):
        check(previous[key] == inputs[key], f"cost update changed original {key}")
    check(previous["cost_feed_version"] != inputs["cost_feed_version"],
          "cost update must identify a new feed version")
    for key in ("list_revenue", "offer_revenue", "stress_cost", "economic_floor"):
        money(previous[key], f"previous_quote.{key}", contract=key.endswith("revenue"))
    old_cost = Decimal(previous["stress_cost"])
    old_revenue = Decimal(previous["offer_revenue"])
    check(previous["economic_floor"] == cents(old_cost / (ONE - MIN_MARGIN), ROUND_CEILING),
          "previous quote floor is incorrect")
    check(old_revenue * (ONE - MIN_MARGIN) >= old_cost,
          "previous approved quote must meet its original margin floor")
    check((Decimal(previous["list_revenue"]) - old_revenue)
          <= Decimal(previous["list_revenue"]) * DIRECTOR_DISCOUNT,
          "previous approved quote exceeds director authority")
    approval = previous["approval"]
    check(isinstance(approval, dict) and set(approval) == {
        "role", "quote_id", "quote_version", "approved_offer_revenue", "expires_on"
    }, "invalid previous approval shape")
    check(approval["role"] == "sales_director", "historical concession requires sales director")
    for key in ("quote_id", "quote_version"):
        check(approval[key] == previous[key], f"approval is not bound to original {key}")
    money(approval["approved_offer_revenue"], "approval.approved_offer_revenue", contract=True)
    check(approval["approved_offer_revenue"] == previous["offer_revenue"],
          "approval price differs from original offer")
    iso_date(approval["expires_on"], "approval.expires_on")
    check(approval["expires_on"] == inputs["quote_expires_on"], "approval expiry mismatch")
    return previous


def calculate_expected(inputs):
    missing = validate_inputs(inputs)
    result = {
        "currency": inputs.get("currency"),
        "approval_outcome": "",
        "release_allowed": False,
        "review_required": "cost_update" in inputs,
        "missing_inputs": missing,
        "messages": [],
    }
    if inputs.get("currency") not in (None, "USD"):
        result["approval_outcome"] = "unsupported_currency"
        result["messages"] = [f"Unsupported currency: {inputs['currency']}; USD only. No FX conversion."]
        return result
    if missing:
        result["approval_outcome"] = "missing_critical_input"
        result["messages"] = [f"Missing critical input: {key}." for key in missing]
        return result

    base = cost_totals(inputs, "base")
    stress = cost_totals(inputs, "stress")
    cost = Decimal(stress["total"])
    revenue = Decimal(inputs["offer_revenue"])
    list_revenue = Decimal(inputs["list_revenue"])
    concession = list_revenue - revenue
    floor = cents(cost / (ONE - MIN_MARGIN), ROUND_CEILING)
    result.update({
        "base_costs": base,
        "stress_costs": stress,
        "stress_reserve": cents(cost - Decimal(base["total"])),
        "offer_revenue": cents(revenue),
        "discount_percent": cents(concession / list_revenue * HUNDRED),
        "stress_margin_percent": cents((revenue - cost) / revenue * HUNDRED),
        "economic_floor": floor,
    })
    # Authority and margin checks use exact amounts, never rounded display percentages.
    if Decimal(floor) > list_revenue:
        result["approval_outcome"] = "infeasible_under_current_terms"
        result["messages"].append("infeasible under current terms")
    elif revenue * (ONE - MIN_MARGIN) < cost:
        result["approval_outcome"] = "below_margin_floor"
        result["messages"].append("Offer is below the stress-margin floor; finance exceptions are outside the MVP.")
    elif concession > list_revenue * DIRECTOR_DISCOUNT:
        result["approval_outcome"] = "discount_exceeds_director_authority"
        result["messages"].append("Discount exceeds 20%; blocked in the MVP.")
    elif concession > list_revenue * REP_DISCOUNT:
        result["approval_outcome"] = "director_approval_required"
        result["messages"].append("Sales director approval required for this quote version before release.")
    else:
        result["approval_outcome"] = "representative_authority"
        result["release_allowed"] = True
    if result["review_required"]:
        result["preserved_quote"] = preserved_quote(inputs)
        result["release_allowed"] = False
        result["messages"].append("New cost feed requires review; preserve the original quote and approval history.")
    return result


def compare(actual, expected, path="expected"):
    """Report a specific field rather than a large opaque JSON mismatch."""
    check(type(actual) is type(expected), f"{path}: wrong type")
    if isinstance(actual, dict):
        check(actual.keys() == expected.keys(),
              f"{path}: field mismatch (required {sorted(actual)}, found {sorted(expected)})")
        for key in actual:
            compare(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(actual, list):
        check(len(actual) == len(expected), f"{path}: wrong number of items")
        for index, value in enumerate(actual):
            compare(value, expected[index], f"{path}[{index}]")
    else:
        check(actual == expected, f"{path}: calculated {actual!r}, fixture has {expected!r}")


def reject_float(value):
    raise ValueError(f"JSON numeric literal {value!r}: use a decimal string instead")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", nargs="?", type=Path,
                        default=ROOT / "tests" / "fixtures" / "pricing_cases.json")
    args = parser.parse_args()
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"), parse_float=reject_float,
                          parse_constant=reject_float, object_pairs_hook=unique_object)
        check(isinstance(data, dict) and set(data) == {
            "schema_version", "synthetic", "description", "policy", "units", "cases"
        }, "invalid fixture document shape")
        check(data["schema_version"] == "1.0" and data["synthetic"] is True,
              "fixtures must be schema 1.0 and explicitly synthetic")
        check(isinstance(data["description"], str) and data["description"].strip(), "missing description")
        compare(POLICY, data["policy"], "policy")
        compare({"money": "inputs.currency", "hardware": "unit",
                 "freight": "shipment", "installation": "hour",
                 "service": "active_unit * month"}, data["units"], "units")
        cases = data["cases"]
        check(isinstance(cases, list) and len(cases) == 8, "expected exactly eight cases")
        ids = [case.get("id") for case in cases if isinstance(case, dict)]
        check(len(ids) == 8 and set(ids) == set(CASE_NAMES), "missing, duplicate, or unknown case IDs")
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"FAIL fixture structure: {error}")
        return 1

    passed = 0
    with localcontext() as context:
        context.prec = 80  # Products are exact within the input bounds; ratios are display only.
        for case in cases:
            try:
                check(set(case) == {"id", "name", "purpose", "inputs", "expected", "calculation"},
                      "invalid case shape")
                check(case["name"] == CASE_NAMES[case["id"]], "incorrect case name")
                for field in ("purpose", "calculation"):
                    check(isinstance(case[field], str) and case[field].strip(), f"missing {field}")
                compare(calculate_expected(case["inputs"]), case["expected"])
                print(f"PASS {case['id']}: {case['expected']['approval_outcome']}")
                passed += 1
            except (ValueError, TypeError, KeyError, ArithmeticError) as error:
                print(f"FAIL {case.get('id', '?')}: {error}")
    print(f"\n{passed}/8 pricing fixtures passed.")
    return 0 if passed == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
