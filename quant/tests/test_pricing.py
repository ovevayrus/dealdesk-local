"""Hand-priced acceptance cases. Expected numbers were worked out by hand from the
fixtures before running the engine; the arithmetic for each is in the comments so
Jai can check them independently."""
import copy
import unittest
from pathlib import Path

from dealdesk_quant.errors import QuantError
from dealdesk_quant.pricing import price_deal, sensitivity
from dealdesk_quant.util import load_json

FIX = Path(__file__).resolve().parent.parent / "fixtures"
DEMO = load_json(FIX / "deal_demo.json")
FEED1 = load_json(FIX / "cost_feed_v1.json")
FEED2 = load_json(FIX / "feed_updates" / "cost_feed_v2.json")
POLICY = load_json(FIX / "policy.json")
PB = load_json(FIX / "price_book.json")


def deal(**kw):
    d = copy.deepcopy(DEMO)
    for k, v in kw.items():
        if v is None:
            d.pop(k, None)
        else:
            d[k] = v
    return d


def run(d, feed=FEED1, role="rep"):
    return price_deal(d, feed, POLICY, PB, role)


def pkg(r, name):
    return next(p for p in r["packages"] if p["package"] == name)


class EightHandPricedCases(unittest.TestCase):

    def test_1_normal_deal(self):
        # costs: hw 100*600 + freight 2*1000 + install 50h*80 + service 100*20*12 = 90,000
        # stress: 100*660 + 2*1200 + 4,000 + 100*21*12 = 97,600
        # floor = ceil(97,600 / 0.75) = 130,133.34 ; list = 100,000 + 6,000 + 54,000 = 160,000
        r = run(deal(proposed_price=None))
        self.assertEqual(r["ledger"]["base_cost"], "90000.00")
        self.assertEqual(r["ledger"]["stress_cost"], "97600.00")
        self.assertEqual(r["ledger"]["reserve"], "7600.00")
        self.assertEqual(r["list_revenue"]["total"], "160000.00")
        self.assertEqual(r["floors"]["economic_floor"], "130133.34")
        std = pkg(r, "standard")
        self.assertEqual((std["price"], std["discount_pct"], std["stress_margin_pct"]),
                         ("144000.00", "10.00", "32.22"))
        self.assertEqual(std["policy_status"], "compliant")
        # no proposed price: negotiated = deepest director offer = max(128,000, 130,133.34)
        neg = pkg(r, "negotiated")
        self.assertEqual((neg["price"], neg["discount_pct"], neg["stress_margin_pct"]),
                         ("130133.34", "18.67", "25.00"))
        self.assertEqual(neg["required_approval"], "director")
        self.assertEqual(r["status"], "ready_for_review")

    def test_2_recurring_costs_nonstandard_term(self):
        # 24 month service: base 100*20*24 = 48,000 ; stress 100*21*24 = 50,400
        # base total 114,000 ; stress 122,800 ; floor ceil(122,800/0.75) = 163,733.34
        # list = 100,000 + 6,000 + 100*45*24 = 214,000 ; rep floor 192,600
        r = run(deal(service={"start_month": "2026-12", "term_months": 24}, proposed_price=None))
        self.assertEqual(r["ledger"]["totals"]["service"], {"base": "48000.00", "stress": "50400.00"})
        self.assertEqual(r["ledger"]["stress_cost"], "122800.00")
        self.assertEqual(r["floors"]["economic_floor"], "163733.34")
        self.assertEqual(pkg(r, "standard")["price"], "192600.00")
        self.assertEqual(len([l for l in r["ledger"]["lines"] if l["category"] == "service"]), 24)
        self.assertEqual(r["status"], "pending_review")
        self.assertIn("NONSTANDARD_TERM", [f["code"] for f in r["flags"]])

    def test_3_freight_units(self):
        # four shipments of 25: freight base 4*1000 = 4,000 ; stress 4*1200 = 4,800
        # stress total 66,000 + 4,800 + 4,000 + 25,200 = 100,000 ; floor 133,333.34
        ships = [{"month": "2026-11", "units": 25}, {"month": "2026-11", "units": 25},
                 {"month": "2026-12", "units": 25}, {"month": "2026-12", "units": 25}]
        r = run(deal(shipments=ships))
        self.assertEqual(r["ledger"]["totals"]["freight"], {"base": "4000.00", "stress": "4800.00"})
        self.assertEqual(r["ledger"]["base_cost"], "92000.00")
        self.assertEqual(r["ledger"]["stress_cost"], "100000.00")
        self.assertEqual(r["floors"]["economic_floor"], "133333.34")

    def test_4_concession_needs_director(self):
        # 136,000: discount 24,000/160,000 = 15% ; stress margin 38,400/136,000 = 28.24%
        # upfront 136,000 * 106/160 = 90,100 ; recurring 45,900 = 3,825/month
        r = run(deal())
        neg = pkg(r, "negotiated")
        self.assertEqual(neg["price"], "136000.00")
        self.assertEqual(neg["discount_pct"], "15.00")
        self.assertEqual(neg["stress_margin_pct"], "28.24")
        self.assertEqual(neg["base_margin_pct"], "33.82")
        self.assertEqual((neg["upfront"], neg["recurring_total"], neg["recurring_monthly"]),
                         ("90100.00", "45900.00", "3825.00"))
        self.assertEqual(neg["policy_status"], "requires_director_approval")
        self.assertFalse(neg["within_actor_authority"])
        # the same price is within a director's own authority
        self.assertTrue(pkg(run(deal(), role="director"), "negotiated")["within_actor_authority"])

    def test_5_floor_above_list(self):
        # hardware stress 1,100/unit: stress = 110,000 + 2,400 + 4,000 + 25,200 = 141,600
        # floor = 188,800 > list 160,000 -> infeasible, never clamped down
        feed = copy.deepcopy(FEED1)
        for m in ("2026-11", "2026-12"):
            feed["series"]["hardware_unit:EDGE-100"]["months"][m]["stress"] = "1100.00"
        r = run(deal(), feed=feed)
        self.assertEqual(r["floors"]["economic_floor"], "188800.00")
        self.assertEqual(r["feasibility"]["status"], "infeasible_under_current_terms")
        self.assertEqual([p["package"] for p in r["packages"]], [])
        self.assertFalse(r["floors"]["authorization"]["director"]["feasible"])
        self.assertEqual(r["status"], "pending_review")

    def test_6_missing_input(self):
        with self.assertRaises(QuantError) as cm:
            run(deal(shipments=None))
        self.assertEqual((cm.exception.code, cm.exception.field), ("MISSING_INPUT", "shipments"))

    def test_7_high_cost_shock(self):
        # feed v2 hardware stress 740: stress = 74,000 + 2,400 + 4,000 + 25,200 = 105,600
        # margin at 136,000 = 30,400/136,000 = 22.35% ; new floor 105,600/0.75 = 140,800
        r = run(deal(), feed=FEED2)
        self.assertEqual(r["ledger"]["stress_cost"], "105600.00")
        self.assertEqual(r["floors"]["economic_floor"], "140800.00")
        neg = pkg(r, "negotiated")
        self.assertEqual(neg["stress_margin_pct"], "22.35")
        self.assertEqual(neg["policy_status"], "blocked_below_floor")
        self.assertEqual(neg["required_approval"], "finance_exception")
        self.assertEqual(pkg(r, "standard")["stress_margin_pct"], "26.67")

    def test_8_invalid_currency(self):
        with self.assertRaises(QuantError) as cm:
            run(deal(currency="EUR"))
        self.assertEqual(cm.exception.code, "INVALID_CURRENCY")


