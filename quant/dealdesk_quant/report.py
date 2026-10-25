"""Write the saved evidence: backtest table, forecast chart, demo quote, cost shock result."""
import json
from pathlib import Path

from .forecast import forecast_costs, load_series
from .pricing import price_deal
from .repricing import review_open_quotes
from .util import load_json

ROOT = Path(__file__).resolve().parent.parent
FIX, DATA, OUT = ROOT / "fixtures", ROOT / "data", ROOT / "reports"
AS_OF = "2026-10-01"
TARGETS = ["2026-11", "2026-12"]
SERIES = [("hardware_unit:EDGE-100", DATA / "hardware_unit_cost.csv", "Supplier cost per bundle unit"),
          ("freight_shipment:LANE-OAK-PHX", DATA / "freight_lane_cost.csv", "Freight cost per shipment, OAK to PHX")]
INK, MUTED, BLUE, BAND, ORANGE = "#1f2328", "#6b7280", "#2a78d6", "#cde2fb", "#eb6834"


def _chart(fcs, feed):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(9, 7.2))
    for ax, (sid, path, title), fc in zip(axes, SERIES, fcs):
        s = load_series(path, sid)
        hx = list(range(len(s["months"])))
        fx = [len(hx) - 1 + p["horizon"] for p in fc["path"]]
        ax.fill_between(fx, [float(p["low"]) for p in fc["path"]], [float(p["high"]) for p in fc["path"]],
                        color=BAND, linewidth=0, label="Low to high scenario")
        ax.plot(hx, s["values"], color=INK, linewidth=2, label="History (synthetic)")
        ax.plot([hx[-1]] + fx, [s["values"][-1]] + [float(p["base"]) for p in fc["path"]],
                color=BLUE, linewidth=2, linestyle="--", label=f"Base forecast ({fc['method']})")
        qx, qy = [], []
        for p, x in zip(fc["path"], fx):
            m = feed["series"][sid]["months"].get(p["month"])
            if m and p["used_by_quote"]:
                qx.append(x)
                qy.append(float(m["base"]))
        ax.scatter(qx, qy, s=60, color=ORANGE, zorder=5, edgecolor="white", linewidth=2,
                   label="Supplier/carrier quoted base, quote months")
        labels = s["months"] + [p["month"] for p in fc["path"]]
        ticks = list(range(0, len(labels), 6))
        ax.set_xticks(ticks, [labels[i] for i in ticks], fontsize=8, color=MUTED)
        ax.tick_params(axis="y", labelsize=8, colors=MUTED)
        ax.set_title(f"{title} ({fc['unit']})", loc="left", fontsize=11, color=INK)
        ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color("#d1d5db")
        ax.legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle(f"DealDesk cost forecasts as of {AS_OF}. SYNTHETIC DATA.", fontsize=10, color=MUTED,
                 x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "forecast_chart.png", dpi=150)
    plt.close(fig)


def _backtest_md(fcs, feed):
    L = ["# Forecast backtest", "",
         f"As of {AS_OF}. 36 months of seeded synthetic history (seed in data/manifest.json). "
         "Rolling origin: at each cutoff from month 18 onward, every method is fit only on earlier months "
         "and scored on horizons 1 to 6. No random splits.", "",
         "Results on synthetic data show the pipeline works. They say nothing about real supplier markets.", ""]
    for (sid, _, title), fc in zip(SERIES, fcs):
        sc = fc["backtest"]["scores"]
        L += [f"## {title}", "", f"Series `{sid}`, unit {fc['unit']}, data version `{fc['data_version']}`.", "",
              "| Method | Mean MAE | Overall WAPE | Forecasts scored |", "|---|---:|---:|---:|"]
        for m in ("naive", "seasonal_naive", "damped_holt"):
            mark = " (selected)" if m == fc["method"] else ""
            L.append(f"| {m}{mark} | {sc[m]['mean_mae']:.2f} | {sc[m]['overall_wape_pct']:.2f}% | "
                     f"{sc[m]['n_forecasts']} |")
        L += ["", "MAE by horizon (" + fc["unit"] + "):", "",
              "| Horizon | n | naive | seasonal_naive | damped_holt |", "|---:|---:|---:|---:|---:|"]
        for i, row in enumerate(sc["naive"]["by_horizon"]):
            L.append(f"| {row['horizon']} | {row['n']} | {row['mae']:.2f} | "
                     f"{sc['seasonal_naive']['by_horizon'][i]['mae']:.2f} | "
                     f"{sc['damped_holt']['by_horizon'][i]['mae']:.2f} |")
        verdict = ("The candidate beat the best baseline." if fc["candidate_beats_best_baseline"] else
                   f"The damped Holt candidate did not beat the best baseline, so `{fc['method']}` is used.")
        L += ["", verdict, "", "Forecast for the quote months, next to what the feed actually quotes:", "",
              "| Month | Forecast base | Low | High | Quoted base | Quoted stress |", "|---|---:|---:|---:|---:|---:|"]
        for p in fc["path"]:
            if p["used_by_quote"]:
                q = feed["series"][sid]["months"][p["month"]]
                L.append(f"| {p['month']} | {p['base']} | {p['low']} | {p['high']} | {q['base']} | {q['stress']} |")
        L += ["", f"Scenarios: {fc['scenario_definition']}", ""]
    L += ["## How pricing uses this", "",
          "The pricing engine reads a dated cost feed. For the demo months, hardware and freight come from a "
          "supplier quote and a carrier contract, because company terms beat a statistical estimate. The forecast "
          "is the cross check (quoted base sits within about 2% of the forecast for hardware) and fills any month "
          "no contract covers, via `feed_from_forecasts` (base = forecast base, stress = high scenario). "
          "The quoted stress values are wider than the forecast band because they come from contract caps, "
          "not from history.", ""]
    (OUT / "forecast_backtest.md").write_text("\n".join(L))


