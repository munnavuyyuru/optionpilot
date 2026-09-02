from __future__ import annotations

from dataclasses import dataclass

from options_selector import OptionCandidate
from signals import MarketSignal


@dataclass(frozen=True)
class ScoredCandidate:
    option: OptionCandidate
    market_score: float
    options_score: float
    total_score: float
    eligible: bool
    reasons: tuple[str, ...]


def score_candidate(
    market_signal: MarketSignal,
    candidate: OptionCandidate,
    threshold: float = 75.0,
) -> ScoredCandidate:
    if market_signal.score is None:
        return ScoredCandidate(
            option=candidate,
            market_score=0.0,
            options_score=candidate.options_score,
            total_score=0.0,
            eligible=False,
            reasons=(
                "Market signal incomplete.",
                "Sentiment/volatility inputs are unavailable.",
            ),
        )

    total_score = (
        market_signal.score * 0.60
        + candidate.options_score * 0.40
    )

    eligible = (
        total_score >= threshold
        and market_signal.direction != "neutral"
    )

    reasons = (
        f"market_score={market_signal.score:.2f}",
        f"options_score={candidate.options_score:.2f}",
        f"total_score={total_score:.2f}",
    )

    return ScoredCandidate(
        option=candidate,
        market_score=market_signal.score,
        options_score=candidate.options_score,
        total_score=total_score,
        eligible=eligible,
        reasons=reasons,
    )


def rank_candidates(
    market_signal: MarketSignal,
    candidates: list[OptionCandidate],
    threshold: float = 75.0,
) -> list[ScoredCandidate]:
    scored = [
        score_candidate(
            market_signal=market_signal,
            candidate=candidate,
            threshold=threshold,
        )
        for candidate in candidates
    ]

    scored.sort(
        key=lambda candidate: candidate.total_score,
        reverse=True,
    )

    return scored