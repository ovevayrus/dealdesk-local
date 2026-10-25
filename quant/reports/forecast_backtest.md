# Forecast backtest

As of 2026-10-01. 36 months of seeded synthetic history (seed in data/manifest.json). Rolling origin: at each cutoff from month 18 onward, every method is fit only on earlier months and scored on horizons 1 to 6. No random splits.

Results on synthetic data show the pipeline works. They say nothing about real supplier markets.

## Supplier cost per bundle unit

Series `hardware_unit:EDGE-100`, unit USD/unit, data version `sha256:967b3859bf273b12`.

| Method | Mean MAE | Overall WAPE | Forecasts scored |
|---|---:|---:|---:|
| naive (selected) | 10.57 | 1.77% | 93 |
| seasonal_naive | 22.68 | 3.92% | 93 |
| damped_holt | 13.49 | 2.22% | 93 |

MAE by horizon (USD/unit):

| Horizon | n | naive | seasonal_naive | damped_holt |
|---:|---:|---:|---:|---:|
| 1 | 18 | 7.36 | 23.69 | 6.47 |
| 2 | 17 | 7.30 | 23.00 | 7.99 |
| 3 | 16 | 9.37 | 22.67 | 11.16 |
| 4 | 15 | 10.91 | 22.25 | 15.40 |
| 5 | 14 | 13.00 | 22.31 | 17.82 |
| 6 | 13 | 15.50 | 22.16 | 22.09 |

The damped Holt candidate did not beat the best baseline, so `naive` is used.

Forecast for the quote months, next to what the feed actually quotes:

| Month | Forecast base | Low | High | Quoted base | Quoted stress |
|---|---:|---:|---:|---:|---:|
| 2026-11 | 588.47 | 569.98 | 606.96 | 600.00 | 660.00 |
| 2026-12 | 588.47 | 567.53 | 609.41 | 600.00 | 660.00 |

Scenarios: low/high = base x (1 -/+ q), q = 90th percentile of absolute percentage error for the selected method at that horizon in the rolling backtest. These are scenarios, not calibrated prediction intervals.

## Freight cost per shipment, OAK to PHX

Series `freight_shipment:LANE-OAK-PHX`, unit USD/shipment, data version `sha256:f298c1dabc456a60`.

| Method | Mean MAE | Overall WAPE | Forecasts scored |
|---|---:|---:|---:|
| naive | 57.42 | 6.11% | 93 |
| seasonal_naive (selected) | 23.56 | 2.60% | 93 |
| damped_holt | 77.95 | 8.22% | 93 |

MAE by horizon (USD/shipment):

| Horizon | n | naive | seasonal_naive | damped_holt |
|---:|---:|---:|---:|---:|
| 1 | 18 | 25.18 | 23.89 | 28.36 |
| 2 | 17 | 44.18 | 24.22 | 51.63 |
| 3 | 16 | 56.99 | 24.62 | 73.99 |
| 4 | 15 | 65.75 | 23.86 | 92.37 |
| 5 | 14 | 74.50 | 22.05 | 105.76 |
| 6 | 13 | 77.93 | 22.70 | 115.60 |

The damped Holt candidate did not beat the best baseline, so `seasonal_naive` is used.

Forecast for the quote months, next to what the feed actually quotes:

| Month | Forecast base | Low | High | Quoted base | Quoted stress |
|---|---:|---:|---:|---:|---:|
| 2026-11 | 979.28 | 924.31 | 1034.25 | 1000.00 | 1200.00 |
| 2026-12 | 965.89 | 911.67 | 1020.11 | 1000.00 | 1200.00 |

Scenarios: low/high = base x (1 -/+ q), q = 90th percentile of absolute percentage error for the selected method at that horizon in the rolling backtest. These are scenarios, not calibrated prediction intervals.

## How pricing uses this

The pricing engine reads a dated cost feed. For the demo months, hardware and freight come from a supplier quote and a carrier contract, because company terms beat a statistical estimate. The forecast is the cross check (quoted base sits within about 2% of the forecast for hardware) and fills any month no contract covers, via `feed_from_forecasts` (base = forecast base, stress = high scenario). The quoted stress values are wider than the forecast band because they come from contract caps, not from history.
