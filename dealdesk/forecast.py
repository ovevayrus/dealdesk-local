"""Synthetic monthly supply/freight histories and simple baseline forecasts.

Histories are generated from a fixed seed with integer-cent arithmetic, so they
reproduce exactly on any platform. Forecasts use last-value and seasonal-naive
baselines, scored by a chronological rolling-origin backtest. Base/high values
are scenarios, not calibrated probabilities.
"""

from __future__ import annotations

import csv
import random
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Callable

from .config import SYNTHETIC_DIR
from .costs import select_rate

FORECAST_DIR = SYNTHETIC_DIR / "forecast"
SEED = 20261025
HISTORY_START = (2023, 10)
HISTORY_MONTHS = 36  # 2023-10 through 2026-09
SEASON = 12
BACKTEST_HORIZONS = (1, 2, 3)
BACKTEST_ORIGINS = 12
CENT = Decimal("0.01")

SERIES: dict[str, dict[str, Any]] = {
    "supplier_unit_cost": {
        "label": "CR-200 supplier unit cost",
        "unit": "USD/unit",
        "category": "hardware",
        "match": "CR-200",
        "date_field": "procurement_date",
        "start_cents": 55200,
        "drift_cents": 140,
        "noise_cents": 700,
        "seasonal_cents": {},
    },
    "freight_per_shipment": {
        "label": "Freight per shipment, lane RNO-CMH",
        "unit": "USD/shipment",
        "category": "freight",
        "match": "RNO-CMH",
        "date_field": "shipment_date",
        "start_cents": 91000,
        "drift_cents": 180,
        "noise_cents": 1800,
        # Synthetic Q4 peak-season pattern by calendar month.
        "seasonal_cents": {1: -3500, 2: -4500, 3: -2500, 4: -1000, 5: 0, 6: 500,
                           7: 1000, 8: 1500, 9: 2500, 10: 4500, 11: 6500, 12: 5500},
    },
}


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def add_months(year: int, month: int, count: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + count
    return index // 12, index % 12 + 1


def generate_history(series_id: str, seed: int = SEED) -> list[tuple[str, Decimal]]:
    spec = SERIES[series_id]
    rng = random.Random(seed + sorted(SERIES).index(series_id))
    level = spec["start_cents"]
    rows = []
    for offset in range(HISTORY_MONTHS):
        year, month = add_months(*HISTORY_START, offset)
        level += spec["drift_cents"] + rng.randint(-spec["noise_cents"], spec["noise_cents"]) // 3
        value = level + spec["seasonal_cents"].get(month, 0) + rng.randint(-spec["noise_cents"], spec["noise_cents"])
        rows.append((month_key(year, month), Decimal(value) / 100))
    return rows


def history_path(series_id: str) -> Path:
    return FORECAST_DIR / f"{series_id}.csv"


def write_history(series_id: str, directory: Path = FORECAST_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{series_id}.csv"
    spec = SERIES[series_id]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["month", "value", "unit", "series_id", "synthetic"])
        for month, value in generate_history(series_id):
            writer.writerow([month, format(value, ".2f"), spec["unit"], series_id, "true"])
    return path


def load_history(series_id: str) -> list[tuple[str, Decimal]]:
    with history_path(series_id).open(encoding="utf-8", newline="") as handle:
        return [(row["month"], Decimal(row["value"])) for row in csv.DictReader(handle)]


def last_value(values: list[Decimal], horizon: int) -> Decimal:
    return values[-1]


def seasonal_naive(values: list[Decimal], horizon: int) -> Decimal:
    """Value from the same calendar month one season earlier."""
    return values[len(values) - SEASON + (horizon - 1) % SEASON]


METHODS: dict[str, Callable[[list[Decimal], int], Decimal]] = {
    "last_value": last_value,
    "seasonal_naive": seasonal_naive,
}


def backtest(values: list[Decimal], method: str) -> dict[str, Any]:
    """Rolling-origin evaluation: each origin forecasts only from earlier observations."""
    forecaster = METHODS[method]
    errors: list[Decimal] = []
    actuals: list[Decimal] = []
    last_origin = len(values) - max(BACKTEST_HORIZONS)
    for origin in range(last_origin - BACKTEST_ORIGINS + 1, last_origin + 1):
        train = values[:origin]
        for horizon in BACKTEST_HORIZONS:
            actual = values[origin + horizon - 1]
            errors.append(abs(forecaster(train, horizon) - actual))
            actuals.append(abs(actual))
    mae = sum(errors, Decimal(0)) / len(errors)
    wape = sum(errors, Decimal(0)) / sum(actuals, Decimal(0)) * 100
    return {
        "method": method,
        "mae": format(mae.quantize(CENT, rounding=ROUND_HALF_UP), "f"),
        "wape_percent": format(wape.quantize(CENT, rounding=ROUND_HALF_UP), "f"),
        "samples": len(errors),
        "horizons": list(BACKTEST_HORIZONS),
        "origins": BACKTEST_ORIGINS,
    }


def _money(value: Decimal) -> str:
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), "f")


