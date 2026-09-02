from datetime import datetime, timedelta, timezone

from src.market_data import PriceBar
from src.signals import calculate_market_signal


def _bars(values):
    start = datetime.now(timezone.utc)

    return [
        PriceBar(
            timestamp=start + timedelta(days=i),
            open=value,
            high=value + 1,
            low=value - 1,
            close=value,
            volume=1000,
        )
        for i, value in enumerate(values)
    ]


def test_bullish_signal():
    values = [
        100 + i * 0.5
        for i in range(60)
    ]

    signal = calculate_market_signal(
        symbol="AAPL",
        bars=_bars(values),
    )

    assert signal.direction == "bullish"
    assert signal.score is not None


def test_bearish_signal():
    values = [
        150 - i * 0.5
        for i in range(60)
    ]

    signal = calculate_market_signal(
        symbol="AAPL",
        bars=_bars(values),
    )

    assert signal.direction == "bearish"
    assert signal.score is not None