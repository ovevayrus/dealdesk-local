"""Production pricing engine against the eight reference cases and policy boundaries."""

from datetime import date
from pathlib import Path

import pytest

from dealdesk import pricing
from dealdesk.pricing import price_deal

from conftest import CASES, DEMO_DATE

NUMERIC_FIELDS = ("base_costs", "stress_costs", "stress_reserve", "offer_revenue", "discount_percent",
                  "stress_margin_percent", "economic_floor")


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_reference_cases(case_id, case_inputs):
    expected = CASES[case_id]["expected"]
    result = price_deal(case_inputs(case_id), today=DEMO_DATE)
    for key, value in expected.items():
        assert result[key] == value, f"{case_id}.{key}"
    if "base_costs" not in expected:
        # Blocked before pricing: no numeric USD appraisal at all.
        for key in NUMERIC_FIELDS:
            assert key not in result


def test_engine_is_independent_of_fixture_validator():
    source = Path(pricing.__file__).read_text(encoding="utf-8")
    assert "validate_pricing_fixtures" not in source.split('"""', 2)[2]


def with_offer(inputs, offer):
    inputs["offer_revenue"] = offer
    return inputs


@pytest.mark.parametrize("offer, outcome", [
    ("144000.00", pricing.REPRESENTATIVE_AUTHORITY),      # exactly 10%: inclusive
    ("143999.99", pricing.DIRECTOR_APPROVAL_REQUIRED),    # one cent past representative authority
    ("130133.34", pricing.DIRECTOR_APPROVAL_REQUIRED),    # exactly the economic floor
    ("130133.33", pricing.BELOW_MARGIN_FLOOR),            # one cent below the floor
    ("160000.00", pricing.REPRESENTATIVE_AUTHORITY),      # list price, 0% discount
])
def test_authority_and_floor_boundaries(case_inputs, offer, outcome):
    result = price_deal(with_offer(case_inputs("standard_offer"), offer), today=DEMO_DATE)
    assert result["approval_outcome"] == outcome
    assert result["release_allowed"] is (outcome == pricing.REPRESENTATIVE_AUTHORITY)


def test_failing_margin_that_displays_as_25_percent_stays_blocked(case_inputs):
    result = price_deal(with_offer(case_inputs("standard_offer"), "130133.33"), today=DEMO_DATE)
    assert result["stress_margin_percent"] == "25.00"
    assert result["meets_margin_floor"] is False
    assert result["approval_outcome"] == pricing.BELOW_MARGIN_FLOOR


def test_director_limit_is_inclusive_at_exactly_20_percent(case_inputs):
    inputs = case_inputs("standard_offer")
    inputs["hardware"][0]["stress_unit_cost"] = "644.00"  # stress total 96,000 -> floor exactly 128,000.00
    exact = price_deal(with_offer(inputs, "128000.00"), today=DEMO_DATE)
    assert exact["economic_floor"] == "128000.00"  # an exact cent is retained, not rounded up
    assert exact["discount_percent"] == "20.00"
    assert exact["approval_outcome"] == pricing.DIRECTOR_APPROVAL_REQUIRED


