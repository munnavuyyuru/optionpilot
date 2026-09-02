from datetime import date, timedelta

from src.options_data import (
    OptionContractData,
    OptionSnapshotData,
)
from src.options_selector import select_candidates


def test_neutral_market_returns_no_candidates():
    result = select_candidates(
        direction="neutral",
        contracts=[],
        chain={},
        min_dte=21,
        max_dte=45,
        min_open_interest=100,
        max_spread_pct=0.10,
    )

    assert result == []


def test_bullish_selects_calls():
    contract = OptionContractData(
        symbol="AAPL-CALL",
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
        symbol="AAPL-CALL",
        bid=4.90,
        ask=5.00,
        last=4.95,
        implied_volatility=0.25,
        delta=0.55,
        gamma=0.02,
        theta=-0.03,
        vega=0.10,
    )

    result = select_candidates(
        direction="bullish",
        contracts=[contract],
        chain={contract.symbol: snapshot},
        min_dte=21,
        max_dte=45,
        min_open_interest=100,
        max_spread_pct=0.10,
    )

    assert len(result) == 1
    assert result[0].contract.option_type == "call"