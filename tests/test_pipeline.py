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


def make_candidate(symbol="QQQ", signal_score=84.0):
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
        signal_score=signal_score,
        evidence=evidence,
    )


def make_pipeline():
    risk_policy = RiskPolicy(
        max_position_risk_usd=500.0,
        max_daily_loss_usd=500.0,
        max_total_options_exposure_usd=5000.0,
        max_single_symbol_exposure_usd=1500.0,
        max_open_positions=5,
        min_dte=21,
        max_dte=60,
        max_bid_ask_pct=0.10,
        min_open_interest=100,
        min_volume=10,
    )

    evidence_gate_config = EvidenceGateConfig(
        minimum_score=75.0,
        minimum_conviction=75.0,
        max_contradictions=3,
        max_market_data_age_seconds=120,
    )

    ledger = Phase4Ledger("logs")
    return Phase4Pipeline(
        evidence_gate=EvidenceGate(evidence_gate_config),
        risk_sentinel=RiskSentinel(risk_policy),
        ledger=ledger,
    )


def valid_option_risk():
    return OptionRiskInput(
        max_loss_per_contract_usd=420.0,
        quantity=1,
        dte=32,
        bid=4.10,
        ask=4.30,
        open_interest=500,
        volume=100,
        market_data_fresh=True,
    )


def valid_portfolio_risk():
    return PortfolioRiskInput(
        daily_loss_usd=50.0,
        total_options_exposure_usd=1000.0,
        symbol_exposure_usd=400.0,
        open_positions=1,
        duplicate_symbol=False,
    )


def test_approved_creates_intent():
    candidate = make_candidate(signal_score=95.0)
    pipeline = make_pipeline()

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
        policy=ConvictionPolicy(),
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
        option_risk=valid_option_risk(),
        portfolio_risk=valid_portfolio_risk(),
    )

    assert result.final_status.value == "APPROVED"
    assert result.execution_intent is not None
    assert result.execution_intent.symbol == "QQQ"
    assert result.execution_intent.max_loss_usd == 420.0
    assert result.risk is not None
    assert result.risk.approved


def test_evidence_rejected_no_risk_run():
    candidate = make_candidate(signal_score=58.0)
    pipeline = make_pipeline()

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
        policy=ConvictionPolicy(),
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
        option_risk=valid_option_risk(),
        portfolio_risk=valid_portfolio_risk(),
    )

    assert result.final_status.value == "REJECTED"
    assert result.risk is None
    assert result.execution_intent is None


def test_risk_blocked_no_intent():
    candidate = make_candidate(signal_score=95.0)
    pipeline = make_pipeline()

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
        policy=ConvictionPolicy(),
    )
    conviction_result = engine.evaluate(candidate)

    # Portfolio with high symbol exposure
    portfolio_risk = PortfolioRiskInput(
        daily_loss_usd=50.0,
        total_options_exposure_usd=1000.0,
        symbol_exposure_usd=2000.0,  # Exceeds 1500 limit
        open_positions=1,
        duplicate_symbol=False,
    )

    conviction_result = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
        policy=ConvictionPolicy(),
    ).evaluate(candidate)

    result = pipeline.evaluate(
        candidate=candidate,
        cio_decision=conviction_result.cio,
        evidence=list(candidate.evidence.items),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
        option_risk=valid_option_risk(),
        portfolio_risk=portfolio_risk,
    )

    assert result.final_status.value == "BLOCKED"
    assert result.execution_intent is None
    assert result.risk is not None
    assert not result.risk.approved


def test_missing_data_blocked():
    candidate = make_candidate(signal_score=95.0)
    pipeline = make_pipeline()

    engine = ConvictionEngine(
        bull_agent=DeterministicBullAgent(),
        bear_agent=DeterministicBearAgent(),
        cio=CIO(),
        policy=ConvictionPolicy(),
    )
    conviction_result = engine.evaluate(candidate)

    # Option with missing DTE and stale data
    option_risk = OptionRiskInput(
        max_loss_per_contract_usd=420.0,
        quantity=1,
        dte=None,  # Missing DTE
        bid=4.10,
        ask=4.30,
        open_interest=500,
        volume=100,
        market_data_fresh=False,  # Stale data
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
        portfolio_risk=valid_portfolio_risk(),
    )

    assert result.final_status.value == "BLOCKED"
    assert result.execution_intent is None