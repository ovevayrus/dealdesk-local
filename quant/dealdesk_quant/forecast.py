"""Monthly cost forecasts with chronological rolling origin evaluation.

Methods
  naive           last observed value (baseline)
  seasonal_naive  value from the same month last year (baseline, m = 12)
  damped_holt     additive damped trend exponential smoothing (the one candidate)

Evaluation: at every historical cutoff we fit only on earlier months and score
horizons 1..H. No random splits, no future data. Floats are fine here; values
are rounded to cents (as Decimal strings) only at the output boundary.
"""
import csv
import math
from pathlib import Path

from .errors import QuantError
from .util import add_months, check_month, file_hash, month_index

SEASON = 12
MIN_TRAIN = 18
METHODS = ("naive", "seasonal_naive", "damped_holt")
BASELINES = ("naive", "seasonal_naive")
PHI = 0.9
ALPHAS = [i / 10 for i in range(1, 10)]
BETAS = [0.01, 0.05, 0.1, 0.2, 0.3]


# ---------------------------------------------------------------- data

def load_series(path, series_id=None):
    path = Path(path)
    if not path.exists():
        raise QuantError("DATA_NOT_FOUND", f"history file not found: {path}", "history_path")
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if series_id:
        rows = [r for r in rows if r["series_id"] == series_id]
    if not rows:
        raise QuantError("DATA_NOT_FOUND", f"no rows for series {series_id!r} in {path}", "series_id")
    rows.sort(key=lambda r: r["month"])
    months = [check_month(r["month"], "month") for r in rows]
    for a, b in zip(months, months[1:]):
        if month_index(b) != month_index(a) + 1:
            raise QuantError("DATA_GAP", f"history has a gap between {a} and {b}", "month")
    return {
        "series_id": rows[0]["series_id"], "unit": rows[0]["unit"],
        "months": months, "values": [float(r["value"]) for r in rows],
        "synthetic": rows[0].get("synthetic", "").lower() == "true",
        "data_version": file_hash(path),
    }


# ---------------------------------------------------------------- methods

def f_naive(y, h):
    return [y[-1]] * h


def f_seasonal_naive(y, h, m=SEASON):
    if len(y) < m:
        raise ValueError("not enough history for seasonal naive")
    return [y[len(y) - m + (i % m)] for i in range(h)]


def _holt_run(y, a, b, phi):
    level, trend = y[0], y[1] - y[0]
    sse = 0.0
    for t in range(1, len(y)):
        pred = level + phi * trend
        err = y[t] - pred
        sse += err * err
        new_level = a * y[t] + (1 - a) * pred
        trend = b * (new_level - level) + (1 - b) * phi * trend
        level = new_level
    return sse, level, trend


def fit_damped_holt(y, phi=PHI):
    best = None
    for a in ALPHAS:
        for b in BETAS:
            sse, level, trend = _holt_run(y, a, b, phi)
            if best is None or sse < best[0]:
                best = (sse, a, b, level, trend)
    _, a, b, level, trend = best
    return {"alpha": a, "beta": b, "phi": phi, "level": level, "trend": trend}


def f_damped_holt(y, h, phi=PHI):
    p = fit_damped_holt(y, phi)
    out, damp = [], 0.0
    for k in range(1, h + 1):
        damp += phi ** k
        out.append(p["level"] + damp * p["trend"])
    return out


FORECASTERS = {"naive": f_naive, "seasonal_naive": f_seasonal_naive, "damped_holt": f_damped_holt}


# ---------------------------------------------------------------- evaluation

def rolling_origin(y, horizon, methods=METHODS, min_train=MIN_TRAIN):
    """Errors[method][h] = list of (actual, forecast) pairs, fit only on data before the cutoff."""
    errs = {m: {h: [] for h in range(1, horizon + 1)} for m in methods}
    for cutoff in range(min_train, len(y)):
        train = y[:cutoff]
        for m in methods:
            fc = FORECASTERS[m](train, horizon)
            for h in range(1, horizon + 1):
                idx = cutoff + h - 1
                if idx < len(y):
                    errs[m][h].append((y[idx], fc[h - 1]))
    return errs


def score(errs):
    table = {}
    for m, by_h in errs.items():
        rows = []
        tot_abs = tot_act = 0.0
        tot_n = 0
        for h, pairs in by_h.items():
            if not pairs:
                continue
            abs_e = [abs(a - f) for a, f in pairs]
            mae = sum(abs_e) / len(abs_e)
            wape = sum(abs_e) / sum(abs(a) for a, _ in pairs)
            rows.append({"horizon": h, "n": len(pairs), "mae": round(mae, 2),
                         "wape_pct": round(100 * wape, 2)})
            tot_abs += sum(abs_e)
            tot_act += sum(abs(a) for a, _ in pairs)
            tot_n += len(pairs)
        table[m] = {"by_horizon": rows,
                    "mean_mae": round(sum(r["mae"] for r in rows) / len(rows), 2),
                    "overall_wape_pct": round(100 * tot_abs / tot_act, 2),
                    "n_forecasts": tot_n}
    return table


