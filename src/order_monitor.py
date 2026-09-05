from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus


@dataclass(frozen=True)
class FillResult:
    alpaca_order_id: str
    status: str
    filled_quantity: int
    filled_avg_price: float | None
    filled_at: str | None
    raw_response: dict


class OrderMonitor:
    """Monitor Alpaca order until fill, timeout, or cancellation."""

    def __init__(self, client: TradingClient, poll_interval: float = 2.0) -> None:
        self.client = client
        self.poll_interval = poll_interval

    def wait_for_fill(
        self,
        order_id: str,
        timeout: int = 120,
    ) -> FillResult:
        """Poll order until fill, timeout, or cancellation."""
        start = time.time()

        while time.time() - start < timeout:
            order = self.client.get_order_by_id(order_id)
            status = order.status

            if status == OrderStatus.FILLED:
                return FillResult(
                    alpaca_order_id=order_id,
                    status=status.value,
                    filled_quantity=int(order.filled_qty or 0),
                    filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    filled_at=order.filled_at.isoformat() if order.filled_at else None,
                    raw_response=order.__dict__ if hasattr(order, "__dict__") else {},
                )

            if status in (OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED):
                return FillResult(
                    alpaca_order_id=order_id,
                    status=status.value,
                    filled_quantity=int(order.filled_qty or 0),
                    filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    filled_at=None,
                    raw_response={},
                )

            time.sleep(self.poll_interval)

        # Timeout
        return FillResult(
            alpaca_order_id=order_id,
            status="TIMEOUT",
            filled_quantity=0,
            filled_avg_price=None,
            filled_at=None,
            raw_response={},
        )