from __future__ import annotations

from dataclasses import dataclass

from conviction_models import BearThesis, BullThesis, CIODecision, Decision, EvidencePackage


@dataclass(frozen=True)
class ConvictionPolicy:
    min_trade_conviction: int = 75
    min_evidence_quality: float = 60.0
    max_unresolved_contradictions: int = 2
    min_bull_confidence: int = 70
    max_bear_confidence_for_trade: int = 75

    def apply(
        self,
        bull: BullThesis,
        bear: BearThesis,
        cio: CIODecision,
        evidence: EvidencePackage,
    ) -> tuple[Decision, str]:
        evidence_quality = evidence.average_quality
        contradictions = evidence.unresolved_contradictions + len(
            cio.unresolved_contradictions
        )

        if not evidence.items:
            return Decision.ABSTAIN, "No evidence supplied."

        if evidence_quality < self.min_evidence_quality:
            return (
                Decision.ABSTAIN,
                f"Evidence quality {evidence_quality:.1f} is below "
                f"{self.min_evidence_quality:.1f}.",
            )

        if contradictions > self.max_unresolved_contradictions:
            return (
                Decision.ABSTAIN,
                f"Unresolved contradictions {contradictions} exceed "
                f"{self.max_unresolved_contradictions}.",
            )

        if cio.decision == Decision.TRADE:
            if cio.conviction < self.min_trade_conviction:
                return (
                    Decision.ABSTAIN,
                    f"CIO conviction {cio.conviction} is below "
                    f"{self.min_trade_conviction}.",
                )

            if bull.confidence < self.min_bull_confidence:
                return (
                    Decision.ABSTAIN,
                    f"Bull confidence {bull.confidence} is below "
                    f"{self.min_bull_confidence}.",
                )

            if bear.confidence > self.max_bear_confidence_for_trade:
                return (
                    Decision.ABSTAIN,
                    f"Bear confidence {bear.confidence} is too high "
                    f"for a trade.",
                )

            return Decision.TRADE, "CIO trade decision passed conviction policy."

        if cio.decision == Decision.REJECT:
            return Decision.REJECT, "CIO rejected the candidate."

        return Decision.ABSTAIN, "CIO abstained."
