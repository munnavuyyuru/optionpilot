from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from conviction_models import EvidenceItem, EvidenceKind
from phase4_models import (
    EvidenceCheck,
    EvidenceDecision,
    EvidenceStatus,
)

from freshness import is_fresh
from evidence_validator import validate_evidence, REQUIRED_CATEGORIES


@dataclass(frozen=True)
class EvidenceGateConfig:
    minimum_score: float = 75.0
    minimum_conviction: float = 75.0
    max_contradictions: int = 3
    max_market_data_age_seconds: int = 120
    required_categories: frozenset[EvidenceKind] = REQUIRED_CATEGORIES


class EvidenceGate:
    def __init__(self, config: EvidenceGateConfig) -> None:
        self.config = config

    def evaluate(
        self,
        *,
        conviction: float,
        evidence: list[EvidenceItem],
        bull_present: bool,
        bear_present: bool,
        contradictions: list[str],
        market_data_timestamp: datetime | None,
    ) -> EvidenceDecision:
        checks: list[EvidenceCheck] = []
        reasons: list[str] = []
        missing: list[str] = []

        # CIO Conviction
        if conviction >= self.config.minimum_conviction:
            checks.append(
                EvidenceCheck(
                    name="cio_conviction",
                    passed=True,
                    reason="CIO conviction meets minimum threshold.",
                    actual=conviction,
                    expected=self.config.minimum_conviction,
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="cio_conviction",
                    passed=False,
                    reason="CIO conviction is below the minimum threshold.",
                    actual=conviction,
                    expected=self.config.minimum_conviction,
                )
            )
            reasons.append(
                f"CIO conviction {conviction:.1f} is below "
                f"{self.config.minimum_conviction:.1f}."
            )

        # Evidence Presence
        if evidence:
            checks.append(
                EvidenceCheck(
                    name="evidence_presence",
                    passed=True,
                    reason="Evidence package is not empty.",
                    actual=len(evidence),
                    expected="> 0",
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="evidence_presence",
                    passed=False,
                    reason="Evidence package is empty.",
                    actual=0,
                    expected="> 0",
                )
            )
            missing.append("evidence_package")
            reasons.append("No evidence was supplied.")

        # Evidence Validation (categories, source integrity, completeness)
        validation = validate_evidence(evidence, self.config.required_categories)
        if validation.valid:
            checks.append(
                EvidenceCheck(
                    name="evidence_validation",
                    passed=True,
                    reason="Evidence validation passed.",
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="evidence_validation",
                    passed=False,
                    reason="Evidence validation failed.",
                )
            )
            for reason in validation.invalid_reasons:
                reasons.append(reason)
            for cat in validation.missing_categories:
                missing.append(cat)

        # Bull Thesis Present
        if bull_present:
            checks.append(
                EvidenceCheck(
                    name="bull_thesis",
                    passed=True,
                    reason="Bull thesis is present.",
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="bull_thesis",
                    passed=False,
                    reason="Bull thesis is missing.",
                )
            )
            missing.append("bull_thesis")
            reasons.append("Bull thesis is missing.")

        # Bear Thesis Present
        if bear_present:
            checks.append(
                EvidenceCheck(
                    name="bear_thesis",
                    passed=True,
                    reason="Bear thesis is present.",
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="bear_thesis",
                    passed=False,
                    reason="Bear thesis is missing.",
                )
            )
            missing.append("bear_thesis")
            reasons.append("Bear thesis is missing.")

        # Contradictions
        contradiction_count = len([c for c in contradictions if c.strip()])

        if contradiction_count <= self.config.max_contradictions:
            checks.append(
                EvidenceCheck(
                    name="contradictions",
                    passed=True,
                    reason="Contradictions are within policy.",
                    actual=contradiction_count,
                    expected=f"<= {self.config.max_contradictions}",
                )
            )
        else:
            checks.append(
                EvidenceCheck(
                    name="contradictions",
                    passed=False,
                    reason="Too many unresolved contradictions.",
                    actual=contradiction_count,
                    expected=f"<= {self.config.max_contradictions}",
                )
            )
            reasons.append(
                "Bull/Bear disagreement exceeds the configured policy threshold."
            )

        # Market Data Freshness
        if market_data_timestamp is None:
            checks.append(
                EvidenceCheck(
                    name="market_data_freshness",
                    passed=False,
                    reason="Market-data timestamp is missing.",
                )
            )
            reasons.append("Market-data timestamp is missing.")
        else:
            fresh = is_fresh(
                market_data_timestamp,
                self.config.max_market_data_age_seconds,
            )

            age = 0.0
            if market_data_timestamp is not None:
                from freshness import age_seconds
                age = age_seconds(market_data_timestamp)

            checks.append(
                EvidenceCheck(
                    name="market_data_freshness",
                    passed=fresh,
                    reason=(
                        "Market data is fresh."
                        if fresh
                        else "Market data is stale."
                    ),
                    actual=age,
                    expected=self.config.max_market_data_age_seconds,
                )
            )

            if not fresh:
                reasons.append(
                    f"Market data age {age:.1f}s exceeds "
                    f"{self.config.max_market_data_age_seconds}s."
                )

        # Overall Score
        passed_checks = sum(1 for check in checks if check.passed)
        score = (passed_checks / len(checks) * 100.0) if checks else 0.0

        if score < self.config.minimum_score:
            reasons.append(
                f"Evidence score {score:.1f} is below "
                f"{self.config.minimum_score:.1f}."
            )

        passed = not reasons and score >= self.config.minimum_score

        return EvidenceDecision(
            status=(
                EvidenceStatus.PASS
                if passed
                else EvidenceStatus.REJECT
            ),
            score=score,
            completeness=(
                len(evidence) / max(len(evidence), 1)
                if evidence
                else 0.0
            ),
            checks=tuple(checks),
            contradictions=tuple(contradictions),
            missing=tuple(missing),
            reasons=tuple(reasons),
        )


def age_seconds(timestamp: datetime, now: datetime | None = None) -> float:
    """Helper for EvidenceGate to compute age."""
    from freshness import age_seconds as _age_seconds
    return _age_seconds(timestamp)