from __future__ import annotations

from abc import ABC, abstractmethod

from conviction_models import BearThesis, OptionCandidate


class BearAgent(ABC):
    @abstractmethod
    def analyze(self, candidate: OptionCandidate) -> BearThesis:
        raise NotImplementedError


class DeterministicBearAgent(BearAgent):
    def analyze(self, candidate: OptionCandidate) -> BearThesis:
        evidence = candidate.evidence
        evidence_ids = tuple(item.evidence_id for item in evidence.items[:3])

        return BearThesis(
            summary=(
                "The candidate can fail if supporting evidence weakens or "
                "contradictory conditions intensify."
            ),
            key_points=(
                f"Options carry a defined max loss of {candidate.max_loss:.2f}.",
                "A bullish thesis is exposed to regime reversal.",
            ),
            invalidation_conditions=(
                "Underlying moves against the candidate direction.",
                "Liquidity or volatility conditions deteriorate.",
            ),
            evidence_ids=evidence_ids or (candidate.evidence.items[0].evidence_id,),
            confidence=55,
            counterarguments=(
                "The evidence package is a snapshot rather than a guarantee.",
                "Options can lose value even when the underlying thesis is directionally correct.",
            ),
            risk_flags=("Regime reversal", "Option premium risk"),
            uncertainty=("Future market conditions are unknown.",),
        )