def forecast_costs(feed: dict[str, Any], deal: dict[str, Any], as_of: date, horizon: int = 6) -> dict[str, Any]:
    """Forecast each series from complete months before ``as_of`` and tie it to the deal's dates."""
    if type(horizon) is not int or not 1 <= horizon <= 24:
        raise ValueError("horizon must be an integer between 1 and 24 months.")
    as_of_month = month_key(as_of.year, as_of.month)
    series_out = []
    for series_id, spec in SERIES.items():
        history = [(month, value) for month, value in load_history(series_id) if month < as_of_month]
        months = [month for month, _ in history]
        values = [value for _, value in history]
        scores = {name: backtest(values, name) for name in METHODS}
        selected = min(scores, key=lambda name: (Decimal(scores[name]["mae"]), name != "last_value"))
        last_year, last_month = (int(part) for part in months[-1].split("-"))

        # High scenario applies the active feed's named stress uplift for this category.
        current_rate = select_rate(feed, spec["category"], spec["match"], as_of)
        uplift = Decimal(current_rate["stress"]) / Decimal(current_rate["base"]) if current_rate else Decimal(1)
        path = []
        for step in range(1, horizon + 1):
            year, month = add_months(last_year, last_month, step)
            base = METHODS[selected](values, step)
            path.append({
                "month": month_key(year, month),
                "horizon": step,
                "base": _money(base),
                "high_scenario": _money(base * uplift),
                "comparison": {name: _money(fn(values, step)) for name, fn in METHODS.items()},
            })

        quote_lines = []
        lines = deal.get(spec["category"]) or []
        for line in [lines] if isinstance(lines, dict) else lines:
            line_date = date.fromisoformat(line[spec["date_field"]])
            target = month_key(line_date.year, line_date.month)
            point = next((p for p in path if p["month"] == target), None)
            rate = select_rate(feed, spec["category"], spec["match"], line_date)
            quote_lines.append({
                "date_field": spec["date_field"],
                "date": line_date.isoformat(),
                "forecast_month": target,
                "forecast_base": point["base"] if point else None,
                "forecast_high_scenario": point["high_scenario"] if point else None,
                "ledger_rate_base": rate["base"] if rate else None,
                "ledger_rate_stress": rate["stress"] if rate else None,
                "ledger_rate_source": rate["source"] if rate else None,
                "ledger_rate_effective_from": rate["effective_from"] if rate else None,
            })

        series_out.append({
            "series_id": series_id,
            "label": spec["label"],
            "unit": spec["unit"],
            "history": [{"month": m, "value": _money(v)} for m, v in history[-12:]],
            "history_months_used": len(history),
            "last_observed_month": months[-1],
            "selected_method": selected,
            "backtest": list(scores.values()),
            "high_scenario_uplift_percent": _money((uplift - 1) * 100),
            "forecast": path,
            "quote_lines": quote_lines,
        })
    return {
        "synthetic": True,
        "as_of_date": as_of.isoformat(),
        "feed_version": feed["feed_version"],
        "stress_scenario": feed["stress_scenario"],
        "series": series_out,
        "scenario_note": ("Base and high values are scenarios: high applies the active feed's named stress "
                          "uplift. They are not calibrated probabilities or prediction intervals."),
        "service_note": ("Managed-service cost uses explicit base/high assumptions from the cost feed "
                         "(USD 20.00 / 21.00 per active unit per month), not a statistical forecast."),
    }
