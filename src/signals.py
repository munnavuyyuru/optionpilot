from __future__ import annotations

from dataclasses import dataclass

from market_data import PriceBar


@dataclass(frozen=True)
class SignalComponent:
    name: str
    score: float | None
    weight: float
    reason: str


@dataclass(frozen=True)
class MarketSignal:
    symbol: str
    direction: str
    score: float | None
    components: tuple[SignalComponent, ...]
    reasons: tuple[str, ...]


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None

    return sum(values[-period:]) / period


def _momentum_score(closes: list[float]) -> float | None:
    if len(closes) < 21:
        return None

    current = closes[-1]
    previous = closes[-21]

    if previous <= 0:
        return None

    return max(
        0.0,
        min(
            100.0,
            50.0 + ((current / previous) - 1.0) * 500.0,
        ),
    )


def _technical_score(closes: list[float]) -> float | None:
    fast = _sma(closes, 20)
    slow = _sma(closes, 50)

    if fast is None or slow is None:
        return None

    if slow <= 0:
        return None

    ratio = fast / slow

    return max(
        0.0,
        min(
            100.0,
            50.0 + (ratio - 1.0) * 1000.0,
        ),
    )


def _regime_score(closes: list[float]) -> float | None:
    fast = _sma(closes, 20)
    slow = _sma(closes, 50)

    if fast is None or slow is None:
        return None

    if fast > slow:
        return 75.0

    if fast < slow:
        return 25.0

    return 50.0


def _direction(
    regime_score: float | None,
    momentum_score: float | None,
    technical_score: float | None,
) -> str:
    available = [
        score
        for score in (
            regime_score,
            momentum_score,
            technical_score,
        )
        if score is not None
    ]

    if not available:
        return "neutral"

    average = sum(available) / len(available)

    if average >= 60.0:
        return "bullish"

    if average <= 40.0:
        return "bearish"

    return "neutral"


def calculate_market_signal(
    symbol: str,
    bars: list[PriceBar],
) -> MarketSignal:
    closes = [bar.close for bar in bars]

    regime = _regime_score(closes)
    momentum = _momentum_score(closes)
    technical = _technical_score(closes)

    components = (
        SignalComponent(
            name="regime",
            score=regime,
            weight=0.25,
            reason=(
                "20-day SMA versus 50-day SMA."
            ),
        ),
        SignalComponent(
            name="momentum",
            score=momentum,
            weight=0.25,
            reason=(
                "20-session price momentum."
            ),
        ),
        SignalComponent(
            name="technical",
            score=technical,
            weight=0.20,
            reason=(
                "Short/medium moving-average relationship."
            ),
        ),
        SignalComponent(
            name="sentiment",
            score=None,
            weight=0.15,
            reason=(
                "Unavailable: no sentiment data source "
                "is configured in Phase 2."
            ),
        ),
        SignalComponent(
            name="volatility",
            score=None,
            weight=0.15,
            reason=(
                "Reserved for realized/option-implied "
                "volatility integration."
            ),
        ),
    )

    weighted_scores = [
        component.score * component.weight
        for component in components
        if component.score is not None
    ]

    weighted_weights = [
        component.weight
        for component in components
        if component.score is not None
    ]

    if not weighted_weights:
        total_score = None
    else:
        total_score = (
            sum(weighted_scores)
            / sum(weighted_weights)
        )

    direction = _direction(
        regime,
        momentum,
        technical,
    )

    reasons = tuple(
        component.reason
        for component in components
    )

    return MarketSignal(
        symbol=symbol,
        direction=direction,
        score=total_score,
        components=components,
        reasons=reasons,
    )