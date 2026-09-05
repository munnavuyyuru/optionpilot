from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from typing import Any

from alpaca_connection import create_client
from phase4_models import Phase4Decision, ExecutionIntent as Phase4ExecutionIntent
from execution_models import (
    ExecutionRecord, ExecutionStatus, ExecutionResult,
    ExecutionIntent, OptionLeg, OrderSide, OrderType, TimeInForce
)
from execution_guard import ExecutionGuard
from order_translator import OrderTranslator
from alpaca_executor import AlpacaExecutor, ExecutionResult as AlpacaResult
from order_monitor import OrderMonitor, FillResult
from fill_verifier import FillVerifier, VerificationResult
from execution_ledger import ExecutionLedger
from recovery import ExecutionRecovery
from alpaca_connection import create_client
from order_store import get_order_store
from order_id import generate_client_order_id
from alpaca.trading.enums import OrderStatus
import time


@dataclass
class ExecutionContext:
    intent_id: str
    decision_id: str
    candidate_id: str
    execution_id: str
    client_order_id: str
    alpaca_order_id: str | None = None
    status: ExecutionStatus = ExecutionStatus.RECEIVED


class ExecutionEngine:
    """Main orchestration for Phase 5 execution."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.trading_client = create_client()
        self.guard = ExecutionGuard(config)
        self.translator = OrderTranslator()
        self.executor = AlpacaExecutor(self.trading_client)
        self.monitor = OrderMonitor(self.trading_client)
        self.verifier = FillVerifier(self.trading_client)
        self.ledger = ExecutionLedger("logs")
        self.recovery = ExecutionRecovery()
        self.order_store = get_order_store()

    def execute(self, phase4_decision) -> ExecutionResult:
        """Execute a Phase 4 approved decision."""

        if not phase4_decision.execution_intent:
            return self._failed_result("No execution intent in Phase 4 decision")

        intent = phase4_decision.execution_intent
        decision_id = phase4_decision.decision_id

        # 1. Generate IDs
        execution_id = f"EXE-{uuid4().hex[:12].upper()}"
        intent_id = f"INT-{uuid4().hex[:12].upper()}"
        client_order_id = generate_client_order_id(
            intent.symbol, "SPREAD", datetime.now(timezone.utc)
        )

        # 1. Execution Guard
        guard_result = self.guard.validate(
            intent=phase4_decision.execution_intent,
            phase4_decision=phase4_decision,
            trading_client=create_client(),
        )
        if not guard_result.passed:
            return self._rejected_result(
                execution_id, intent, phase4_decision, guard_result.blocking_reasons
            )

        # 2. Translate to Alpaca request
        order_request = self.translator.translate(phase4_decision.execution_intent)

        # 3. Submit to Alpaca
        alpaca_result = self.executor.submit_order(order_request)
        if not alpaca_result.success:
            return self._failed_result(
                execution_id, intent, phase4_decision,
                [alpaca_result.error_message or "Submission failed"]
            )

        alpaca_order_id = alpaca_result.alpaca_order_id

        # 3. Save initial order record
        self._save_initial_order(
            client_order_id, alpaca_order_id, phase4_decision, intent
        )

        # 4. Monitor order
        fill_result = self.monitor.wait_for_fill(
            alpaca_order_id,
            timeout=self.config.get("execution", {}).get("order_timeout_seconds", 120),
        )

        # 5. Verify fill
        if fill_result.filled_quantity > 0:
            verification = self.verifier.verify(
                alpaca_order_id=fill_result.alpaca_order_id,
                expected_symbol=phase4_decision.symbol,
                expected_quantity=phase4_decision.execution_intent.quantity,
                expected_max_loss=phase4_decision.execution_intent.max_loss_usd,
            )
            if not verification.verified:
                return self._verification_failed(execution_id, verification)

        # 5. Record final result
        result = self._build_result(
            execution_id, intent, phase4_decision, fill_result, True
        )
        self.ledger.record(result)
        return result

    def _save_initial_order(self, client_order_id, alpaca_order_id, decision, intent):
        order_store = get_order_store()
        order_store.save_order(
            client_order_id=client_order_id,
            alpaca_order=type('obj', (object,), {
                'id': alpaca_order_id,
                'client_order_id': client_order_id,
                'symbol': intent.symbol,
                'side': 'buy',
                'order_type': 'limit',
                'qty': str(intent.quantity),
                'status': 'pending_new',
                'created_at': datetime.now(timezone.utc).isoformat(),
            })(),
            metadata={
                "decision_id": decision.decision_id,
                "intent_id": intent.intent_id,
                "candidate_id": decision.candidate_id,
                "strategy": intent.strategy,
            }
        )

    def _rejected_result(self, execution_id, intent, decision, reasons):
        result = ExecutionResult(
            execution_id=execution_id,
            intent_id="",
            decision_id=decision.decision_id,
            status=ExecutionStatus.REJECTED,
            alpaca_order_id=None,
            filled_quantity=0,
            average_fill_price=None,
            filled_at=None,
            verified=False,
            error_code="GUARD_REJECTED",
            error_message="; ".join(reasons),
        )
        self.ledger.record(result)
        return result

    def _failed_result(self, execution_id, intent, decision, reasons):
        result = ExecutionResult(
            execution_id=execution_id,
            intent_id="",
            decision_id=decision.decision_id,
            status=ExecutionStatus.FAILED,
            alpaca_order_id=None,
            filled_quantity=0,
            average_fill_price=None,
            filled_at=None,
            verified=False,
            error_code="EXECUTION_FAILED",
            error_message="; ".join(reasons),
        )
        self.ledger.record(result)
        return result

    def _verification_failed(self, execution_id, verification):
        result = ExecutionResult(
            execution_id=execution_id,
            intent_id="",
            decision_id="",
            status=ExecutionStatus.FAILED,
            alpaca_order_id="",
            filled_quantity=0,
            average_fill_price=None,
            filled_at=None,
            verified=False,
            error_code="VERIFICATION_FAILED",
            error_message="; ".join(verification.discrepancies),
        )
        self.ledger.record(result)
        return result

    def _build_result(self, execution_id, intent, decision, fill_result, verified):
        return ExecutionResult(
            execution_id=execution_id,
            intent_id=f"INT-{uuid4().hex[:12].upper()}",
            decision_id=decision.decision_id,
            status=ExecutionStatus.FILLED if fill_result.filled_quantity > 0 else ExecutionStatus.REJECTED,
            alpaca_order_id=fill_result.alpaca_order_id,
            filled_quantity=fill_result.filled_quantity,
            average_fill_price=Decimal(str(fill_result.filled_avg_price)) if fill_result.filled_avg_price else None,
            filled_at=datetime.fromisoformat(fill_result.filled_at) if fill_result.filled_at else None,
            verified=verified,
            error_code=None,
            error_message=None,
        )