from datetime import date, timedelta

from src.market_data import PriceBar
from src.options_data import (
    OptionContractData,
    OptionSnapshotData,
)
from src.options_selector import OptionCandidate
from src.scoring import score_candidate
from src.signals import calculate_market_signal


def test_candidate_score_is_bounded():
    bars = [
        PriceBar(
            timestamp=None,
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i,
            volume=1000,
        )
        for i in range(60)
    ]

    signal = calculate_market_signal(
        symbol="AAPL",
        bars=bars,
    )

    contract = OptionContractData(
        symbol="TEST",
        contract_id="id",
        underlying_symbol="AAPL",
        expiration_date=(
            date.today() + timedelta(days=30)
        ),
        strike_price=200.0,
        option_type="call",
        tradable=True,
        open_interest=1000,
    )

    snapshot = OptionSnapshotData(
        symbol="TEST",
        bid=4.9,
        ask=5.0,
        last=4.95,
        implied_volatility=0.25,
        delta=0.55,
        gamma=0.02,
        theta=-0.03,
        vega=0.1,
    )

    option = OptionCandidate(
        contract=contract,
        snapshot=snapshot,
        dte=30,
        liquidity_score=90,
        options_score=90,
        reasons=(),
    )

    result = score_candidate(
        market_signal=signal,
        candidate=option,
    )

    assert 0 <= result.total_score <= 100