#!/usr/bin/env python3
"""Phase 5 Demo Runner - Mock and Live modes."""

from __future__ import annotations

import argparse
import yaml
from datetime import datetime, timezone
from decimal import Decimal

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
from execution_engine import ExecutionEngine
from alpaca_connection import create_client
from execution_models import ExecutionStatus


def make_approved_candidate(symbol: str = "QQQ") -> OptionCandidate:
    """Create a mock candidate for demo purposes."""
    now = datetime.now(timezone.utc)

    evidence = EvidencePackage(
        items=(
            EvidenceItem(
                evidence_id=f"SIG-REGIME-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Regime",
                observed_at=datetime.now(timezone.utc),
                summary="20-day SMA above 50-day SMA", relevance=85, quality=85, freshness=95,
                corroboration_count=2, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"SIG-MOMENTUM-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Momentum",
                observed_at=datetime.now(timezone.utc),
                summary="20-session momentum positive", relevance=80, quality=80, freshness=95,
                corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-IV-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind="OPTIONS", source="phase2_option_chain", title="IV 650C",
                observed_at=datetime.now(timezone.utc),
                summary="Implied volatility 0.28", relevance=85, quality=90, freshness=90,
                corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-GREEKS-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind="OPTIONS", source="phase2_option_chain", title="Greeks 650C",
                observed_at=datetime.now(timezone.utc),
                summary="Delta=0.55 Gamma=0.02 Theta=-0.03 Vega=0.10",
                relevance=90, quality=90, freshness=90, corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"RISK-VAL-{symbol}-{now.strftime('%Y%m%d')}",
                kind="RISK", source="phase2_risk", title="Risk Validation",
                observed_at=datetime.now(timezone.utc),
                summary="Risk check passed", relevance=95, quality=100, freshness=100,
                corroboration_count=1, primary_source=True,
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


def make_evidence_rejected_candidate(symbol: str = "NVDA") -> OptionCandidate:
    """Create a mock candidate with low conviction for evidence rejection."""
    now = datetime.now(timezone.utc)

    evidence = EvidencePackage(
        items=(
            EvidenceItem(
                evidence_id=f"SIG-REGIME-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Regime",
                observed_at=now,
                summary="Bearish market regime",
                relevance=85, quality=85, freshness=95,
                corroboration_count=2, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"SIG-MOMENTUM-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Momentum",
                observed_at=now,
                summary="Negative momentum",
                relevance=80, quality=80, freshness=95,
                corroboration_count=1, primary_source=True,
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


def make_risk_blocked_candidate(symbol: str = "QQQ") -> OptionCandidate:
    """Create a mock candidate that will be blocked by risk sentinel."""
    now = datetime.now(timezone.utc)

    evidence = EvidencePackage(
        items=(
            EvidenceItem(
                evidence_id=f"SIG-REGIME-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Regime",
                observed_at=now,
                summary="20-day SMA above 50-day SMA",
                relevance=85, quality=85, freshness=95,
                corroboration_count=2, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"SIG-MOMENTUM-{symbol}-{now.strftime('%Y%m%d')}",
                kind="TECHNICAL", source="phase2", title="Momentum",
                observed_at=now,
                summary="20-session momentum positive",
                relevance=80, quality=80, freshness=95,
                corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-IV-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind="OPTIONS", source="phase2_option_chain", title="IV 650C",
                observed_at=now,
                summary="Implied volatility 0.28",
                relevance=85, quality=90, freshness=90,
                corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"OPT-GREEKS-{symbol}-650-{now.strftime('%Y%m%d')}",
                kind="OPTIONS", source="phase2_option_chain", title="Greeks 650C",
                observed_at=now,
                summary="Delta=0.55 Gamma=0.02 Theta=-0.03 Vega=0.10",
                relevance=90, quality=90, freshness=90,
                corroboration_count=1, primary_source=True,
            ),
            EvidenceItem(
                evidence_id=f"RISK-VAL-{symbol}-{now.strftime('%Y%m%d')}",
                kind="RISK", source="phase2_risk", title="Risk Validation",
                observed_at=now,
                summary="Risk check passed",
                relevance=95, quality=100, freshness=100,
                corroboration_count=1, primary_source=True,
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
    """Run Phase 5 demo with mock data."""
    print("=" * 60)
    print("OPTIONPILOT PHASE 5 DEMO — MOCK MODE")
    print("=" * 60)
    print()

    # Load configs
    with open("config/execution.yaml") as f:
        exec_config = yaml.safe_load(f)

    with open("config/risk.yaml") as f:
        risk_config = yaml.safe_load(f)

    # Build Phase 4 pipeline
    risk_policy = RiskPolicy(
        max_position_risk_usd=risk_config["risk"]["max_position_risk_usd"],
        max_daily_loss_usd=risk_config["risk"]["max_daily_loss_usd"],
        max_total_options_exposure_usd=risk_config["risk"]["max_total_options_exposure_usd"],
        max_single_symbol_exposure_usd=risk_config["risk"]["max_single_symbol_exposure_usd"],
        max_open_positions=risk_config["risk"]["max_open_positions"],
        min_dte=risk_config["risk"]["min_dte"],
        max_dte=risk_config["risk"]["max_dte"],
        max_bid_ask_pct=risk_config["risk"]["max_bid_ask_pct"],
        min_open_interest=risk_config["risk"]["min_open_interest"],
        min_volume=risk_config["risk"]["min_volume"],
    )

    evidence_gate_config = EvidenceGateConfig(
        minimum_score=risk_config.get("evidence", {}).get("minimum_score", 75.0),
        minimum_conviction=75.0,
        max_contradictions=3,
        max_market_data_age_seconds=120,
    )

    # Phase 4 pipeline
    phase4_pipeline = Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=Phase4Ledger("logs"),
    )

    # Phase 5 engine
    engine = ExecutionEngine(exec_config)

    print("=" * 60)
    print("OPTIONPILOT PHASE 5 DEMO — MOCK MODE")
    print("=" * 60)
    print()

    # Test: Full approval path
    print("-" * 60)
    print("SCENARIO 1: FULL EXECUTION (Mock)")
    print("-" * 60)

    candidate = make_approved_candidate("QQQ")
    portfolio = PortfolioRiskInput(
        daily_loss_usd=50.0,
        total_options_exposure_usd=1000.0,
        symbol_exposure_usd=400.0,
        open_positions=1,
        duplicate_symbol=False,
    )
    option_risk = OptionRiskInput(
        max_loss_per_contract_usd=420.0,
        quantity=1,
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
        policy=ConvictionPolicy(),
    )
    conviction_result = engine.evaluate(candidate)

    # Phase 4
    phase4_pipeline = Phase4Pipeline(
        evidence_gate=EvidenceGate(EvidenceGateConfig(minimum_score=75, minimum_conviction=75, max_contradictions=3, max_market_data_age_seconds=120)),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=Phase4Ledger("logs"),
    )
    phase4_result = phase4_pipeline.evaluate(
        candidate=candidate,
        cio_decision=conviction_result.cio,
        evidence=list(candidate.evidence.items),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
        option_risk=OptionRiskInput(
            max_loss_per_contract_usd=420, quantity=1, dte=32,
            bid=4.10, ask=4.30, open_interest=500, volume=100, market_data_fresh=True
        ),
        portfolio_risk=PortfolioRiskInput(
            daily_loss_usd=50, total_options_exposure_usd=1000,
            symbol_exposure_usd=400, open_positions=1, duplicate_symbol=False
        ),
    )

    print(f"Phase 4 Result: {phase4_result.final_status.value}")
    print(f"Execution Intent: {'CREATED' if phase4_result.execution_intent else 'NONE'}")

    if phase4_result.execution_intent:
        print("Phase 4 PASSED - Ready for Phase 5 Execution")
        print("Execution Intent:")
        print(f"  Symbol: {phase4_result.execution_intent.symbol}")
        print(f"  Contracts: {phase4_result.execution_intent.option_contracts}")
        print(f"  Max Loss: ${phase4_result.execution_intent.max_loss_usd:.2f}")
        print(f"  Quantity: {phase4_result.execution_intent.quantity}")
        print()
        print("DRY RUN: Order would be submitted to Alpaca Paper")
        print("Execution Intent: CREATED")
        print("Order submitted: NO (dry run)")
    else:
        print(f"Phase 4 Result: {phase4_result.final_status.value}")
        print(f"Reasons: {phase4_result.reasons}")


def run_live_demo(symbol: str):
    """Run Phase 5 with live Alpaca data."""
    print("=" * 60)
    print(f"OPTIONPILOT PHASE 5 DEMO — LIVE — {symbol}")
    print("=" * 60)
    print()

    with open("config/execution.yaml") as f:
        exec_config = yaml.safe_load(f)

    with open("config/risk.yaml") as f:
        risk_config = yaml.safe_load(f)

    risk_policy = RiskPolicy(
        max_position_risk_usd=risk_config["risk"]["max_position_risk_usd"],
        max_daily_loss_usd=risk_config["risk"]["max_daily_loss_usd"],
        max_total_options_exposure_usd=risk_config["risk"]["max_total_options_exposure_usd"],
        max_single_symbol_exposure_usd=risk_config["risk"]["max_single_symbol_exposure_usd"],
        max_open_positions=risk_config["risk"]["max_open_positions"],
        min_dte=risk_config["risk"]["min_dte"],
        max_dte=risk_config["risk"]["max_dte"],
        max_bid_ask_pct=risk_config["risk"]["max_bid_ask_pct"],
        min_open_interest=risk_config["risk"]["min_open_interest"],
        min_volume=risk_config["risk"]["min_volume"],
    )

    evidence_gate_config = EvidenceGateConfig(
        minimum_score=75.0,
        minimum_conviction=75.0,
        max_contradictions=3,
        max_market_data_age_seconds=120,
    )

    ledger = Phase4Ledger("logs")
    phase4_pipeline = Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=Phase4Ledger("logs"),
    )

    # Get live portfolio state
    trading_client = create_client()
    portfolio = get_portfolio_state(trading_client)
    symbol_exposure = get_symbol_exposure(trading_client, symbol)
    duplicate = check_duplicate_symbol(trading_client, symbol)

    portfolio.symbol_exposure_usd = symbol_exposure
    portfolio.duplicate_symbol = duplicate

    # Phase 5 engine
    engine = ExecutionEngine(exec_config)

    print("=" * 60)
    print(f"OPTIONPILOT PHASE 5 DEMO — LIVE — {symbol}")
    print("=" * 60)
    print()

    # Run Phase 2 scan to get candidate
    # This would use the actual Phase 2 scan_market.py
    print("LIVE MODE: Phase 2→3→4→5 pipeline not fully implemented yet.")
    print("Use --mock for demonstration.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 Autonomous Execution Engine Demo")
    parser.add_argument(
        "--symbol",
        default="QQQ",
        choices=["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA"],
        help="Symbol for live mode.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run with live Alpaca paper.",
    )
    args = parser.parse_args()

    if args.live:
        run_live_demo(args.symbol)
    else:
        run_mock_demo()

    return 0


if __name__ == "__main__":
    exit(main())