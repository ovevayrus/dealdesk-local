import copy
import unittest
from pathlib import Path

from dealdesk_quant.errors import QuantError
from dealdesk_quant.forecast import (FORECASTERS, feed_from_forecasts, forecast_costs, load_series,
                                     rolling_origin)
from dealdesk_quant.pricing import price_deal
from dealdesk_quant.repricing import review_open_quotes, verify_quote_hash
from dealdesk_quant.util import load_json

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures"
HW = ("hardware_unit:EDGE-100", ROOT / "data" / "hardware_unit_cost.csv")
FR = ("freight_shipment:LANE-OAK-PHX", ROOT / "data" / "freight_lane_cost.csv")
POLICY = load_json(FIX / "policy.json")
PB = load_json(FIX / "price_book.json")
FEED1 = load_json(FIX / "cost_feed_v1.json")
FEED2 = load_json(FIX / "feed_updates" / "cost_feed_v2.json")
QUOTES = load_json(FIX / "open_quotes.json")["quotes"]


class Forecasts(unittest.TestCase):

    def test_no_future_leakage(self):
        y = load_series(HW[1], HW[0])["values"]
        cutoff = 24
        before = rolling_origin(y, 3, min_train=cutoff)
        y2 = y[:cutoff] + [v * 10 for v in y[cutoff:]]  # wreck the future
        after = rolling_origin(y2, 3, min_train=cutoff)
        for m in FORECASTERS:
            self.assertAlmostEqual(before[m][1][0][1], after[m][1][0][1])  # same first forecast

    def test_backtest_counts(self):
        r = forecast_costs(HW[1], HW[0], "2026-10-01", ["2026-11", "2026-12"])
        rows = r["backtest"]["scores"]["naive"]["by_horizon"]
        self.assertEqual([x["n"] for x in rows], [18, 17, 16, 15, 14, 13])
        self.assertEqual(r["history_months"], 36)
        self.assertTrue(r["synthetic_data"])
        self.assertIn(r["method"], ("naive", "seasonal_naive", "damped_holt"))

    def test_scenario_ordering_and_targets(self):
        for sid, path in (HW, FR):
            r = forecast_costs(path, sid, "2026-10-01", ["2026-11", "2026-12"])
            for p in r["path"]:
                self.assertLessEqual(float(p["low"]), float(p["base"]))
                self.assertLessEqual(float(p["base"]), float(p["high"]))
            self.assertEqual([p["month"] for p in r["path"] if p["used_by_quote"]],
                             ["2026-11", "2026-12"])

    def test_out_of_horizon(self):
        with self.assertRaises(QuantError):
            forecast_costs(HW[1], HW[0], "2026-10-01", ["2027-09"])

    def test_stale_history_flag(self):
        r = forecast_costs(HW[1], HW[0], "2027-01-15")
        self.assertEqual(r["status"], "pending_review")

    def test_forecast_feed_prices_a_deal(self):
        fcs = [forecast_costs(p, s, "2026-10-01") for s, p in (HW, FR)]
        feed = feed_from_forecasts(fcs, FEED1, "fc-1", "2026-10-01")
        r = price_deal(load_json(FIX / "deal_demo.json"), feed, POLICY, PB, "rep")
        self.assertTrue(r["ledger"]["lines"][0]["source"].startswith("forecast:"))
        self.assertEqual(r["feasibility"]["status"], "feasible")


class Watcher(unittest.TestCase):

    def test_shock_flags_the_right_quotes(self):
        r = review_open_quotes(QUOTES, FEED2, POLICY, PB)
        sev = {e["quote_id"]: e["severity"] for e in r["events"]}
        self.assertEqual(sev, {"Q-1001": "breach", "Q-1002": "info", "Q-1003": "info",
                               "Q-1005": "breach"})
        self.assertEqual(r["unaffected_quotes"], ["Q-1004"])
        q1 = next(e for e in r["events"] if e["quote_id"] == "Q-1001")
        self.assertEqual(q1["previous"]["stress_margin_pct"], "28.24")
        self.assertEqual(q1["new"]["stress_margin_pct"], "22.35")
        self.assertEqual(q1["new"]["economic_floor"], "140800.00")
        self.assertTrue(q1["requires_new_version"] and q1["original_offer_preserved"])
        opts = {o["option"]: o for o in q1["recommended_responses"]}
        self.assertEqual(opts["reprice_to_new_floor"]["price"], "140800.00")
        self.assertEqual(opts["reprice_to_new_floor"]["discount_pct"], "12.00")
        self.assertEqual(opts["hardware_cost_adjustment_clause"]["max_hardware_stress_per_unit_at_this_price"],
                         "704.00")

    def test_unchanged_feed_emits_nothing(self):
        r = review_open_quotes(QUOTES, FEED1, POLICY, PB)
        self.assertEqual(r["events"], [])

    def test_dedup_key_stable(self):
        a = review_open_quotes(QUOTES, FEED2, POLICY, PB)
        b = review_open_quotes(QUOTES, copy.deepcopy(FEED2), POLICY, PB)
        self.assertEqual([e["dedup_key"] for e in a["events"]], [e["dedup_key"] for e in b["events"]])

    def test_original_quotes_untouched(self):
        before = copy.deepcopy(QUOTES)
        review_open_quotes(QUOTES, FEED2, POLICY, PB)
        self.assertEqual(before, QUOTES)

    def test_tampered_quote_rejected(self):
        q = copy.deepcopy(QUOTES[0])
        self.assertTrue(verify_quote_hash(q))
        q["price"] = "120000.00"
        self.assertFalse(verify_quote_hash(q))
        with self.assertRaises(QuantError):
            review_open_quotes([q], FEED2, POLICY, PB)

    def test_approval_bound_to_hash(self):
        q = QUOTES[0]
        self.assertEqual(q["approval"]["quote_hash"], q["quote_hash"])


if __name__ == "__main__":
    unittest.main()
