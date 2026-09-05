from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import OrderRequest
from alpaca.trading.enums import OrderStatus
from alpaca_connection import create_client


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    alpaca_order_id: str | None
    alpaca_response: dict | None
    error_code: str | None
    error_message: str | None


class AlpacaExecutor:
    """Thin wrapper around Alpaca TradingClient for order execution."""

    def __init__(self, client: TradingClient | None = None) -> None:
        self.client = client or create_client()

    def submit_order(self, order_request) -> ExecutionResult:
        """Submit order to Alpaca paper trading."""
        try:
            response = self.client.submit_order(order_request)
            return ExecutionResult(
                success=True,
                alpaca_order_id=response.id,
                alpaca_response=response.__dict__ if hasattr(response, "__dict__") else {"id": response.id},
                error_code=None,
                error_message=None,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                alpaca_order_id=None,
                alpaca_response=None,
                error_code="SUBMISSION_FAILED",
                error_message=str(e),
            )

    def get_order(self, order_id: str):
        """Get order status from Alpaca."""
        return self.client.get_order_by_id(order_id)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            self.client.cancel_order_by_id(order_id)
            return True
        except Exception:
            return False

    def get_position(self, symbol: str):
        """Get current position for symbol."""
        try:
            return self.client.get_open_position(symbol)
        except Exception:
            return None

    def list_open_orders(self):
        """List all open orders."""
        return self.client.get_orders(status="open")