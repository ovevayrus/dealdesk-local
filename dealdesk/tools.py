"""The bounded tool set the chatbot (or an external agent runtime) may call.

search_documents, price_deal, forecast_costs, and apply_demo_cost_update all run
locally against synthetic data. Every number shown to the user comes from these
structured results.
"""

from __future__ import annotations

import json
from typing import Any

from . import documents, forecast, pricing
from .config import Settings
from .costs import (INITIAL_FEED_VERSION, REFERENCE_QUOTE_ID, SHOCK_FEED_VERSION, build_pricing_inputs, load_deal,
                    load_feed)
from .state import Store

PRICED_OUTCOMES = {
    pricing.INFEASIBLE, pricing.BELOW_MARGIN_FLOOR, pricing.EXCEEDS_DIRECTOR,
    pricing.DIRECTOR_APPROVAL_REQUIRED, pricing.REPRESENTATIVE_AUTHORITY,
}
MANUAL = "manual"
SCHEDULED = "scheduled_watcher"
FEED_KEYS = {"feed_version", "as_of_date", "stress_scenario", "rates"}


class DemoTools:
    def __init__(self, settings: Settings, store: Store) -> None:
        self.settings = settings
        self.store = store

    # -- context -----------------------------------------------------------------
    def active_feed(self) -> dict[str, Any]:
        return self.store.get("active_feed") or load_feed(INITIAL_FEED_VERSION)

    def open_quote(self) -> dict[str, Any] | None:
        return self.store.latest_quote(REFERENCE_QUOTE_ID)

    # -- search_documents -----------------------------------------------------------
    def search_documents(self, query: str, account_id: str | None = None,
                         doc_types: list[str] | None = None, limit: int = 4) -> list[dict[str, Any]]:
        return documents.search_documents(query, account_id=account_id, doc_types=doc_types, limit=limit)

    # -- price_deal -------------------------------------------------------------------
    def appraise(self, offer_revenue: str, quote_version: int, *, currency: str | None = None,
                 feed: dict[str, Any] | None = None, deal: dict[str, Any] | None = None) -> dict[str, Any]:
        deal = dict(deal or load_deal())
        if currency:
            deal["currency"] = currency
        inputs, provenance = build_pricing_inputs(deal, feed or self.active_feed(), offer_revenue, quote_version)
        result = pricing.price_deal(inputs, today=self.settings.today())
        result["rate_provenance"] = provenance
        result["account_name"] = deal.get("account_name")
        result["bundle_name"] = deal.get("bundle_name")
        return result

    def recommended_offer(self) -> str | None:
        """Lowest price within representative authority that also meets the stress-margin floor."""
        deal = load_deal()
        at_list = self.appraise(deal["list_revenue"], 1)
        return at_list.get("representative_min_offer")

    def price_deal(self, offer_revenue: str | None = None, currency: str | None = None) -> dict[str, Any]:
        """Appraise an offer for the reference deal; a priced change creates a new quote version."""
        if offer_revenue is None:
            offer_revenue = self.recommended_offer() or load_deal()["list_revenue"]
        feed = self.active_feed()
        latest = self.open_quote()
        if (latest and currency in (None, "USD") and latest["offer_revenue"] == offer_revenue
                and latest["feed_version"] == feed["feed_version"]):
            return dict(latest["appraisal"], quote_version_created=False)
        version = (latest["version"] + 1) if latest else 1
        appraisal = self.appraise(offer_revenue, version, currency=currency, feed=feed)
        if appraisal["approval_outcome"] not in PRICED_OUTCOMES:
            return dict(appraisal, quote_version_created=False)
        self.store.add_quote_version(REFERENCE_QUOTE_ID, version, appraisal["offer_revenue"],
                                     feed["feed_version"], appraisal)
        return dict(appraisal, quote_version_created=True)

    def price_incomplete_request(self, account_id: str, account_name: str) -> dict[str, Any]:
        """No deal request exists for this account; the engine reports exactly what is missing."""
        skeleton = {"quote_id": f"SYN-DRAFT-{account_id[-3:]}", "account_id": account_id,
                    "account_name": account_name, "currency": "USD", "payment_terms": "standard_upfront"}
        inputs, _ = build_pricing_inputs(skeleton, self.active_feed(), None, 1)
        result = pricing.price_deal(inputs, today=self.settings.today())
        result["account_name"] = account_name
        return result

    # -- forecast_costs -----------------------------------------------------------------
    def forecast_costs(self, horizon: int = 6) -> dict[str, Any]:
        return forecast.forecast_costs(self.active_feed(), load_deal(), self.settings.today(), horizon)

    # -- apply_demo_cost_update -----------------------------------------------------------
    def _ensure_open_quote(self) -> tuple[dict[str, Any], bool]:
        quote = self.open_quote()
        if quote:
            return quote, False
        self.price_deal(None)
        return self.open_quote(), True

    def _revised_appraisal(self, quote: dict[str, Any], new_feed: dict[str, Any]) -> dict[str, Any]:
        original = quote["appraisal"]
        deal = load_deal()
        inputs, provenance = build_pricing_inputs(deal, new_feed, quote["offer_revenue"], quote["version"])
        inputs["cost_update"] = {
            "reason": "new_cost_feed",
            "previous_quote": {
                "quote_id": original["quote_id"],
                "quote_version": original["quote_version"],
                "currency": original["currency"],
                "list_revenue": original["list_revenue"],
                "offer_revenue": original["offer_revenue"],
                "cost_feed_version": original["cost_feed_version"],
                "stress_cost": original["stress_costs"]["total"],
                "economic_floor": original["economic_floor"],
                "approval_status": original["approval_outcome"],
            },
        }
        revised = pricing.price_deal(inputs, today=self.settings.today())
        revised["rate_provenance"] = provenance
        revised["account_name"] = deal.get("account_name")
        revised["bundle_name"] = deal.get("bundle_name")
        return revised

    def preview_cost_update(self, feed_version: str = SHOCK_FEED_VERSION) -> dict[str, Any]:
        """What-if appraisal under the supplier feed; nothing is stored or changed."""
        quote = self.open_quote()
        if quote is None:
            offer = self.recommended_offer()
            appraisal = self.appraise(offer, 1)
            quote = {"version": 1, "offer_revenue": offer, "appraisal": appraisal}
        new_feed = load_feed(feed_version)
        if self.active_feed()["feed_version"] == new_feed["feed_version"]:
            return dict(self.apply_cost_feed(new_feed, MANUAL), preview=True)  # already applied: no change
        return {"preview": True, "already_applied": False, "original": quote["appraisal"],
                "revised": self._revised_appraisal(quote, new_feed), "feed": _feed_summary(new_feed)}

    def apply_cost_feed(self, new_feed: dict[str, Any], source: str) -> dict[str, Any]:
        """Record a new feed: keep the open quote unchanged and add a separate, reviewed appraisal."""
        if not FEED_KEYS <= set(new_feed):
            raise ValueError("Cost feed is missing feed_version, as_of_date, stress_scenario, or rates.")
        current = self.active_feed()
        if new_feed["feed_version"] == current["feed_version"]:
            events = [e for e in self.store.review_events() if e["feed_version"] == new_feed["feed_version"]]
            event = events[-1] if events else None
            original = next((q["appraisal"] for q in self.store.quote_versions(event["quote_id"])
                             if q["version"] == event["quote_version"]), None) if event else None
            return {"preview": False, "already_applied": True, "source": source, "original": original,
                    "revised": event["revised_appraisal"] if event else None, "event": event,
                    "feed": _feed_summary(new_feed)}
        quote, created_quote = self._ensure_open_quote()
        revised = self._revised_appraisal(quote, new_feed)
        self.store.set("active_feed", new_feed)
        event, created = self.store.add_review_event(
            quote_id=quote["quote_id"], quote_version=quote["version"], feed_version=new_feed["feed_version"],
            previous_feed_version=current["feed_version"], source=source, revised_appraisal=revised)
        return {"preview": False, "already_applied": not created, "source": source,
                "created_standard_quote": created_quote, "original": quote["appraisal"],
                "revised": revised, "event": event, "feed": _feed_summary(new_feed)}

    def apply_demo_cost_update(self, source: str = MANUAL) -> dict[str, Any]:
        return self.apply_cost_feed(load_feed(SHOCK_FEED_VERSION), source)

    # -- scheduled watcher ------------------------------------------------------------
    def poll_incoming_feeds(self) -> list[dict[str, Any]]:
        """Apply each new feed file dropped into the local incoming folder, once."""
        folder = self.settings.incoming_feed_dir
        if not folder.is_dir():
            return []
        seen = set(self.store.get("watcher_seen_feeds", []))
        applied = []
        for path in sorted(folder.glob("*.json")):
            try:
                feed = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            version = feed.get("feed_version") if isinstance(feed, dict) else None
            if not version or version in seen or not FEED_KEYS <= set(feed):
                continue
            seen.add(version)
            self.store.set("watcher_seen_feeds", sorted(seen))
            applied.append(self.apply_cost_feed(feed, SCHEDULED))
        return applied

    # -- reset ----------------------------------------------------------------------
    def reset(self) -> None:
        self.store.reset()
        folder = self.settings.incoming_feed_dir
        if folder.is_dir():
            for path in folder.glob("*.json"):
                path.unlink()


