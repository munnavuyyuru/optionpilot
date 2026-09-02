from datetime import date, timedelta

from src.options_data import (
    OptionContractData,
    OptionSnapshotData,
)
from src.options_selector import OptionCandidate
from src.risk import validate_candidate


def _candidate():
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

    return OptionCandidate(
        contract=contract,
        snapshot=snapshot,
        dte=30,
        liquidity_score=90,
        options_score=90,
        reasons=(),
    )


def test_risk_passes():
    result = validate_candidate(
        candidate=_candidate(),
        max_debit_usd=1000,
        max_contracts=1,
    )

    assert result.approved is True


def test_risk_rejects_expensive_contract():
    result = validate_candidate(
        candidate=_candidate(),
        max_debit_usd=100,
        max_contracts=1,
    )

    assert result.approved is False