def test_discount_above_20_percent_is_blocked(case_inputs):
    inputs = case_inputs("standard_offer")
    inputs["hardware"][0]["stress_unit_cost"] = "600.00"  # margin passes, so the authority gate decides
    result = price_deal(with_offer(inputs, "127999.99"), today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.EXCEEDS_DIRECTOR
    assert result["release_allowed"] is False


def test_lowest_authorized_offers(case_inputs):
    result = price_deal(case_inputs("standard_offer"), today=DEMO_DATE)
    assert result["representative_min_offer"] == "144000.00"
    assert result["director_min_offer"] == "130133.34"  # floor binds before the 20% limit (128,000)


def test_category_sums_before_rounding(case_inputs):
    inputs = case_inputs("standard_offer")
    line = {"procurement_date": "2026-11-01", "units": 1, "base_unit_cost": "0.005", "stress_unit_cost": "0.005"}
    inputs["hardware"] = [dict(line), dict(line)]
    inputs["installation"] = {"installation_date": "2026-12-01", "hours": "2.5",
                              "base_loaded_hourly_rate": "33.333", "stress_loaded_hourly_rate": "0.006"}
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["base_costs"]["hardware"] == "0.01"  # 0.005 + 0.005, rounded once (not 0.01 + 0.01)
    assert result["base_costs"]["installation"] == "83.33"  # 2.5 * 33.333 = 83.3325
    assert result["stress_costs"]["installation"] == "0.02"  # 2.5 * 0.006 = 0.015, ROUND_HALF_UP
    assert result["base_costs"]["total"] == "26083.34"  # 0.01 + 2000.00 + 83.33 + 24000.00


@pytest.mark.parametrize("field, value, path", [
    ("currency", None, "currency"),
    ("delivery_date", "", "delivery_date"),
    ("offer_revenue", None, "offer_revenue"),
])
def test_missing_top_level_inputs(case_inputs, field, value, path):
    inputs = case_inputs("standard_offer")
    inputs[field] = value
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.MISSING_CRITICAL_INPUT
    assert path in result["missing_inputs"]
    assert f"Missing critical input: {path}." in result["messages"]
    assert result["release_allowed"] is False
    assert "base_costs" not in result


def test_missing_line_rate_is_reported_not_invented(case_inputs):
    inputs = case_inputs("standard_offer")
    inputs["freight"][0]["stress_cost_per_shipment"] = None
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["missing_inputs"] == ["freight[0].stress_cost_per_shipment"]


@pytest.mark.parametrize("currency", ["EUR", "GBP", "usd"])
def test_unsupported_currency_has_no_usd_appraisal(case_inputs, currency):
    inputs = case_inputs("standard_offer")
    inputs["currency"] = currency
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.UNSUPPORTED_CURRENCY
    assert result["messages"] == [f"Unsupported currency: {currency}; USD only. No FX conversion."]
    for key in NUMERIC_FIELDS:
        assert key not in result


@pytest.mark.parametrize("mutate, field", [
    (lambda i: i.update(offer_revenue="170000.00"), "offer_revenue"),           # premium above list
    (lambda i: i.update(payment_terms="net_90_milestones"), "payment_terms"),  # nonstandard terms
    (lambda i: i["hardware"][0].update(base_unit_cost="-600.00"), "hardware[0].base_unit_cost"),
    (lambda i: i["hardware"][0].update(base_unit_cost="600"), "hardware[0].base_unit_cost"),
    (lambda i: i["hardware"][0].update(base_unit_cost=600.0), "hardware[0].base_unit_cost"),
    (lambda i: i["hardware"][0].update(units=0), "hardware[0].units"),
    (lambda i: i.update(delivery_date="12/01/2026"), "delivery_date"),
    (lambda i: i.update(offer_revenue="144000.001"), "offer_revenue"),
])
def test_invalid_inputs_block_release_with_field_reason(case_inputs, mutate, field):
    inputs = case_inputs("standard_offer")
    mutate(inputs)
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.INVALID_INPUT
    assert field in [item["field"] for item in result["invalid_inputs"]]
    assert result["release_allowed"] is False


def test_quote_expiry_uses_injected_clock(case_inputs):
    on_expiry_day = price_deal(case_inputs("standard_offer"), today=date(2026, 11, 15))
    assert on_expiry_day["quote_expired"] is False and on_expiry_day["release_allowed"] is True
    after = price_deal(case_inputs("standard_offer"), today=date(2026, 11, 16))
    assert after["quote_expired"] is True and after["release_allowed"] is False
    assert after["approval_outcome"] == pricing.REPRESENTATIVE_AUTHORITY
    assert "Quote expired on 2026-11-15; issue a new version before release." in after["messages"]


def test_cost_shock_preserves_original_quote(case_inputs):
    inputs = case_inputs("cost_shock")
    previous = dict(inputs["cost_update"]["previous_quote"])
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["preserved_quote"] == previous
    assert result["offer_revenue"] == previous["offer_revenue"] == "136000.00"
    assert result["quote_version"] == previous["quote_version"]
    assert result["review_required"] is True and result["release_allowed"] is False


def test_cost_update_cannot_change_original_terms(case_inputs):
    inputs = case_inputs("cost_shock")
    inputs["cost_update"]["previous_quote"]["offer_revenue"] = "144000.00"
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.INVALID_INPUT
    assert "cost_update.previous_quote.offer_revenue" in [i["field"] for i in result["invalid_inputs"]]


def test_compliant_economics_still_need_review_after_new_feed(case_inputs):
    inputs = case_inputs("cost_shock")
    inputs["hardware"][0]["stress_unit_cost"] = "660.00"  # new feed, but economics unchanged
    result = price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.DIRECTOR_APPROVAL_REQUIRED
    assert result["review_required"] is True and result["release_allowed"] is False
