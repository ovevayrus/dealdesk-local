"""Production pricing engine for the synthetic policy ``synthetic-demo-v1``.

Implements docs/pricing-policy.md directly: Decimal money, USD only, category
rounding with ROUND_HALF_UP, a 25% stress-margin floor rounded up to the cent,
and inclusive 10% / 20% discount authority. It is written independently of
scripts/validate_pricing_fixtures.py, which checks the reference data.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

POLICY_ID = "synthetic-demo-v1"
SUPPORTED_CURRENCY = "USD"
SUPPORTED_PAYMENT_TERMS = "standard_upfront"
MIN_STRESS_MARGIN = Decimal("0.25")
REPRESENTATIVE_MAX_DISCOUNT = Decimal("0.10")
DIRECTOR_MAX_DISCOUNT = Decimal("0.20")

CENT = Decimal("0.01")
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
PRECISION = 60  # Exact for every product and sum within the accepted input sizes.

CATEGORIES = ("hardware", "freight", "installation", "service")

# Outcomes, in the order the policy evaluates them.
UNSUPPORTED_CURRENCY = "unsupported_currency"
MISSING_CRITICAL_INPUT = "missing_critical_input"
INVALID_INPUT = "invalid_input"
INFEASIBLE = "infeasible_under_current_terms"
BELOW_MARGIN_FLOOR = "below_margin_floor"
EXCEEDS_DIRECTOR = "discount_exceeds_director_authority"
DIRECTOR_APPROVAL_REQUIRED = "director_approval_required"
REPRESENTATIVE_AUTHORITY = "representative_authority"

MESSAGES = {
    INFEASIBLE: "infeasible under current terms",
    BELOW_MARGIN_FLOOR: "Offer is below the stress-margin floor; finance exceptions are outside the MVP.",
    EXCEEDS_DIRECTOR: "Discount exceeds 20%; blocked in the MVP.",
    DIRECTOR_APPROVAL_REQUIRED: "Sales director approval required for this quote version before release.",
}
REVIEW_MESSAGE = "New cost feed requires review; preserve the original quote and approval history."

TOP_LEVEL_FIELDS = (
    "quote_id", "quote_version", "account_id", "bundle_id", "currency", "list_revenue",
    "offer_revenue", "delivery_date", "quote_expires_on", "payment_terms", "cost_feed_version",
    "cost_as_of_date", "stress_scenario", "hardware", "freight", "installation", "service",
)
TEXT_FIELDS = ("quote_id", "account_id", "bundle_id", "cost_feed_version", "stress_scenario")
DATE_FIELDS = ("delivery_date", "quote_expires_on", "cost_as_of_date")

_MONEY_TEXT = re.compile(r"(?:0|[1-9]\d*)\.\d{2,6}")
_DECIMAL_TEXT = re.compile(r"(?:0|[1-9]\d*)(?:\.\d{1,6})?")
MAX_COUNT = 1_000_000
MAX_DECIMAL_CHARS = 24


@dataclass(frozen=True)
class CategoryRule:
    """How one cost category's lines are shaped and multiplied."""

    date_field: str
    count_fields: tuple[str, ...]
    decimal_fields: tuple[str, ...]
    base_rate: str
    stress_rate: str
    single_object: bool = False


RULES = {
    "hardware": CategoryRule("procurement_date", ("units",), (), "base_unit_cost", "stress_unit_cost"),
    "freight": CategoryRule("shipment_date", ("shipments",), (),
                            "base_cost_per_shipment", "stress_cost_per_shipment"),
    "installation": CategoryRule("installation_date", (), ("hours",),
                                 "base_loaded_hourly_rate", "stress_loaded_hourly_rate", single_object=True),
    "service": CategoryRule("start_date", ("active_units", "applicable_months"), (),
                            "base_monthly_cost_per_unit", "stress_monthly_cost_per_unit"),
}
QUANTITY_UNITS = {"hardware": "units", "freight": "shipments", "installation": "hours",
                  "service": "active unit-months"}
RATE_UNITS = {"hardware": "USD/unit", "freight": "USD/shipment", "installation": "USD/hour",
              "service": "USD/active unit/month"}


class _Problems:
    def __init__(self) -> None:
        self.missing: list[str] = []
        self.invalid: list[dict[str, str]] = []

    def bad(self, field: str, message: str) -> None:
        self.invalid.append({"field": field, "message": message})


def _blank(value: Any) -> bool:
    return value is None or value == "" or value == []


def to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def ceil_to_cent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_CEILING)