def _shock_md(demo1, demo2, review):
    n1 = next(p for p in demo1["packages"] if p["package"] == "negotiated")
    n2 = next(p for p in demo2["packages"] if p["package"] == "negotiated")
    L = ["# Cost shock result", "", "Simulated risk demonstration on synthetic data. Not a claim of realized savings.", "",
         "## Demo quote Q-1001 (100 units, $160,000 list)", "",
         "| | Feed v1 | Feed v2 |", "|---|---:|---:|",
         f"| Base cost | {demo1['ledger']['base_cost']} | {demo2['ledger']['base_cost']} |",
         f"| Stress cost | {demo1['ledger']['stress_cost']} | {demo2['ledger']['stress_cost']} |",
         f"| Economic floor (25% stress margin) | {demo1['floors']['economic_floor']} | {demo2['floors']['economic_floor']} |",
         f"| Standard offer (rep, 10%) | {demo1['packages'][0]['price']} | {demo2['packages'][0]['price']} |",
         f"| $136,000 concession stress margin | {n1['stress_margin_pct']}% | {n2['stress_margin_pct']}% |",
         f"| $136,000 concession status | {n1['policy_status']} | {n2['policy_status']} |", "",
         f"Break even: at $136,000 the quote stays within policy while hardware stress cost is at most "
         f"${demo1['sensitivity']['breakeven_hardware_stress_per_unit']} per unit. Feed v2 sets it to $740.", "",
         "## Watcher run over the five open quotes", "",
         f"Checked {review['counts']['checked']}: {review['counts']['breach']} breach, "
         f"{review['counts']['info']} info, {review['counts']['unaffected']} unaffected "
         f"({', '.join(review['unaffected_quotes'])}). Rerunning on an unchanged feed emits no events.", ""]
    for e in review["events"]:
        L += [f"### {e['quote_id']} ({e['severity']})", "", e["summary"], ""]
        for o in e["recommended_responses"]:
            if o["option"] == "reprice_to_new_floor":
                L.append(f"* Reprice to {o['price']} (+{o['price_change']}), discount {o['discount_pct']}%, "
                         f"needs {o['required_approval']} approval.")
            elif o["option"] == "phase_first_shipment":
                L.append(f"* Phase: commit {o['quantity']} units at {o['price']}, stress margin "
                         f"{o['stress_margin_pct']}%, within {o['required_approval']} authority.")
            elif o["option"] == "hardware_cost_adjustment_clause":
                L.append(f"* Keep {o['keep_price']} with a cost adjustment clause above "
                         f"{o['max_hardware_stress_per_unit_at_this_price']} per unit (finance and legal review).")
        if e["recommended_responses"]:
            L.append("")
    (OUT / "cost_shock.md").write_text("\n".join(L))


def main():
    OUT.mkdir(exist_ok=True)
    feed1 = load_json(FIX / "cost_feed_v1.json")
    feed2 = load_json(FIX / "feed_updates" / "cost_feed_v2.json")
    policy, pb = load_json(FIX / "policy.json"), load_json(FIX / "price_book.json")
    fcs = [forecast_costs(p, s, AS_OF, TARGETS) for s, p, _ in SERIES]
    demo = load_json(FIX / "deal_demo.json")
    d1 = price_deal(demo, feed1, policy, pb, "rep")
    d2 = price_deal(demo, feed2, policy, pb, "rep")
    review = review_open_quotes(load_json(FIX / "open_quotes.json")["quotes"], feed2, policy, pb)
    for name, obj in [("demo_quote_feed_v1.json", d1), ("demo_quote_feed_v2.json", d2),
                      ("review_events_feed_v2.json", review),
                      ("forecasts.json", {"as_of": AS_OF, "forecasts": fcs})]:
        (OUT / name).write_text(json.dumps(obj, indent=2) + "\n")
    _backtest_md(fcs, feed1)
    _shock_md(d1, d2, review)
    _chart(fcs, feed1)
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
