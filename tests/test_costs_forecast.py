"""Deal + dated cost feed -> pricing inputs, and the reproducible synthetic forecast."""

from datetime import date

from conftest import CASES, DEMO_DATE

from dealdesk import pricing
from dealdesk.costs import build_pricing_inputs, load_deal, load_feed
from dealdesk.forecast import SERIES, forecast_costs, generate_history, load_history


def test_demo_deal_and_initial_feed_reproduce_reference_inputs():
    inputs, provenance = build_pricing_inputs(load_deal(), load_feed("synthetic-costs-v1"), "136000.00", 1)
    assert inputs == CASES["negotiated_offer"]["inputs"]
    assert {p["category"] for p in provenance} == {"hardware", "freight", "installation", "service"}
    assert all(p["source"] and p["effective_from"] for p in provenance)


def test_supplier_feed_reproduces_cost_shock_inputs():
    inputs, _ = build_pricing_inputs(load_deal(), load_feed("synthetic-costs-v2"), "136000.00", 1)
    expected = dict(CASES["cost_shock"]["inputs"])
    expected.pop("cost_update")
    assert inputs == expected


def test_rates_follow_each_line_date():
    deal = load_deal()
    deal["hardware"] = [dict(deal["hardware"][0], procurement_date="2026-10-20")]  # before the 2026-10-26 notice
    inputs, provenance = build_pricing_inputs(deal, load_feed("synthetic-costs-v2"), "136000.00", 1)
    assert inputs["hardware"][0]["stress_unit_cost"] == "660.00"
    assert provenance[0]["source"] == "Synthetic supplier price list SPL-2026-10"


def test_missing_rate_becomes_missing_input_not_zero():
    deal = load_deal()
    deal["hardware"] = [dict(deal["hardware"][0], procurement_date="2025-01-01")]  # no rate effective yet
    inputs, _ = build_pricing_inputs(deal, load_feed("synthetic-costs-v1"), "144000.00", 1)
    result = pricing.price_deal(inputs, today=DEMO_DATE)
    assert result["approval_outcome"] == pricing.MISSING_CRITICAL_INPUT
    assert "hardware[0].base_unit_cost" in result["missing_inputs"]


def test_committed_history_matches_fixed_seed():
    for series_id in SERIES:
        assert load_history(series_id) == generate_history(series_id)
        assert len(load_history(series_id)) == 36


def test_forecast_uses_only_months_before_as_of_date():
    feed, deal = load_feed("synthetic-costs-v1"), load_deal()
    result = forecast_costs(feed, deal, DEMO_DATE)
    for series in result["series"]:
        assert series["last_observed_month"] == "2026-09"
        assert series["forecast"][0]["month"] == "2026-10"
        assert len(series["forecast"]) == 6
    earlier = forecast_costs(feed, deal, date(2026, 6, 15))
    assert all(s["last_observed_month"] == "2026-05" for s in earlier["series"])


def test_forecast_is_tied_to_quote_dates_and_ledger_rates():
    result = forecast_costs(load_feed("synthetic-costs-v1"), load_deal(), DEMO_DATE)
    by_id = {s["series_id"]: s for s in result["series"]}
    hardware = by_id["supplier_unit_cost"]["quote_lines"][0]
    assert (hardware["date"], hardware["forecast_month"]) == ("2026-11-01", "2026-11")
    assert (hardware["ledger_rate_base"], hardware["ledger_rate_stress"]) == ("600.00", "660.00")
    freight = by_id["freight_per_shipment"]["quote_lines"][0]
    assert (freight["date"], freight["forecast_month"]) == ("2026-11-28", "2026-11")
    assert (freight["ledger_rate_base"], freight["ledger_rate_stress"]) == ("1000.00", "1200.00")
    assert "not calibrated probabilities" in result["scenario_note"]


def test_backtest_and_high_scenario():
    result = forecast_costs(load_feed("synthetic-costs-v1"), load_deal(), DEMO_DATE)
    for series in result["series"]:
        assert {b["method"] for b in series["backtest"]} == {"last_value", "seasonal_naive"}
        assert all(b["samples"] == 36 for b in series["backtest"])
        best = min(series["backtest"], key=lambda b: float(b["mae"]))
        assert series["selected_method"] == best["method"]
    hardware = {s["series_id"]: s for s in result["series"]}["supplier_unit_cost"]
    assert hardware["high_scenario_uplift_percent"] == "10.00"
    shocked = forecast_costs(load_feed("synthetic-costs-v2"), load_deal(), date(2026, 10, 26))
    assert {s["series_id"]: s for s in shocked["series"]}["supplier_unit_cost"]["high_scenario_uplift_percent"] \
        == "23.33"
