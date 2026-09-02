from __future__ import annotations

from abc import ABC, abstractmethod

from conviction_models import BullThesis, OptionCandidate


class BullAgent(ABC):
    @abstractmethod
    def analyze(self, candidate: OptionCandidate) -> BullThesis:
        raise NotImplementedError


class DeterministicBullAgent(BullAgent):
    """
    Offline implementation used for tests and demos.

    Replace this adapter with a real LLM-backed implementation without changing
    the orchestration contract.
    """

    def analyze(self, candidate: OptionCandidate) -> BullThesis:
        evidence = candidate.evidence
        evidence_ids = tuple(item.evidence_id for item in evidence.items[:3])

        return BullThesis(
            summary=(
                f"{candidate.underlying} has a {candidate.direction.value.lower()} "
                "candidate supported by the supplied evidence."
            ),
            key_points=(
                f"Deterministic signal score is {candidate.signal_score:.1f}/100.",
                f"Defined-risk structure has max loss {candidate.max_loss:.2f}.",
            ),
            catalysts=("Signal alignment remains supportive.",),
            invalidation_conditions=(
                "Candidate evidence becomes stale.",
                "Deterministic Phase 2 signal falls below policy threshold.",
            ),
            evidence_ids=evidence_ids or (candidate.evidence.items[0].evidence_id,),
            confidence=min(95, max(50, int(candidate.signal_score))),
            uncertainty=("Qualitative evidence may change after the snapshot.",),
        )
