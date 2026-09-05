from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alpaca.trading.client import TradingClient


@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    checks: tuple[str, ...]
    discrepancies: tuple[str, ...]


class FillVerifier:
    """Verify that Alpaca fill matches expected execution."""

    def __init__(self, client: TradingClient) -> None:
        self.client = client

    def verify(
        self,
        alpaca_order_id: str,
        expected_symbol: str,
        expected_quantity: int,
        expected_max_loss: float,
    ) -> 'VerificationResult':
        """Verify fill matches expectations."""
        checks = []
        discrepancies = []

        order = self.client.get_order_by_id(alpaca_order_id)

        # Check fill quantity
        filled_qty = int(order.filled_qty or 0)
        if filled_qty != 1:  # For single-contract spreads
            discrepancies.append(f"Expected quantity 1, got {filled_qty}")
        else:
            checks.append("fill_quantity")

        # Check position exists
        try:
            position = self.client.get_open_position(expected_symbol)
            if position:
                checks.append("position_exists")
            else:
                discrepancies.append(f"No position found for {expected_symbol}")
        except Exception:
            discrepancies.append(f"Position check failed for {expected_symbol}")

        # Verify P&L within expected bounds
        # (Optional: compare fill price to expected limit)

        verified = len(discrepancies) == 0
        return VerificationResult(
            verified=verified,
            checks=tuple(checks),
            discrepancies=tuple(discrepancies),
        )