def money_text(value: Decimal) -> str:
    return format(value.quantize(CENT), "f")


def percent_text(ratio: Decimal) -> str:
    """Display-only percentage; policy gates never use this rounded value."""
    return format((ratio * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP), "f")


def _parse_date(value: Any, field: str, problems: _Problems) -> date | None:
    if not isinstance(value, str):
        problems.bad(field, f"{field} must be an ISO date (YYYY-MM-DD).")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        parsed = None
    if parsed is None or parsed.isoformat() != value:
        problems.bad(field, f"{field} must be an ISO date (YYYY-MM-DD).")
        return None
    return parsed


def _parse_count(value: Any, field: str, problems: _Problems) -> int | None:
    if type(value) is not int or not 0 < value <= MAX_COUNT:
        problems.bad(field, f"{field} must be a whole number from 1 to {MAX_COUNT}.")
        return None
    return value


def _parse_decimal(value: Any, field: str, problems: _Problems, *, money: bool) -> Decimal | None:
    pattern = _MONEY_TEXT if money else _DECIMAL_TEXT
    if not isinstance(value, str) or len(value) > MAX_DECIMAL_CHARS or not pattern.fullmatch(value):
        kind = "a nonnegative USD amount string with 2-6 decimal places" if money else \
            "a nonnegative decimal string with at most 6 decimal places"
        problems.bad(field, f"{field} must be {kind}.")
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        problems.bad(field, f"{field} is not a valid decimal.")
        return None


def _category_lines(inputs: Mapping[str, Any], category: str) -> list[Any]:
    value = inputs[category]
    return [value] if RULES[category].single_object else value


def _validate(inputs: Mapping[str, Any]) -> _Problems:
    problems = _Problems()
    for field in TOP_LEVEL_FIELDS:
        if _blank(inputs.get(field)):
            problems.missing.append(field)

    for field in TEXT_FIELDS:
        if field not in problems.missing and not (isinstance(inputs[field], str) and inputs[field].strip()):
            problems.bad(field, f"{field} must be non-empty text.")
    if "quote_version" not in problems.missing:
        _parse_count(inputs["quote_version"], "quote_version", problems)
    for field in DATE_FIELDS:
        if field not in problems.missing:
            _parse_date(inputs[field], field, problems)

    revenues = {}
    for field in ("list_revenue", "offer_revenue"):
        if field in problems.missing:
            continue
        amount = _parse_decimal(inputs[field], field, problems, money=True)
        if amount is not None and (amount <= ZERO or amount != amount.quantize(CENT)):
            problems.bad(field, f"{field} must be a positive amount in whole cents.")
        elif amount is not None:
            revenues[field] = amount
    if len(revenues) == 2 and revenues["offer_revenue"] > revenues["list_revenue"]:
        problems.bad("offer_revenue", "Offers above list price are outside this demonstration's supported inputs.")

    if "payment_terms" not in problems.missing and inputs["payment_terms"] != SUPPORTED_PAYMENT_TERMS:
        problems.bad("payment_terms",
                     f"Payment terms '{inputs['payment_terms']}' are not supported; "
                     f"only {SUPPORTED_PAYMENT_TERMS} can be priced. Clarify terms before release.")

    for category, rule in RULES.items():
        if category in problems.missing:
            continue
        raw = inputs[category]
        if rule.single_object:
            if not isinstance(raw, Mapping):
                problems.bad(category, f"{category} must be an object.")
                continue
        elif not isinstance(raw, list):
            problems.bad(category, f"{category} must be a list of line items.")
            continue
        for index, line in enumerate(_category_lines(inputs, category)):
            prefix = category if rule.single_object else f"{category}[{index}]"
            if not isinstance(line, Mapping):
                problems.bad(prefix, f"{prefix} must be an object.")
                continue
            fields = (rule.date_field, *rule.count_fields, *rule.decimal_fields, rule.base_rate, rule.stress_rate)
            for field in sorted(fields):
                path = f"{prefix}.{field}"
                value = line.get(field)
                if _blank(value):
                    problems.missing.append(path)
                elif field == rule.date_field:
                    _parse_date(value, path, problems)
                elif field in rule.count_fields:
                    _parse_count(value, path, problems)
                elif field in rule.decimal_fields:
                    quantity = _parse_decimal(value, path, problems, money=False)
                    if quantity is not None and quantity <= ZERO:
                        problems.bad(path, f"{path} must be positive.")
                else:
                    _parse_decimal(value, path, problems, money=True)
    problems.missing.sort()
    return problems


