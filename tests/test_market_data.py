from datetime import datetime, timezone

from src.market_data import PriceBar


def test_price_bar_is_created():
    bar = PriceBar(
        timestamp=datetime.now(timezone.utc),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000,
    )

    assert bar.close == 103.0
    assert bar.volume == 1000