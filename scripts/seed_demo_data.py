#!/usr/bin/env python3
"""Regenerate the synthetic forecast histories (fixed seed) and check the demo data.

Usage:
    python scripts/seed_demo_data.py          # write data/synthetic/forecast/*.csv
    python scripts/seed_demo_data.py --check  # verify committed CSVs match the seed
"""

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealdesk.documents import load_corpus  # noqa: E402
from dealdesk.forecast import FORECAST_DIR, SERIES, write_history  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare committed CSVs with a fresh generation")
    args = parser.parse_args()

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            for series_id in SERIES:
                fresh = write_history(series_id, Path(tmp)).read_text(encoding="utf-8")
                committed = (FORECAST_DIR / f"{series_id}.csv").read_text(encoding="utf-8")
                if fresh != committed:
                    print(f"MISMATCH {series_id}: rerun without --check")
                    return 1
                print(f"OK {series_id}")
    else:
        for series_id in SERIES:
            print(f"wrote {write_history(series_id).relative_to(FORECAST_DIR.parents[2])}")

    corpus = load_corpus()
    print(f"{len({p.doc_id for p in corpus})} documents, {len(corpus)} searchable passages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
