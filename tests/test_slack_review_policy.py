import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations" / "slack"))
import slack_poster


@pytest.fixture
def review(monkeypatch, tmp_path):
    monkeypatch.setattr(slack_poster, "REVIEW_MAP_PATH", str(tmp_path / "reviews.json"))
    monkeypatch.setenv("DEALDESK_SLACK_REVIEWERS", "U-REVIEWER")
    monkeypatch.setenv("DEAL_ROOM_CHANNEL", "C-TEST")
    class Fake:
        def chat_postMessage(self, **kwargs): return {"channel": "C-TEST", "ts": "1.0"}
    monkeypatch.setattr(slack_poster, "_client", Fake())
    return slack_poster.post_deal_card({"deal_id": "SYN-TEST"})["review_id"]


def resolve(rid, user="U-REVIEWER", channel="C-TEST", ts="1.0"):
    return slack_poster.resolve_review(rid, user, channel, ts, "Review acknowledged")


def test_review_requires_known_user_channel_message_and_pending_state(review):
    assert not resolve("R-UNKNOWN")
    assert not resolve(review, user="U-OUTSIDER")
    assert not resolve(review, channel="C-OTHER")
    assert not resolve(review, ts="2.0")
    assert resolve(review)
    assert not resolve(review)
    assert not slack_poster.resolve_review(review, "U-REVIEWER", "C-TEST", "1.0", "Approved")


def test_review_denies_missing_reviewer_configuration(review, monkeypatch):
    monkeypatch.delenv("DEALDESK_SLACK_REVIEWERS")
    assert not resolve(review)


def test_duplicate_concurrent_callbacks_record_one_verdict(review):
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(lambda _: resolve(review), range(8))) == 1


def test_callback_import_does_not_connect_and_reject_does_not_update_slack(review):
    path = Path(slack_poster.__file__).with_name("app.py")
    spec = importlib.util.spec_from_file_location("review_app", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class Fake:
        def chat_update(self, **kwargs): raise AssertionError("No update permitted")
    body = {"actions": [{"value": review}], "user": {"id": "U-OUTSIDER"},
            "channel": {"id": "C-TEST"}, "message": {"ts": "1.0"}}
    assert not module._resolve(body, Fake(), "Review acknowledged")
