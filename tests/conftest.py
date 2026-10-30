import copy
import json
from datetime import date
from pathlib import Path

import pytest

from dealdesk.config import Settings

ROOT = Path(__file__).resolve().parents[1]
DEMO_DATE = date(2026, 10, 25)


def _load_cases():
    data = json.loads((ROOT / "tests" / "fixtures" / "pricing_cases.json").read_text(encoding="utf-8"))
    return {case["id"]: case for case in data["cases"]}


CASES = _load_cases()


@pytest.fixture
def case_inputs():
    """Return a deep copy of one reference case's inputs so tests never mutate the fixture."""
    return lambda case_id: copy.deepcopy(CASES[case_id]["inputs"])


@pytest.fixture
def settings(tmp_path):
    return Settings(state_dir=tmp_path / "runtime", watch_interval_seconds=0, demo_date="2026-10-25")


@pytest.fixture
def client(settings):
    from fastapi.testclient import TestClient

    from dealdesk.app import create_app

    with TestClient(create_app(settings), base_url="http://127.0.0.1") as test_client:
        yield test_client
