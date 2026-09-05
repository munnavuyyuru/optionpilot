from execution_guard import ExecutionGuard
from phase4_models import (
    Phase4Decision, ExecutionIntent, EvidenceDecision, RiskDecision,
    FinalStatus, RiskStatus, EvidenceStatus
)
from conviction_models import CIODecision, Decision
from datetime import datetime, timezone


def make_approved_decision():
    return Phase4Decision(
        decision_id="DEC-001",
        symbol="QQQ",
        direction="BULLISH",
        conviction=85,
        evidence=EvidenceDecision(status=EvidenceStatus.PASS, score=85, completeness=1.0, checks=(), contradictions=(), missing=(), reasons=()),
        risk=RiskDecision(status=RiskStatus.APPROVED, checks=()),
        final_status=FinalStatus.APPROVED,
        execution_intent=ExecutionIntent(
            decision_id="DEC-001",
            symbol="QQQ",
            direction="BULLISH",
            strategy="BULL_CALL_DEBIT_SPREAD",
            option_contracts=("QQQ260918C00650000", "QQQ260918C00665000"),
            quantity=1,
            max_loss_usd=420.0,
            max_reward_usd=1080.0,
            created_at=datetime.now(timezone.utc),
        ),
        created_at=datetime.now(timezone.utc),
    )


def test_guard_passes_for_valid_intent():
    guard = ExecutionGuard({"execution": {"enabled": True, "max_order_notional_usd": 1000}})
    decision = make_approved_decision()
    intent = decision.execution_intent

    result = guard.validate(intent=intent, phase4_decision=decision)
    assert result.passed


def test_guard_rejects_missing_approval():
    guard = ExecutionGuard({"execution": {"enabled": True}})
    decision = Phase4Decision(
        decision_id="DEC-001", symbol="QQQ", direction="BULLISH", conviction=85,
        evidence=EvidenceDecision(status=EvidenceStatus.PASS, score=85, completeness=1.0, checks=(), contradictions=(), missing=(), reasons=()),
        risk=None, final_status=FinalStatus.REJECTED, execution_intent=None,
        created_at=datetime.now(timezone.utc),
    )
    intent = ExecutionIntent(decision_id="DEC-001", symbol="QQQ", direction="BULLISH",
        strategy="BULL_CALL_DEBIT_SPREAD", option_contracts=("C1", "C2"),
        quantity=1, max_loss_usd=420, max_reward_usd=1080, created_at=datetime.now(timezone.utc))

    result = guard.validate(intent=intent, phase4_decision=decision)
    assert not result.passed
    assert any("APPROVED" in r for r in result.blocking_reasons)


def test_guard_rejects_excessive_loss():
    guard = ExecutionGuard({"execution": {"enabled": True, "max_order_notional_usd": 100}})
    decision = make_approved_decision()
    intent = decision.execution_intent  # max_loss = 420 > 100 limit

    result = guard.validate(intent=intent, phase4_decision=decision)
    assert not result.passed
    assert any("exceeds execution limit" in r for r in result.blocking_reasons)