def _ledger(inputs: Mapping[str, Any]) -> tuple[dict[str, dict[str, Decimal]], list[dict[str, Any]]]:
    """Return rounded base/stress category totals plus the line items and rates used.

    Line products stay unrounded within a category; each category is rounded once.
    """
    raw = {"base": dict.fromkeys(CATEGORIES, ZERO), "stress": dict.fromkeys(CATEGORIES, ZERO)}
    lines_used = []
    for category, rule in RULES.items():
        for line in _category_lines(inputs, category):
            quantity = ONE
            for field in rule.count_fields:
                quantity *= Decimal(line[field])
            for field in rule.decimal_fields:
                quantity *= Decimal(line[field])
            base_rate = Decimal(line[rule.base_rate])
            stress_rate = Decimal(line[rule.stress_rate])
            raw["base"][category] += quantity * base_rate
            raw["stress"][category] += quantity * stress_rate
            lines_used.append({
                "category": category,
                "date": line[rule.date_field],
                "quantity": format(quantity.normalize(), "f"),
                "quantity_unit": QUANTITY_UNITS[category],
                "rate_unit": RATE_UNITS[category],
                "base_rate": line[rule.base_rate],
                "stress_rate": line[rule.stress_rate],
                "base_amount": money_text(to_cents(quantity * base_rate)),
                "stress_amount": money_text(to_cents(quantity * stress_rate)),
            })
    ledgers = {}
    for scenario, amounts in raw.items():
        rounded = {category: to_cents(amount) for category, amount in amounts.items()}
        rounded["total"] = sum(rounded.values(), ZERO)
        ledgers[scenario] = rounded
    return ledgers, lines_used


def _lowest_authorized_offer(list_revenue: Decimal, floor: Decimal, max_discount: Decimal) -> Decimal | None:
    lowest = max(floor, ceil_to_cent(list_revenue * (ONE - max_discount)))
    return lowest if lowest <= list_revenue else None


RATE_FIELDS = frozenset(field for rule in RULES.values() for field in (rule.base_rate, rule.stress_rate))
SCOPE_FIELDS = ("quote_id", "quote_version", "account_id", "bundle_id", "currency", "list_revenue", "offer_revenue",
                "delivery_date", "quote_expires_on", "payment_terms")


