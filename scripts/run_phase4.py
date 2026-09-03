#!/usr/bin/env python3
"""Phase 4 Demo Runner - Mock and Live modes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from conviction_models import (
    Direction,
    EvidenceItem,
    EvidenceKind,
    EvidencePackage,
    OptionCandidate,
)
from agents import CIO, DeterministicBullAgent, DeterministicBearAgent
from conviction_engine import ConvictionEngine
from conviction_policy import ConvictionPolicy
from phase4_models import (
    OptionRiskInput,
    PortfolioRiskInput,
)
from evidence_gate import EvidenceGate, EvidenceGateConfig
from risk_sentinel import RiskSentinel
from risk_policy import RiskPolicy
from pipeline import Phase4Pipeline
from ledger import Phase4Ledger
from portfolio_state import get_portfolio_state, get_symbol_exposure, check_duplicate_symbol
from alpaca_connection import create_client


def make_mock_candidate(symbol: str = "QQQ") -> OptionCandidate:
    """Create a mock candidate for demo purposes."""
    now = datetime.now(timezone.utc)

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
        signal_score=95.0,
        evidence=evidence,
    )


def make_mock_evidence_rejected_candidate(symbol: str = "NVDA") -> OptionCandidate:
    """Create a mock candidate with low conviction for evidence rejection."""
    now = datetime.now(timezone.utc)

    evidence = EvidencePackage(
        items=(
            EvidenceItem(
                evidence_id=f"SIG-REGIME-{symbol}-{now.strftime('%Y%m%d')}",
                kind=EvidenceKind.TECHNICAL,
                source="phase2",
                title="Regime",
                observed_at=now,
                summary="Bearish market regime",
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
                summary="Negative momentum",
                relevance=80,
                quality=80,
                freshness=95,
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
        signal_score=58.0,  # Low signal score
        evidence=evidence,
    )


def make_mock_risk_blocked_candidate(symbol: str = "QQQ") -> OptionCandidate:
    """Create a mock candidate that will be blocked by risk sentinel."""
    now = datetime.now(timezone.utc)

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
        signal_score=95.0,
        evidence=evidence,
    )


def run_mock_demo():
    """Run Phase 4 demo with mock data."""
    print("=" * 60)
    print("OPTIONPILOT PHASE 4 DEMO — MOCK MODE")
    print("=" * 60)
    print()

    # Load config
    risk_policy = RiskPolicy.from_yaml("config/risk.yaml")

    evidence_gate_config = EvidenceGateConfig(
        minimum_score=risk_policy.required_evidence_categories and 75.0 or 75.0,
        minimum_conviction=75.0,
        max_contradictions=3,
        max_market_data_age_seconds=120,
    )

    ledger = Phase4Ledger("logs")
    pipeline = Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=ledger,
    )

    # Scenario 1: APPROVED
    print("-" * 60)
    print("SCENARIO 1: APPROVED")
    print("-" * 60)
    run_scenario(pipeline, make_mock_candidate("QQQ"), "QQQ")

    # Scenario 2: EVIDENCE REJECTED
    print()
    print("-" * 60)
    print("SCENARIO 2: EVIDENCE REJECTED")
    print("-" * 60)
    run_scenario(pipeline, make_mock_evidence_rejected_candidate("NVDA"), "NVDA")

    # Scenario 3: RISK BLOCKED
    print()
    print("-" * 60)
    print("SCENARIO 3: RISK BLOCKED")
    print("-" * 60)
    # Create candidate with high symbol exposure to trigger risk block
    candidate = make_mock_risk_blocked_candidate("QQQ")
    # Modify portfolio to have high symbol exposure
    run_scenario_with_portfolio(pipeline, candidate, "QQQ", high_exposure=True)

    print()
    print("=" * 60)
    print("MOCK DEMO COMPLETE")
    print("=" * 60)


def run_scenario(pipeline, candidate, symbol):
    """Run a single scenario with mock portfolio state."""
    now = datetime.now(timezone.utc)

    # Mock portfolio state
    portfolio_risk = PortfolioRiskInput(
        daily_loss_usd=50.0,
        total_options_exposure_usd=1000.0,
        symbol_exposure_usd=400.0,
        open_positions=1,
        duplicate_symbol=False,
    )

    option_risk = OptionRiskInput(
        max_loss_per_contract_usd=candidate.max_loss,
        quantity=candidate.quantity,
        dte=32,
        bid=4.10,
        ask=4.30,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )

    # Get CIO decision
    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
    )
    conviction_result = engine.evaluate(candidate)

    result = pipeline.evaluate(
        candidate=candidate,
        cio_decision=conviction_result.cio,
        evidence=list(candidate.evidence.items),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
        option_risk=option_risk,
        portfolio_risk=portfolio_risk,
    )

    print_result(result)
    return result


def run_scenario_with_portfolio(pipeline, candidate, symbol, high_exposure=False):
    """Run scenario with custom portfolio state."""
    now = datetime.now(timezone.utc)

    portfolio_risk = PortfolioRiskInput(
        daily_loss_usd=50.0,
        total_options_exposure_usd=5500.0 if high_exposure else 1000.0,
        symbol_exposure_usd=2000.0 if high_exposure else 400.0,
        open_positions=1,
        duplicate_symbol=False,
    )

    option_risk = OptionRiskInput(
        max_loss_per_contract_usd=candidate.max_loss,
        quantity=candidate.quantity,
        dte=32,
        bid=4.10,
        ask=4.30,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
    )
    conviction_result = engine.evaluate(candidate)

    result = pipeline.evaluate(
        candidate=candidate,
        cio_decision=conviction_result.cio,
        evidence=list(candidate.evidence.items),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
        option_risk=option_risk,
        portfolio_risk=portfolio_risk,
    )

    print_result(result)
    return result


def print_result(result):
    print(f"Decision ID: {result.decision_id}")
    print(f"Symbol: {result.symbol}")
    print(f"Direction: {result.direction}")
    print(f"Conviction: {result.conviction:.0f}")
    print(f"Evidence: {result.evidence.status.value}")
    print(f"Risk: {result.risk.status.value if result.risk else 'NOT RUN'}")
    print(f"FINAL: {result.final_status.value}")

    if result.reasons:
        print("Reasons:")
        for r in result.reasons:
            print(f"  - {r}")

    if result.execution_intent:
        print("Execution Intent: CREATED")
        print(f"  Contracts: {result.execution_intent.option_contracts}")
        print(f"  Max Loss: ${result.execution_intent.max_loss_usd:.2f}")
        print(f"  Max Reward: ${result.execution_intent.max_reward_usd:.2f}")
    else:
        print("Execution Intent: NOT CREATED")

    print(f"Order submitted: NO")
    print()


def run_live_demo(symbol: str):
    """Run Phase 4 with live Alpaca data."""
    print("=" * 60)
    print(f"OPTIONPILOT PHASE 4 DEMO — LIVE — {symbol}")
    print("=" * 60)
    print()

    risk_policy = RiskPolicy.from_yaml("config/risk.yaml")

    evidence_gate_config = EvidenceGateConfig(
        minimum_score=75.0,
        minimum_conviction=75.0,
        max_contradictions=3,
        max_market_data_age_seconds=120,
    )

    ledger = Phase4Ledger("logs")
    pipeline = Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=ledger,
    )

    # Get live portfolio state
    trading_client = create_client()
    portfolio = get_portfolio_state(trading_client)
    symbol_exposure = get_symbol_exposure(trading_client, symbol)
    duplicate = check_duplicate_symbol(trading_client, symbol)

    portfolio.symbol_exposure_usd = symbol_exposure
    portfolio.duplicate_symbol = duplicate

    # Run Phase 2 scan to get candidate
    # This would use the actual Phase 2 scan_market.py
    print("LIVE MODE: Phase 2→3→4 pipeline not fully implemented yet.")
    print("Use --mock for demonstration.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 Evidence Gate + Risk Sentinel Demo")
    parser.add_argument(
        "--symbol",
        default="QQQ",
        choices=["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA"],
        help="Symbol for live mode.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run with live Alpaca data.",
    )
    args = parser.parse_args()

    if args.live:
        run_live_demo(args.symbol)
    else:
        run_mock_demo()

    return 0


if __name__ == "__main__":
    exit(main())