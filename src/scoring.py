from __future__ import annotations

from dataclasses import dataclass

from options_selector import OptionCandidate, build_debit_spread
from signals import MarketSignal


@dataclass(frozen=True)
class ScoredCandidate:
    option: OptionCandidate
    market_score: float
    options_score: float
    total_score: float
    eligible: bool
    reasons: tuple[str, ...]
    max_reward: float = 0.0
    max_loss: float = 0.0


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

    # Calculate max_reward and max_loss for debit spread
    max_reward = 0.0
    max_loss = 0.0
    spread_width = 5.0
    spread = build_debit_spread(
        direction=market_signal.direction,
        long_contract=candidate.contract,
        chain={candidate.snapshot.symbol: candidate.snapshot},
        width=spread_width,
    )
    if spread:
        long_leg, short_leg = spread
        long_mid = long_leg.snapshot.midpoint
        short_mid = short_leg.snapshot.midpoint
        if long_mid is not None and short_mid is not None:
            if market_signal.direction == "bullish":
                # Bull call spread: pay net debit, max reward = width - debit
                debit = long_mid - short_mid
                max_loss = debit * 100
                max_reward = (spread_width * 100) - max_loss
            else:
                # Bear put spread: pay net debit
                debit = long_mid - short_mid
                max_loss = debit * 100
                max_reward = (spread_width * 100) - max_loss

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
        max_reward=max_reward,
        max_loss=max_loss,
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
