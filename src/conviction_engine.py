from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from agents import BearAgent, BullAgent
from conviction_models import ConvictionResult, OptionCandidate
from conviction_policy import ConvictionPolicy
from decision_ledger import DecisionLedger


class ConvictionEngine:
    def __init__(
        self,
        bull_agent: BullAgent,
        bear_agent: BearAgent,
        cio,
        policy: ConvictionPolicy | None = None,
        ledger: DecisionLedger | None = None,
    ) -> None:
        self.bull_agent = bull_agent
        self.bear_agent = bear_agent
        self.cio = cio
        self.policy = policy or ConvictionPolicy()
        self.ledger = ledger or DecisionLedger()

    def evaluate(self, candidate: OptionCandidate) -> ConvictionResult:
        if not candidate.evidence.items:
            raise ValueError("Phase 3 requires a non-empty evidence package.")

        bull = self.bull_agent.analyze(candidate)
        bear = self.bear_agent.analyze(candidate)

        candidate.evidence.validate_refs(bull.evidence_ids)
        candidate.evidence.validate_refs(bear.evidence_ids)

        cio = self.cio.adjudicate(candidate, bull, bear)
        candidate.evidence.validate_refs(cio.evidence_ids)

        decision, policy_reason = self.policy.apply(
            bull=bull,
            bear=bear,
            cio=cio,
            evidence=candidate.evidence,
        )

        # Policy is deterministic and has final authority over the AI's label.
        cio = cio.model_copy(update={"decision": decision})

        result = ConvictionResult(
            decision_id=f"DEC-{uuid4().hex[:12].upper()}",
            created_at=datetime.now(UTC),
            candidate=candidate,
            bull=bull,
            bear=bear,
            cio=cio,
            evidence_quality=candidate.evidence.average_quality,
            evidence_freshness=candidate.evidence.average_freshness,
            policy_reason=policy_reason,
        )
        self.ledger.append(result)
        return result
