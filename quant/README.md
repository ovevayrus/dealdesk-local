# DealDesk Local: quant module (Khushi)

Quantitative pricing and forecasting for DealDesk Local. One small Python package, standard library only (matplotlib is used just for the report chart). It owns every number in a quote. The LLM never produces an authoritative price.

**All data here is SYNTHETIC.** The seller, accounts, supplier, carrier, prices, and policy are demo assumptions.

## Run it

```bash
python3 -m unittest discover -s tests -v       # 29 tests, includes the 8 hand priced cases
python3 -m dealdesk_quant.report               # rewrites reports/ (backtest, chart, cost shock)
python3 -m dealdesk_quant price fixtures/deal_demo.json --actor-role rep
python3 -m dealdesk_quant price fixtures/deal_demo.json --actor-role rep --feed fixtures/feed_updates/cost_feed_v2.json
python3 -m dealdesk_quant review --feed fixtures/feed_updates/cost_feed_v2.json
python3 -m dealdesk_quant forecast --series hardware_unit:EDGE-100 --history data/hardware_unit_cost.csv --as-of 2026-10-01 --targets 2026-11,2026-12
python3 -m dealdesk_quant sensitivity fixtures/deal_demo.json --price 136000.00 --hardware -10,0,10,20 --freight 0,20
python3 -m dealdesk_quant generate-data         # regenerates data/ from the fixed seed
```

Python 3.10 or newer. No installs needed for pricing, forecasting, or tests.

## Demo numbers (all verified by tests)

| | Feed v1 | Feed v2 (supplier notice) |
|---|---:|---:|
| Base cost | $90,000 | $90,000 |
| Stress cost | $97,600 | $105,600 |
| Economic floor at 25% stress margin | $130,133.34 | $140,800.00 |
| Standard offer, rep 10% | $144,000 | $144,000 |
| $136,000 concession (15%) stress margin | 28.24%, needs director | 22.35%, blocked below floor |

Break even for the $136,000 quote: hardware stress cost of $704 per unit. Feed v2 sets $740.

The watcher run over five open quotes flags Q-1001 and Q-1005 as breaches, Q-1002 and Q-1003 as info, and leaves Q-1004 alone. An unchanged feed produces zero events. Each breach comes with three recomputed options: reprice to the new floor, phase the first shipment, or keep the price with a cost adjustment clause.

## Layout

```
dealdesk_quant/
  money.py         Decimal helpers; floats are rejected for money
  pricing.py       validate_deal, build_ledger, floors, evaluate_offer, price_deal, sensitivity
  forecast.py      naive, seasonal naive, damped Holt; rolling origin backtest; forecast_costs
  repricing.py     make_quote_version (hashed), appraise_quote, review_open_quotes
  data_gen.py      seeded synthetic history (seed 20261025)
  build_fixtures.py  rebuilds fixtures/open_quotes.json
  report.py        writes reports/
  __main__.py      CLI, one JSON envelope per call
data/              36 months per series plus manifest.json (seed, data versions)
fixtures/          price_book, policy, cost_feed_v1, feed_updates/cost_feed_v2, deal_demo, open_quotes
reports/           forecast_backtest.md, forecast_chart.png, cost_shock.md, JSON outputs
tests/             test_pricing.py (8 hand priced cases + guards), test_forecast_and_watch.py
```

## Contracts

Every CLI call prints one envelope. Exit code 0 on success, 2 on a known error.

```json
{"ok": true,  "tool": "price_deal", "run_id": "uuid", "result": {}}
{"ok": false, "tool": "price_deal", "run_id": "uuid", "error": {"code": "INVALID_CURRENCY", "message": "...", "field": "currency"}}
```

All money and percentages are strings (`"136000.00"`, `"28.24"`). Render them directly; never reformat through floats.

### price_deal

Input: a `DealRequest` (see `fixtures/deal_demo.json`) plus `actor_role` from the trusted session. The role must never come from the model.

Output keys: `inputs` (price book, policy, feed versions and hashes), `schedule`, `ledger` (dated lines with unit costs, source, feed version; totals per category; `base_cost`, `stress_cost`, `reserve`), `list_revenue`, `floors` (`economic_floor` and per role `authorization_floor`, `lowest_authorized_offer`, `range`), `feasibility`, `packages` (standard, negotiated, alternative), `sensitivity`, `flags`, `status`, `assumptions`, `exclusions`, `evidence_refs`.

