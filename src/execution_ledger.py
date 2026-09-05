from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from execution_models import ExecutionRecord, ExecutionResult


class ExecutionLedger:
    def __init__(self, base_path: str | Path = "logs") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(v) for v in value]
        if hasattr(value, "value"):
            return value.value
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    def record(self, result) -> None:
        """Record execution result to executions.jsonl."""
        path = self.base_path / "executions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "execution_id": result.execution_id,
            "intent_id": result.intent_id,
            "decision_id": result.decision_id,
            "symbol": result.symbol,
            "strategy": result.strategy,
            "direction": result.direction,
            "status": result.status.value if hasattr(result.status, "value") else result.status,
            "requested_quantity": result.requested_quantity,
            "filled_quantity": result.filled_quantity,
            "requested_limit_price": float(result.requested_limit_price) if result.requested_limit_price else None,
            "average_fill_price": float(result.average_fill_price) if result.average_fill_price else None,
            "max_loss_usd": result.max_loss_usd,
            "max_reward_usd": result.max_reward_usd,
            "alpaca_order_id": result.alpaca_order_id,
            "submitted_at": result.submitted_at.isoformat() if result.submitted_at else None,
            "filled_at": result.filled_at.isoformat() if result.filled_at else None,
            "verified_at": result.verified_at.isoformat() if result.verified_at else None,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "paper": result.paper,
        }

        with open(self.base_path / "executions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")