from datetime import datetime, timedelta, timezone

from src.freshness import is_fresh


def test_recent_timestamp_is_fresh():
    now = datetime.now(timezone.utc)
    timestamp = now - timedelta(seconds=10)

    assert is_fresh(timestamp, 120, now=now)


def test_old_timestamp_is_stale():
    now = datetime.now(timezone.utc)
    timestamp = now - timedelta(seconds=121)

    assert not is_fresh(timestamp, 120, now=now)


def test_missing_timestamp_is_stale():
    assert not is_fresh(None, 120)