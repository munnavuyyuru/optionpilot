from __future__ import annotations

from datetime import datetime, timezone


def age_seconds(timestamp: datetime, now: datetime | None = None) -> float:
    if now is None:
        now = datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    return max(0.0, (now - timestamp).total_seconds())


def is_fresh(
    timestamp: datetime | None,
    max_age_seconds: int,
    now: datetime | None = None,
) -> bool:
    if timestamp is None:
        return False

    return age_seconds(timestamp, now) <= max_age_seconds