def _feed_summary(feed: dict[str, Any]) -> dict[str, Any]:
    return {key: feed.get(key) for key in ("feed_version", "as_of_date", "stress_scenario", "description")}


TOOL_NAMES = ("search_documents", "price_deal", "forecast_costs", "apply_demo_cost_update")


def _tool_summary(name: str, result: Any) -> str:
    if name == "search_documents":
        return f"{len(result)} passages"
    if name == "forecast_costs":
        return f"{len(result['series'])} series as of {result['as_of_date']}"
    if name == "apply_demo_cost_update":
        outcome = (result.get("revised") or {}).get("approval_outcome", "no open quote")
        return ("preview: " if result.get("preview") else "") + ("already applied: " if result.get(
            "already_applied") else "") + outcome
    return result["approval_outcome"]


def run_tool(tools: DemoTools, store: Store, name: str, arguments: dict[str, Any], caller: str) -> dict[str, Any]:
    """Run one named tool for an external local agent (HTTP or CLI) and log it for the viewer."""
    if not isinstance(arguments, dict):
        raise TypeError("arguments must be a JSON object")
    if name == "search_documents":
        result: Any = tools.search_documents(str(arguments.get("query", "")), account_id=arguments.get("account_id"),
                                             doc_types=arguments.get("doc_types"),
                                             limit=int(arguments.get("limit", 4)))
    elif name == "price_deal":
        offer = arguments.get("offer_revenue")
        result = tools.price_deal(None if offer is None else str(offer), currency=arguments.get("currency"))
    elif name == "forecast_costs":
        result = tools.forecast_costs(int(arguments.get("horizon", 6)))
    elif name == "apply_demo_cost_update":
        result = tools.preview_cost_update() if arguments.get("preview") else tools.apply_demo_cost_update()
    else:
        raise KeyError(f"Unknown tool {name!r}; available: {', '.join(TOOL_NAMES)}")
    summary = _tool_summary(name, result)
    store.set("external_tool_calls", store.get("external_tool_calls", 0) + 1)
    store.set("external_last_caller", caller)
    store.add_message("event", {"kind": "tool_call", "caller": caller, "tool": name, "arguments": arguments,
                                "summary": summary, "result": result})
    return {"tool": name, "caller": caller, "summary": summary, "result": result}
