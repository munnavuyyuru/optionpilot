from datetime import datetime, timezone
from decimal import Decimal
from execution_models import (
    ExecutionStatus, OptionLeg, AlpacaOrderRequest,
    ExecutionRecord, ExecutionResult, OrderSide, OrderType
)


def test_execution_status_enum():
    assert ExecutionStatus.FILLED == "FILLED"
    assert ExecutionStatus.REJECTED == "REJECTED"


def test_option_leg_creation():
    leg = OptionLeg(symbol="QQQ260918C00650000", side="buy", quantity=1)
    assert leg.symbol == "QQQ260918C00650000"
    assert leg.side == OrderSide.BUY
    assert leg.quantity == 1


def test_execution_record_creation():
    record = ExecutionRecord(
        execution_id="EXE-001",
        intent_id="INT-001",
        decision_id="DEC-001",
        candidate_id="CAND-001",
        symbol="QQQ",
        strategy="BULL_CALL_DEBIT_SPREAD",
        direction="BULLISH",
        status="FILLED",
        requested_quantity=1,
        filled_quantity=1,
        requested_limit_price=Decimal("4.20"),
        average_fill_price=Decimal("4.15"),
        alpaca_order_id="ALP-001",
        submitted_at=datetime.now(timezone.utc),
        filled_at=datetime.now(timezone.utc),
        verified_at=datetime.now(timezone.utc),
        paper=True,
    )
    assert record.symbol == "QQQ"
    assert record.filled_quantity == 1