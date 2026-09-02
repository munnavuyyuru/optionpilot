from __future__ import annotations

from conviction_models import BearThesis, BullThesis, CIODecision, Decision, OptionCandidate


class CIO:
    """Adjudicates only. It cannot mutate the candidate contract."""

    def adjudicate(
        self,
        candidate: OptionCandidate,
        bull: BullThesis,
        bear: BearThesis,
    ) -> CIODecision:
        conviction = max(0, min(100, round(
            0.60 * bull.confidence
            + 0.40 * (100 - bear.confidence)
        )))

        if conviction >= 75 and bull.confidence >= 70 and bear.confidence <= 75:
            decision = Decision.TRADE
        elif bear.confidence >= 80:
            decision = Decision.REJECT
        else:
            decision = Decision.ABSTAIN

        evidence_ids = tuple(
            dict.fromkeys(bull.evidence_ids + bear.evidence_ids)
        )

        return CIODecision(
            decision=decision,
            conviction=conviction,
            rationale=(
                f"CIO compared Bull confidence {bull.confidence} with "
                f"Bear confidence {bear.confidence}; candidate remains "
                "unchanged."
            ),
            strongest_bull_point=bull.key_points[0],
            strongest_bear_point=bear.counterarguments[0],
            unresolved_contradictions=(),
            evidence_ids=evidence_ids,
        )
