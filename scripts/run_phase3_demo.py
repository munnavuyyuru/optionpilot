#!/usr/bin/env python3
"""Phase 3 demo runner - deterministic version using mock data."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from agents import CIO, DeterministicBearAgent, DeterministicBullAgent
from conviction_engine import ConvictionEngine
from conviction_models import (
    Direction,
    EvidenceItem,
    EvidenceKind,
    EvidencePackage,
    OptionCandidate,
)


def make_mock_candidate(symbol: str = "QQQ") -> OptionCandidate:
    """Create a mock candidate for demo purposes."""
    now = datetime.now(UTC)

    evidence = EvidencePackage(
        items=(
            EvidenceItem(
                evidence_id=f"SIG-REGIME-{symbol}-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.TECHNICAL,
                source="phase2",
                title="Regime",
                observed_at=now,
                summary="20-day SMA above 50-day SMA",
                relevance=85,
                quality=85,
                freshness=95,
                corroboration_count=2,
                primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"SIG-MOMENTUM-{symbol}-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.TECHNICAL,
                source="phase2",
                title="Momentum",
                observed_at=now,
                summary="20-session momentum positive",
                relevance=80,
                quality=80,
                freshness=95,
                corroboration_count=1,
                primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-IV-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.OPTIONS,
                source="phase2_option_chain",
                title="IV 650C",
                observed_at=now,
                summary="Implied volatility 0.28",
                relevance=85,
                quality=90,
                freshness=90,
                corroboration_count=1,
                primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-GREEKS-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.OPTIONS,
                source="phase2_option_chain",
                title="Greeks 650C",
                observed_at=now,
                summary="Delta=0.55 Gamma=0.02 Theta=-0.03 Vega=0.10",
                relevance=90,
                quality=90,
                freshness=90,
                corroboration_count=1,
                primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"RISK-VAL-{symbol}-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.RISK,
                source="phase2_risk",
                title="Risk Validation",
                observed_at=now,
                summary="Risk check passed",
                relevance=95,
                quality=100,
                freshness=100,
                corroboration_count=1,
                primary_source=True,
            ),
        )
    )

    return OptionCandidate(
        candidate_id=f"{symbol}-CAND-{now.strftime('%Y%m%d%H%M')}",
        underlying=symbol,
        direction=Direction.BULLISH,
        strategy="BULL_CALL_DEBIT_SPREAD",
        contracts=(f"{symbol}260918C00650000", f"{symbol}260918C00665000"),
        expiry="2026-09-18",
        strikes=(650.0, 665.0),
        quantity=1,
        max_loss=420.0,
        max_reward=1080.0,
        signal_score=84.0,
        evidence=evidence,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 Conviction Engine Demo")
    parser.add_argument(
        "--symbol",
        default="QQQ",
        choices=["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA"],
        help="Symbol to demo (default: QQQ)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live Phase 2 data (not implemented yet)",
    )
    args = parser.parse_args()

    if args.live:
        print("Live mode not yet implemented. Using mock data.")
        print()

    print("=" * 60)
    print(f"OPTIONPILOT PHASE 3 DEMO — {args.symbol}")
    print("=" * 60)
    print()

    candidate = make_mock_candidate(args.symbol)

    print(f"Candidate: {candidate.candidate_id}")
    print(f"Underlying: {candidate.underlying}")
    print(f"Direction: {candidate.direction.value}")
    print(f"Strategy: {candidate.strategy}")
    print(f"Contracts: {candidate.contracts}")
    print(f"Expiry: {candidate.expiry}")
    print(f"Strikes: {candidate.strikes}")
    print(f"Max Loss: ${candidate.max_loss:.2f}")
    print(f"Max Reward: ${candidate.max_reward:.2f}")
    print(f"Signal Score: {candidate.signal_score:.1f}")
    print(f"Evidence Items: {len(candidate.evidence.items)}")
    print()

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
    )

    result = engine.evaluate(candidate)

    print("=" * 60)
    print("CONVICTION RESULT")
    print("=" * 60)
    print()
    print(f"Decision ID: {result.decision_id}")
    print(f"Candidate: {result.candidate.candidate_id}")
    print(f"Bull confidence: {result.bull.confidence}")
    print(f"Bear confidence: {result.bear.confidence}")
    print(f"CIO conviction: {result.cio.conviction}")
    print(f"Decision: {result.cio.decision.value}")
    print()
    print(f"Policy: {result.policy_reason}")
    print()
    print(f"Evidence Quality: {result.evidence_quality:.1f}")
    print(f"Evidence Freshness: {result.evidence_freshness:.1f}")
    print()
    print(f"Bull Summary: {result.bull.summary}")
    print(f"Bear Summary: {result.bear.summary}")
    print()
    print(f"CIO Rationale: {result.cio.rationale}")
    print()
    print("Ledger: logs/decisions.jsonl")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
