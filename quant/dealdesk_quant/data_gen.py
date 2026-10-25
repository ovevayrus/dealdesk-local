"""Generate clearly synthetic monthly cost history with a fixed seed.

Two series, 36 months each, ending at the month before the as-of date:
  hardware_unit:EDGE-100     supplier USD per bundle unit (upward trend, mild seasonality)
  freight_shipment:LANE-OAK-PHX   USD per shipment on one lane (Q4 peak season)
"""
import csv
import json
import math
import random
from pathlib import Path

from .util import add_months, file_hash

SEED = 20261025
FIRST_MONTH = "2023-10"
N_MONTHS = 36
AS_OF = "2026-10-01"

SERIES = {
    "hardware_unit:EDGE-100": {
        "file": "hardware_unit_cost.csv",
        "unit": "USD/unit",
        "level": 520.0, "trend": 2.2, "season_amp": 8.0, "season_peak_month": 2, "noise_sd": 6.0,
    },
    "freight_shipment:LANE-OAK-PHX": {
        "file": "freight_lane_cost.csv",
        "unit": "USD/shipment",
        "level": 880.0, "trend": 1.5, "season_amp": 70.0, "season_peak_month": 12, "noise_sd": 18.0,
    },
}


def _series_values(spec, rng):
    out = []
    for t in range(N_MONTHS):
        month = add_months(FIRST_MONTH, t)
        mo = int(month[5:])
        season = spec["season_amp"] * math.cos(2 * math.pi * (mo - spec["season_peak_month"]) / 12)
        value = spec["level"] + spec["trend"] * t + season + rng.gauss(0, spec["noise_sd"])
        out.append((month, round(value, 2)))
    return out


def generate(out_dir="data") -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    manifest = {
        "synthetic": True,
        "notice": "SYNTHETIC DEMO DATA. Not real supplier or freight prices.",
        "seed": SEED, "as_of": AS_OF, "first_month": FIRST_MONTH, "months": N_MONTHS,
        "series": {},
    }
    for series_id, spec in SERIES.items():
        rows = _series_values(spec, rng)
        path = out / spec["file"]
        with path.open("w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["series_id", "month", "value", "unit", "synthetic"])
            for month, value in rows:
                w.writerow([series_id, month, f"{value:.2f}", spec["unit"], "true"])
        manifest["series"][series_id] = {
            "file": spec["file"], "unit": spec["unit"],
            "last_month": rows[-1][0], "data_version": file_hash(path),
        }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