Each package has `price`, `discount_pct`, `upfront`, `recurring_total`, `recurring_monthly`, `base_margin_pct`, `stress_margin_pct`, `required_approval` (`rep`, `director`, `finance_exception`), `policy_status`, `within_actor_authority`, `reasons`.

`policy_status` values: `compliant`, `requires_director_approval`, `blocked_below_floor`, `blocked_discount_exceeds_authority`, `invalid_above_list`.

`status` is `pending_review` when any flag is `review` or `block`. Flags: `NONSTANDARD_TERM`, `NONSTANDARD_PAYMENT_TERMS`, `STALE_COST_FEED`, `CAPACITY_SHORTFALL`, `INFEASIBLE_UNDER_CURRENT_TERMS`.

Hard error codes: `MISSING_INPUT`, `INVALID_CURRENCY`, `UNSUPPORTED_SKU`, `UNSUPPORTED_DESTINATION`, `INVALID_QUANTITY`, `SCHEDULE_MISMATCH`, `SHIPMENT_TOO_LARGE`, `INFEASIBLE_SCHEDULE`, `INVALID_MONTH`, `INVALID_DATE`, `INVALID_PRICE`, `UNKNOWN_ROLE`, `COST_INPUT_MISSING`.

### forecast_costs

Input: series id, history CSV, as of date, optional target months, horizon (1 to 12). Output: `method`, `best_baseline`, `candidate_beats_best_baseline`, `path` (month, base, low, high, `used_by_quote`), `backtest.scores` (MAE and WAPE by horizon with counts), `data_version`, `last_observation`, `flags` (`STALE_HISTORY`).

### watch_quotes repricing (`review` command)

Input: open quotes file and the new feed. Output: `events` (one per affected quote), `unaffected_quotes`, `counts`. Each event has `severity` (`breach` or `info`), `previous` and `new` appraisal, `changed_lines`, `requires_new_version`, `original_offer_preserved: true`, `dedup_key` (quote id + version + quote hash + feed hash), `recommended_responses`, and a plain `summary` for the viewer. The function never edits a quote.

### QuoteVersion

`make_quote_version` freezes the deal, price, feed/policy/price book versions, and calculated fields, then hashes them into `quote_hash`. An approval should carry that hash; `verify_quote_hash` rejects any altered quote.

## Handoffs

**Suhas.** Wrap the four CLI commands (or import the functions) as agent tools. Pass `actor_role` from the session. For the watcher job: keep a cursor of the last processed feed hash, call `review_open_quotes` when the feed file changes, and store events by `dedup_key` so reruns do not duplicate. Notifications should use the fixed message only; the event summary is for the local viewer.

**Luis.** The viewer can bind every number to a field in `price_deal` output. The Economics panel sliders map to the `sensitivity` command. Customer draft may use `price`, `upfront`, `recurring_monthly`, `discount_pct`, scope, and validity only. Never `ledger`, margins, floors, or sources.

**Jai.** The expected values for the 8 cases are written by hand in the comments of `tests/test_pricing.py`. Please check them independently before we report pass counts. Policy values live in `fixtures/policy.json` (version `policy-v1`); change them there and rerun the tests.

**Michael.** Cost sources named in the feed (`SUP-ALTA-2026-09`, `CARRIER-WEST-2026`, `supplier_notice:SUP-ALTA-2026-10-24`) should match the synthetic documents you write, so citations line up.

## Methods and honest limits

* Hardware is costed in the procurement month, freight per shipment month, installation per hour, service per active month. Stress is one named joint scenario with every line at its stress value, so the reserve is never added twice.
* Margin is gross margin on revenue, not markup. The floor is rounded up to the cent and never clamped down.
* Forecasting uses chronological rolling origin evaluation from month 18 with horizons 1 to 6. On this data the baselines win: naive for hardware, seasonal naive for freight. The damped Holt candidate lost and is reported anyway.
* Low and high are scenarios built from backtest error quantiles. They are not calibrated prediction intervals.
* Demo pricing reads supplier and carrier quoted costs. The forecast is a cross check and fills months no contract covers (`feed_from_forecasts`).
* Excluded: taxes, FX, financing, returns, working capital. Nonstandard terms are flagged for review, not priced.
* A higher floor says nothing about whether a customer will accept a higher price. These are policy compliant, defensible offers, not optimal prices.