class MoreGuards(unittest.TestCase):

    def test_unsupported_sku(self):
        with self.assertRaises(QuantError) as cm:
            run(deal(bundle="EDGE-999"))
        self.assertEqual(cm.exception.code, "UNSUPPORTED_SKU")

    def test_float_price_rejected(self):
        with self.assertRaises(QuantError):
            run(deal(proposed_price=136000.5))

    def test_ship_before_procure(self):
        with self.assertRaises(QuantError) as cm:
            run(deal(procurement=[{"month": "2026-12", "units": 100}]))
        self.assertEqual(cm.exception.code, "INFEASIBLE_SCHEDULE")

    def test_capacity_shortfall_proposes_phase(self):
        ships = [{"month": "2026-11", "units": 50}] * 3 + [{"month": "2026-12", "units": 50}] * 3
        r = run(deal(quantity=300, procurement=[{"month": "2026-11", "units": 300}], shipments=ships))
        self.assertEqual(r["feasibility"]["status"], "infeasible_capacity")
        self.assertEqual([p["package"] for p in r["packages"]], ["alternative"])
        self.assertIn("CAPACITY_SHORTFALL", [f["code"] for f in r["flags"]])

    def test_stale_feed(self):
        r = run(deal(quote_date="2026-12-20", quote_expiry="2027-01-15"))
        self.assertIn("STALE_COST_FEED", [f["code"] for f in r["flags"]])
        self.assertEqual(r["status"], "pending_review")

    def test_unknown_role(self):
        with self.assertRaises(QuantError):
            run(deal(), role="intern")

    def test_alternative_is_recosted(self):
        # 50 units: base 30,000 + 1,000 + 2,000 + 12,000 = 45,000 ; stress 48,800 ; list 80,000
        alt = pkg(run(deal()), "alternative")
        self.assertEqual((alt["quantity"], alt["price"], alt["base_cost"], alt["stress_cost"]),
                         (50, "72000.00", "45000.00", "48800.00"))

    def test_sensitivity_breakeven(self):
        # at 136,000: allowed stress cost 102,000 ; non-hardware stress 31,600 -> 70,400 / 100 = 704
        s = sensitivity(deal(), FEED1, POLICY, PB, "136000.00", [0, 10, 20], [0])
        self.assertEqual(s["breakeven_hardware_stress_per_unit"], "704.00")
        cells = s["grid"][0]["cells"]
        self.assertEqual([c["meets_policy"] for c in cells], [True, False, False])

    def test_no_float_anywhere_in_money_output(self):
        r = run(deal())

        def walk(x):
            if isinstance(x, float):
                self.fail(f"float in output: {x}")
            if isinstance(x, dict):
                for v in x.values():
                    walk(v)
            if isinstance(x, list):
                for v in x:
                    walk(v)
        walk(r)


if __name__ == "__main__":
    unittest.main()
