from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from conviction_models import EvidenceKind, EvidenceItem


REQUIRED_CATEGORIES = frozenset({
    EvidenceKind.TECHNICAL,   # regime, momentum, technical
    EvidenceKind.OPTIONS,     # options (IV, Greeks), liquidity (bid/ask, OI, volume)
    EvidenceKind.RISK,        # risk validation
})


@dataclass(frozen=True)
class EvidenceValidation:
    valid: bool
    missing_categories: tuple[str, ...]
    invalid_reasons: tuple[str, ...]


def validate_evidence(
    evidence: Iterable[EvidenceItem],
    required_categories: frozenset[EvidenceKind] = REQUIRED_CATEGORIES,
) -> EvidenceValidation:
    items = list(evidence)

    categories = {
        item.kind for item in items if item.kind is not None
    }

    missing = sorted(str(cat) for cat in (required_categories - categories))

    invalid_reasons: list[str] = []

    for item in items:
        if not item.evidence_id:
            invalid_reasons.append("Evidence item is missing evidence_id.")

        if not item.source:
            invalid_reasons.append(
                f"{item.evidence_id or 'unknown'} has no source."
            )

        if not item.summary:
            invalid_reasons.append(
                f"{item.evidence_id or 'unknown'} has no summary."
            )

    if missing:
        invalid_reasons.append(
            "Missing required evidence categories: "
            + ", ".join(missing)
        )

    return EvidenceValidation(
        valid=not missing and not invalid_reasons,
        missing_categories=tuple(missing),
        invalid_reasons=tuple(invalid_reasons),
    )