from decimal import Decimal
from order_translator import OrderTranslator
from execution_models import (
    ExecutionIntent, OptionLeg, OrderSide, OrderType, TimeInForce
)
from datetime import datetime, timezone


def test_translate_limit_order():
    translator = OrderTranslator()
    intent = ExecutionIntent(
        intent_id="INT-001",
        decision_id="DEC-001",
        candidate_id="CAND-001",
        symbol="QQQ",
        direction="BULLISH",
        strategy="BULL_CALL_DEBIT_SPREAD",
        legs=(
            OptionLeg(symbol="QQQ260918C00650000", side="buy", quantity=1),
            OptionLeg(symbol="QQQ260918C00665000", side="sell", quantity=1),
        ),
        option_contracts=("QQQ260918C00650000", "QQQ260918C00665000"),
        quantity=1,
        order_type="limit",
        limit_price=4.20,
        max_loss_usd=420.0,
        max_reward_usd=1080.0,
        created_at=datetime.now(timezone.utc),
    )

    translator = OrderTranslator()
    request = translator.translate(intent, Decimal("4.20"))

    # Check that it's a LimitOrderRequest with correct parameters
    assert hasattr(request, 'symbol')
    assert request.symbol == "QQQ"
    assert request.quantity == 1
    assert request.limit_price == 4.20
    assert len(request.legs) == 2


def test_generate_client_order_id():
    from execution_models import ExecutionIntent, OptionLeg
    from datetime import datetime, timezone

    intent = ExecutionIntent(
        intent_id="INT-001",
        decision_id="DEC-001",
        candidate_id="CAND-001",
        symbol="QQQ",
        direction="BULLISH",
        strategy="BULL_CALL_DEBIT_SPREAD",
        legs=(
            OptionLeg(symbol="QQQ260918C00650000", side="buy", quantity=1),
        ),
        option_contracts=("QQQ260918C00650000",),
        quantity=1,
        order_type="limit",
        limit_price=4.20,
        max_loss_usd=420.0,
        max_reward_usd=1080.0,
        created_at=datetime.now(timezone.utc),
    )

    translator = OrderTranslator()
    client_order_id = translator._generate_client_order_id(intent)

    assert client_order_id.startswith("EXEC-")
    assert len(client_order_id) == 21  # "EXEC-" + 16 chars