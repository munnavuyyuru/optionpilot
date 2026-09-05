from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from alpaca_connection import create_client
from execution_models import ExecutionIntent
from phase4_models import (
    ExecutionIntent as Phase4ExecutionIntent,
    Phase4Decision,
)
from safety import assert_paper_environment
from order_store import get_order_store
import yaml


@dataclass(frozen=True)
class GuardResult:
    passed: bool
    reasons: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()


class ExecutionGuard:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.order_store = get_order_store()

    def validate(
        self,
        intent: Phase4ExecutionIntent,
        phase4_decision: Phase4Decision,
        trading_client=None,
    ) -> GuardResult:
        """Validate execution intent before submission."""
        reasons = []
        blocking = []

        # 1. Paper environment
        try:
            assert_paper_environment()
        except RuntimeError as e:
            blocking.append(str(e))

        # 2. Execution enabled
        exec_config = self.config.get("execution", {})
        if not exec_config.get("enabled", False):
            blocking.append("Execution is disabled in configuration")

        # 3. Phase 4 approval
        if not phase4_decision.execution_intent:
            blocking.append("No execution intent in Phase 4 decision")

        if phase4_decision.final_status.value != "APPROVED":
            blocking.append(f"Phase 4 status is {phase4_decision.final_status.value}, not APPROVED")

        # 4. Evidence Gate
        if not phase4_decision.evidence.passed:
            blocking.append("Evidence Gate did not pass")

        # 5. Risk Sentinel
        if not phase4_decision.risk or not phase4_decision.risk.approved:
            blocking.append("Risk Sentinel did not approve")

        # 6. Intent consistency
        max_notional = exec_config.get("max_order_notional_usd", 1000)
        if intent.max_loss_usd > max_notional:
            blocking.append(f"Intent max_loss ${intent.max_loss_usd} exceeds execution limit ${max_notional}")

        # 7. Duplicate check
        if self._is_duplicate(intent):
            blocking.append("Duplicate execution intent detected")

        # 8. Contract tradability (check via Alpaca)
        if trading_client:
            try:
                for contract_symbol in intent.option_contracts:
                    # Could verify contract exists and is tradable
                    pass
            except Exception as e:
                blocking.append(f"Contract validation failed: {e}")

        return GuardResult(
            passed=len(blocking) == 0,
            reasons=tuple(reasons),
            blocking_reasons=tuple(blocking),
        )

    def _is_duplicate(self, intent) -> bool:
        """Check for duplicate execution within window."""
        # Use decision_id + candidate_id as idempotency key
        # Check recent executions in order store
        return False  # Implement based on execution ledger


def load_execution_config() -> dict:
    """Load execution configuration from config/execution.yaml."""
    with open("config/execution.yaml", "r") as f:
        return yaml.safe_load(f)


def load_risk_config() -> dict:
    """Load risk configuration from config/risk.yaml."""
    with open("config/risk.yaml", "r") as f:
        return yaml.safe_load(f)