from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alpaca_connection import create_client
from conviction_models import OptionCandidate, CIODecision
from conviction_engine import ConvictionEngine
from agents import DeterministicBullAgent, DeterministicBearAgent, CIO
from phase4_models import (
    EvidenceDecision,
    RiskDecision,
    FinalStatus,
    Phase4Decision,
    ExecutionIntent,
    OptionRiskInput,
    PortfolioRiskInput,
)
from evidence_gate import EvidenceGate, EvidenceGateConfig
from risk_sentinel import RiskSentinel
from portfolio_state import get_portfolio_state, get_symbol_exposure, check_duplicate_symbol
from ledger import Phase4Ledger
from alpaca_connection import create_client as create_trading_client


class Phase4Pipeline:
    def __init__(
        self,
        evidence_gate: EvidenceGate,
        risk_sentinel: RiskSentinel,
        ledger: Phase4Ledger,
    ) -> None:
        self.evidence_gate = evidence_gate
        self.risk_sentinel = risk_sentinel
        self.ledger = ledger

    def evaluate(
        self,
        *,
        candidate: OptionCandidate,
        cio_decision: CIODecision,
        evidence: list,
        bull_present: bool,
        bear_present: bool,
        contradictions: list[str],
        market_data_timestamp,
        option_risk: OptionRiskInput,
        portfolio_risk: PortfolioRiskInput,
    ) -> Phase4Decision:
        decision_id = f"P4-{uuid4().hex[:12].upper()}"

        # Step 1: Evidence Gate
        evidence_result = self.evidence_gate.evaluate(
            conviction=cio_decision.conviction,
            evidence=evidence,
            bull_present=bull_present,
            bear_present=bear_present,
            contradictions=contradictions,
            market_data_timestamp=market_data_timestamp,
        )

        if not evidence_result.passed:
            result = Phase4Decision(
                decision_id=decision_id,
                symbol=candidate.underlying,
                direction=candidate.direction.value,
                conviction=cio_decision.conviction,
                evidence=evidence_result,
                risk=None,
                final_status=FinalStatus.REJECTED,
                reasons=evidence_result.reasons,
                execution_intent=None,
                created_at=datetime.now(timezone.utc),
            )

            self.ledger.record_decision(result)
            self.ledger.record_evidence(decision_id, candidate.underlying, evidence_result)
            return result

        # Step 2: Risk Sentinel
        risk_result = self.risk_sentinel.evaluate(
            option=option_risk,
            portfolio=portfolio_risk,
        )

        if not risk_result.approved:
            result = Phase4Decision(
                decision_id=decision_id,
                symbol=candidate.underlying,
                direction=candidate.direction.value,
                conviction=cio_decision.conviction,
                evidence=evidence_result,
                risk=risk_result,
                final_status=FinalStatus.BLOCKED,
                reasons=risk_result.blocking_reasons,
                execution_intent=None,
                created_at=datetime.now(timezone.utc),
            )

            self.ledger.record_decision(result)
            self.ledger.record_evidence(decision_id, candidate.underlying, evidence_result)
            self.ledger.record_risk(decision_id, candidate.underlying, risk_result)
            return result

        # Step 3: Approved - Create Execution Intent
        intent = ExecutionIntent(
            decision_id=decision_id,
            symbol=candidate.underlying,
            direction=candidate.direction.value,
            strategy=candidate.strategy,
            option_contracts=tuple(candidate.contracts),
            quantity=candidate.quantity,
            max_loss_usd=candidate.max_loss,
            max_reward_usd=candidate.max_reward,
            created_at=datetime.now(timezone.utc),
        )

        result = Phase4Decision(
            decision_id=decision_id,
            symbol=candidate.underlying,
            direction=candidate.direction.value,
            conviction=cio_decision.conviction,
            evidence=evidence_result,
            risk=risk_result,
            final_status=FinalStatus.APPROVED,
            reasons=("Evidence Gate passed and Risk Sentinel approved.",),
            execution_intent=intent,
            created_at=datetime.now(timezone.utc),
        )

        self.ledger.record_decision(result)
        self.ledger.record_evidence(decision_id, candidate.underlying, evidence_result)
        self.ledger.record_risk(decision_id, candidate.underlying, risk_result)
        return result


def build_pipeline(
    evidence_gate_config: EvidenceGateConfig,
    risk_policy,
    ledger: Phase4Ledger,
) -> Phase4Pipeline:
    return Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=ledger,
    )


def run_phase4_full(
    symbol: str,
    evidence_gate_config: EvidenceGateConfig,
    risk_policy,
    ledger: Phase4Ledger,
    bull_agent,
    bear_agent,
    cio,
) -> Phase4Decision:
    """Run full Phase 2 → Phase 3 → Phase 4 pipeline for a symbol."""

    # Phase 2: Get candidate from Phase 2 engine
    from scan_market import scan_symbol
    from phase2_adapter import scored_candidate_to_option_candidate

    # This would use the actual Phase 2 scanner - simplified for demo
    # In production, this calls the actual Phase 2 scan
    pass