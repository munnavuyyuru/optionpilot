from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    OptionLegRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from execution_models import (
    ExecutionIntent,
    AlpacaOrderRequest,
    OptionLeg,
    OrderSide,
    OrderType,
    TimeInForce,
)


class OrderTranslator:
    """Translate ExecutionIntent to Alpaca order request."""

    def translate(
        self,
        intent: ExecutionIntent,
        limit_price: Decimal | None = None,
    ) -> dict[str, Any]:
        """Translate intent to Alpaca order request dict."""

        legs = []
        for leg in intent.legs:
            legs.append(OptionLegRequest(
                symbol=leg.symbol,
                side=leg.side.value,
                ratio_quantity=leg.quantity,
            ))

        if intent.order_type == OrderType.MARKET:
            request = MarketOrderRequest(
                symbol=intent.symbol,
                legs=legs,
                quantity=intent.quantity,
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.MLEG,
            )
        else:
            request = LimitOrderRequest(
                symbol=intent.symbol,
                legs=legs,
                quantity=intent.quantity,
                limit_price=limit_price or Decimal("0"),
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.MLEG,
            )

        request.client_order_id = self._generate_client_order_id(intent)

        return request

    def _generate_client_order_id(self, intent) -> str:
        """Generate deterministic client_order_id from intent."""
        # Use intent_id + hash of parameters for idempotency
        key = f"{intent.intent_id}:{intent.symbol}:{intent.direction}:{intent.strategy}"
        return f"EXEC-{hashlib.sha256(key.encode()).hexdigest()[:16].upper()}"