def quote_scope(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Every quoted term except cost rates: what a same-version cost re-appraisal must keep unchanged."""
    scope: dict[str, Any] = {field: inputs.get(field) for field in SCOPE_FIELDS}
    for category in CATEGORIES:
        lines = inputs.get(category)
        lines = [lines] if isinstance(lines, Mapping) else (lines or [])
        scope[category] = [{k: v for k, v in line.items() if k not in RATE_FIELDS}
                           for line in lines if isinstance(line, Mapping)]
    return scope


def _preserved_quote(inputs: Mapping[str, Any], problems: _Problems) -> dict[str, Any] | None:
    update = inputs.get("cost_update")
    if not isinstance(update, Mapping) or not isinstance(update.get("previous_quote"), Mapping):
        problems.bad("cost_update", "cost_update must contain previous_quote.")
        return None
    previous = update["previous_quote"]
    for field in ("quote_id", "quote_version", "currency", "list_revenue", "offer_revenue"):
        if previous.get(field) != inputs.get(field):
            problems.bad(f"cost_update.previous_quote.{field}",
                         "A cost update re-appraises the same quote; it must not change the original terms.")
    if "scope" in previous and previous["scope"] != quote_scope(inputs):
        problems.bad("cost_update.previous_quote.scope",
                     "Quantities, dates, or terms differ from the original quote; issue a new quote version.")
    if previous.get("cost_feed_version") == inputs.get("cost_feed_version"):
        problems.bad("cost_update.previous_quote.cost_feed_version", "A cost update must use a new feed version.")
    return copy.deepcopy(dict(previous))


def price_deal(inputs: Mapping[str, Any], *, today: date) -> dict[str, Any]:
    """Appraise one quote under policy synthetic-demo-v1.

    ``today`` is injected so quote-expiry checks are reproducible. Returned money
    values are two-place decimal strings; percentages are display strings.
    """
    if not isinstance(inputs, Mapping):
        raise TypeError("inputs must be a mapping")
    result: dict[str, Any] = {
        "policy_id": POLICY_ID,
        "quote_id": inputs.get("quote_id"),
        "quote_version": inputs.get("quote_version"),
        "currency": inputs.get("currency"),
        "approval_outcome": "",
        "release_allowed": False,
        "review_required": "cost_update" in inputs,
        "missing_inputs": [],
        "invalid_inputs": [],
        "messages": [],
    }

    currency = inputs.get("currency")
    if not _blank(currency) and currency != SUPPORTED_CURRENCY:
        result["approval_outcome"] = UNSUPPORTED_CURRENCY
        result["messages"] = [f"Unsupported currency: {currency}; USD only. No FX conversion."]
        return result

    problems = _validate(inputs)
    if problems.missing:
        result["approval_outcome"] = MISSING_CRITICAL_INPUT
        result["missing_inputs"] = problems.missing
        result["invalid_inputs"] = problems.invalid
        result["messages"] = [f"Missing critical input: {field}." for field in problems.missing]
        return result
    preserved = _preserved_quote(inputs, problems) if result["review_required"] else None
    if problems.invalid:
        result["approval_outcome"] = INVALID_INPUT
        result["invalid_inputs"] = problems.invalid
        result["messages"] = [item["message"] for item in problems.invalid]
        return result

    with localcontext() as context:
        context.prec = PRECISION
        ledgers, lines_used = _ledger(inputs)
        base_total = ledgers["base"]["total"]
        stress_total = ledgers["stress"]["total"]
        list_revenue = Decimal(inputs["list_revenue"])
        offer = Decimal(inputs["offer_revenue"])
        concession = list_revenue - offer
        floor = ceil_to_cent(stress_total / (ONE - MIN_STRESS_MARGIN))

        # Gates compare exact amounts by multiplication, never rounded percentages.
        meets_margin = offer * (ONE - MIN_STRESS_MARGIN) >= stress_total
        within_rep = concession <= list_revenue * REPRESENTATIVE_MAX_DISCOUNT
        within_director = concession <= list_revenue * DIRECTOR_MAX_DISCOUNT
        if floor > list_revenue:
            outcome = INFEASIBLE
        elif not meets_margin:
            outcome = BELOW_MARGIN_FLOOR
        elif not within_director:
            outcome = EXCEEDS_DIRECTOR
        elif not within_rep:
            outcome = DIRECTOR_APPROVAL_REQUIRED
        else:
            outcome = REPRESENTATIVE_AUTHORITY

        rep_lowest = _lowest_authorized_offer(list_revenue, floor, REPRESENTATIVE_MAX_DISCOUNT)
        director_lowest = _lowest_authorized_offer(list_revenue, floor, DIRECTOR_MAX_DISCOUNT)
        result.update({
            "account_id": inputs["account_id"],
            "bundle_id": inputs["bundle_id"],
            "cost_feed_version": inputs["cost_feed_version"],
            "cost_as_of_date": inputs["cost_as_of_date"],
            "stress_scenario": inputs["stress_scenario"],
            "quote_expires_on": inputs["quote_expires_on"],
            "approval_outcome": outcome,
            "list_revenue": money_text(list_revenue),
            "offer_revenue": money_text(offer),
            "discount_amount": money_text(concession),
            "discount_percent": percent_text(concession / list_revenue),
            "base_costs": {key: money_text(value) for key, value in ledgers["base"].items()},
            "stress_costs": {key: money_text(value) for key, value in ledgers["stress"].items()},
            "stress_reserve": money_text(stress_total - base_total),
            "expected_margin_percent": percent_text((offer - base_total) / offer),
            "stress_margin_percent": percent_text((offer - stress_total) / offer),
            "economic_floor": money_text(floor),
            "representative_min_offer": money_text(rep_lowest) if rep_lowest is not None else None,
            "director_min_offer": money_text(director_lowest) if director_lowest is not None else None,
            "meets_margin_floor": meets_margin,
            "within_representative_authority": within_rep,
            "within_director_authority": within_director,
            "ledger_lines": lines_used,
            "quote_scope": quote_scope(inputs),
        })

    if outcome in MESSAGES:
        result["messages"].append(MESSAGES[outcome])
    result["release_allowed"] = outcome == REPRESENTATIVE_AUTHORITY

    expires_on = date.fromisoformat(inputs["quote_expires_on"])
    result["quote_expired"] = today > expires_on
    if result["quote_expired"]:
        result["release_allowed"] = False
        result["messages"].append(f"Quote expired on {expires_on.isoformat()}; issue a new version before release.")

    if result["review_required"]:
        result["preserved_quote"] = preserved
        result["release_allowed"] = False
        result["messages"].append(REVIEW_MESSAGE)
    return result
