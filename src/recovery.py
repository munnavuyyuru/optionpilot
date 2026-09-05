from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus
from alpaca_connection import create_client


@dataclass(frozen=True)
class RecoveryResult:
    reconciled: bool
    actions_taken: tuple[str, ...]
    discrepancies: tuple[str, ...]


class ExecutionRecovery:
    """Reconcile local execution state with Alpaca broker state on startup."""

    def __init__(self) -> None:
        self.client = create_client()

    def reconcile(self) -> RecoveryResult:
        """Reconcile local execution state with Alpaca."""
        actions = []
        discrepancies = []

        # Get all local executions with SUBMITTED/PARTIALLY_FILLED status
        local_executions = self._load_pending_executions()

        for exec_record in local_executions:
            alpaca_order_id = exec_record.get("alpaca_order_id")
            if not alpaca_order_id:
                continue

            try:
                order = self.client.get_order_by_id(alpaca_order_id)
                broker_status = order.status.value

                # Reconcile local status with broker status
                local_status = exec_record.get("status")
                if local_status != broker_status:
                    actions.append(f"Updated {exec_record['execution_id']}: {local_status} -> {broker_status}")
                    # Update local record (would need ledger update method)

                if broker_status == "filled":
                    # Verify position
                    pass

            except Exception as e:
                discrepancies.append(f"Failed to reconcile {alpaca_order_id}: {e}")

        return RecoveryResult(
            reconciled=len(discrepancies) == 0,
            actions_taken=tuple(actions),
            discrepancies=tuple(discrepancies),
        )

    def _load_pending_executions(self) -> list[dict]:
        """Load executions that need reconciliation."""
        # Read executions.jsonl and filter for pending statuses
        import json
        from pathlib import Path

        pending = []
        path = Path("logs/executions.jsonl")
        if not path.exists():
            return []

        pending_statuses = {"SUBMITTED", "PARTIALLY_FILLED", "SUBMITTING", "VALIDATED"}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get("status") in pending_statuses:
                        pending.append(record)
                except json.JSONDecodeError:
                    continue

        return pending