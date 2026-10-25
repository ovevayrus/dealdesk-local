"""Synthetic deal requests and dated cost feeds -> pricing-engine inputs.

Each ledger line takes the feed rate in effect on that line's own date
(procurement, shipment, installation, or service start); nothing is averaged.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .config import SYNTHETIC_DIR

DEALS_DIR = SYNTHETIC_DIR / "deals"
FEEDS_DIR = SYNTHETIC_DIR / "cost_feeds"
REFERENCE_QUOTE_ID = "SYN-REFERENCE-001"
INITIAL_FEED_VERSION = "synthetic-costs-v1"
SHOCK_FEED_VERSION = "synthetic-costs-v2"

# category -> (deal line date field, rate-matching key, pricing base/stress field names)
_LINE_SPECS = {
    "hardware": ("procurement_date", "sku", "base_unit_cost", "stress_unit_cost"),
    "freight": ("shipment_date", "lane", "base_cost_per_shipment", "stress_cost_per_shipment"),
    "installation": ("installation_date", "role", "base_loaded_hourly_rate", "stress_loaded_hourly_rate"),
    "service": ("start_date", "plan", "base_monthly_cost_per_unit", "stress_monthly_cost_per_unit"),
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_deal(quote_id: str = REFERENCE_QUOTE_ID) -> dict[str, Any]:
    return _read_json(DEALS_DIR / f"{quote_id}.json")


def load_feed(version: str) -> dict[str, Any]:
    path = FEEDS_DIR / f"{version}.json"
    if not path.is_file():
        raise KeyError(f"Unknown cost feed version: {version}")
    return _read_json(path)


def select_rate(feed: dict[str, Any], category: str, match_value: str | None, on: date) -> dict[str, Any] | None:
    """Return the latest rate whose effective_from is on or before ``on``."""
    _, match_key, _, _ = _LINE_SPECS[category]
    candidates = [
        rate for rate in feed["rates"].get(category, [])
        if (match_value is None or rate.get(match_key) == match_value)
        and date.fromisoformat(rate["effective_from"]) <= on
    ]
    return max(candidates, key=lambda rate: rate["effective_from"], default=None)


def build_pricing_inputs(deal: dict[str, Any], feed: dict[str, Any], offer_revenue: str,
                         quote_version: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (pricing inputs in the fixture shape, provenance for every rate used).

    A rate that cannot be found is left as None so the engine reports a missing input
    instead of inventing a cost.
    """
    inputs: dict[str, Any] = {
        "quote_id": deal.get("quote_id"),
        "quote_version": quote_version,
        "currency": deal.get("currency"),
        "list_revenue": deal.get("list_revenue"),
        "offer_revenue": offer_revenue,
        "delivery_date": deal.get("delivery_date"),
        "quote_expires_on": deal.get("quote_expires_on"),
        "payment_terms": deal.get("payment_terms"),
        "cost_feed_version": feed["feed_version"],
        "cost_as_of_date": feed["as_of_date"],
        "stress_scenario": feed["stress_scenario"],
    }
    provenance = []
    for category, (date_field, match_key, base_field, stress_field) in _LINE_SPECS.items():
        raw_lines = deal.get(category)
        single = isinstance(raw_lines, dict)
        lines = [raw_lines] if single else (raw_lines or [])
        built = []
        for line in lines:
            line_date = line.get(date_field)
            rate = select_rate(feed, category, line.get(match_key), date.fromisoformat(line_date)) \
                if line_date else None
            out = {key: value for key, value in line.items() if key != match_key}
            out[base_field] = rate["base"] if rate else None
            out[stress_field] = rate["stress"] if rate else None
            built.append(out)
            if rate:
                provenance.append({
                    "category": category,
                    "line_date": line_date,
                    "matched": line.get(match_key),
                    "effective_from": rate["effective_from"],
                    "base": rate["base"],
                    "stress": rate["stress"],
                    "unit": rate["unit"],
                    "source": rate["source"],
                    "feed_version": feed["feed_version"],
                })
        inputs[category] = (built[0] if built else None) if single else built
    inputs["account_id"] = deal.get("account_id")
    inputs["bundle_id"] = deal.get("bundle_id")
    return inputs, provenance
