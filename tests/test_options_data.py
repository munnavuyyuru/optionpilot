from datetime import date, timedelta

from src.options_data import OptionSnapshotData


def test_midpoint():
    snapshot = OptionSnapshotData(
        symbol="TEST",
        bid=4.0,
        ask=5.0,
        last=4.5,
        implied_volatility=0.30,
        delta=0.50,
        gamma=0.02,
        theta=-0.03,
        vega=0.10,
    )

    assert snapshot.midpoint == 4.5


def test_spread():
    snapshot = OptionSnapshotData(
        symbol="TEST",
        bid=4.0,
        ask=5.0,
        last=4.5,
        implied_volatility=0.30,
        delta=0.50,
        gamma=0.02,
        theta=-0.03,
        vega=0.10,
    )

    assert snapshot.spread == 1.0
    assert snapshot.spread_pct == 1.0 / 4.5