def _quantile(xs, q):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, math.ceil(q * len(xs)) - 1))
    return xs[k]


# ---------------------------------------------------------------- tool

def forecast_costs(history_path, series_id, as_of, target_months=None, horizon=6,
                   band_quantile=0.9, max_staleness_months=1):
    """The forecast_costs tool.

    Returns base and low/high scenario paths for each month from the month after the
    last observation through `horizon`, plus the backtest that chose the method.
    """
    s = load_series(history_path, series_id)
    if not isinstance(horizon, int) or not 1 <= horizon <= 12:
        raise QuantError("INVALID_HORIZON", "horizon must be an integer from 1 to 12", "horizon")
    last = s["months"][-1]
    as_of_month = as_of[:7]
    check_month(as_of_month, "as_of")
    months_ahead = [add_months(last, k) for k in range(1, horizon + 1)]
    if target_months:
        for tm in target_months:
            check_month(tm, "target_months")
            if tm not in months_ahead:
                raise QuantError("OUT_OF_HORIZON",
                                 f"{tm} is outside the {horizon} month horizon after {last}",
                                 "target_months")

    y = s["values"]
    errs = rolling_origin(y, horizon)
    table = score(errs)
    selected = min(METHODS, key=lambda m: (table[m]["mean_mae"], METHODS.index(m)))
    best_baseline = min(BASELINES, key=lambda m: table[m]["mean_mae"])

    base = FORECASTERS[selected](y, horizon)
    path = []
    for h, (month, b) in enumerate(zip(months_ahead, base), start=1):
        ape = [abs(a - f) / abs(a) for a, f in errs[selected][h]]
        q = _quantile(ape, band_quantile)
        path.append({
            "month": month, "horizon": h,
            "base": f"{b:.2f}", "low": f"{b * (1 - q):.2f}", "high": f"{b * (1 + q):.2f}",
            "scenario_width_pct": round(100 * q, 2), "backtest_n": len(ape),
            "used_by_quote": (target_months is None) or (month in target_months),
        })

    staleness = month_index(as_of_month) - month_index(last) - 1
    flags = []
    if staleness > max_staleness_months:
        flags.append({"code": "STALE_HISTORY", "severity": "review",
                      "message": f"last observation {last} is {staleness} months behind as_of {as_of}"})
    out = {
        "series_id": s["series_id"], "unit": s["unit"], "as_of": as_of,
        "last_observation": last, "history_months": len(y),
        "synthetic_data": s["synthetic"], "data_version": s["data_version"],
        "horizon": horizon, "method": selected,
        "method_params": fit_damped_holt(y) if selected == "damped_holt" else None,
        "best_baseline": best_baseline,
        "candidate_beats_best_baseline": table["damped_holt"]["mean_mae"] < table[best_baseline]["mean_mae"],
        "path": path,
        "scenario_definition": (
            f"low/high = base x (1 -/+ q), q = {int(band_quantile * 100)}th percentile of absolute "
            "percentage error for the selected method at that horizon in the rolling backtest. "
            "These are scenarios, not calibrated prediction intervals."),
        "backtest": {"min_train_months": MIN_TRAIN, "cutoffs": len(y) - MIN_TRAIN,
                     "selection_rule": "lowest mean MAE across horizons 1..H; ties go to the simpler method",
                     "scores": table},
        "flags": flags,
        "status": "pending_review" if flags else "ok",
    }
    if out["method_params"]:
        out["method_params"] = {k: round(v, 4) for k, v in out["method_params"].items()}
    return out


def feed_from_forecasts(forecasts, base_feed, version, as_of, stress_key="high"):
    """Build a cost feed whose hardware/freight months come from forecasts (base and high).

    Used when no supplier quote covers a month. Other series are copied from base_feed.
    """
    import copy
    feed = copy.deepcopy(base_feed)
    feed["version"], feed["as_of"] = version, as_of
    for fc in forecasts:
        feed["series"][fc["series_id"]] = {
            "unit": fc["unit"],
            "source": f"forecast:{fc['method']} data {fc['data_version']} as_of {fc['as_of']}",
            "months": {p["month"]: {"base": p["base"], "stress": p[stress_key]} for p in fc["path"]},
        }
    return feed
