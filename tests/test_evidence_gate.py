from datetime import datetime, timezone

from conviction_models import EvidenceItem, EvidenceKind
from src.evidence_gate import EvidenceGate, EvidenceGateConfig
from src.evidence_validator import REQUIRED_CATEGORIES


def gate():
    return EvidenceGate(
        EvidenceGateConfig(
            minimum_score=75,
            minimum_conviction=75,
            max_contradictions=3,
            max_market_data_age_seconds=120,
        )
    )


def make_evidence(quality=85, freshness=95):
    now = datetime.now(timezone.utc)
    return [
        EvidenceItem(
            evidence_id="E001",
            kind=EvidenceKind.TECHNICAL,
            source="phase2",
            title="Regime",
            observed_at=now,
            summary="Test evidence",
            relevance=90,
            quality=quality,
            freshness=freshness,
            corroboration_count=1,
            primary_source=True,
        ),
        EvidenceItem(
            evidence_id="E002",
            kind=EvidenceKind.OPTIONS,
            source="phase2",
            title="Options",
            observed_at=now,
            summary="Test options evidence",
            relevance=85,
            quality=quality,
            freshness=freshness,
            corroboration_count=1,
            primary_source=True,
        ),
        EvidenceItem(
            evidence_id="E003",
            kind=EvidenceKind.RISK,
            source="phase2",
            title="Risk",
            observed_at=now,
            summary="Test risk evidence",
            relevance=90,
            quality=quality,
            freshness=freshness,
            corroboration_count=1,
            primary_source=True,
        ),
    ]


def test_good_evidence_passes():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert result.passed


def test_low_conviction_rejects():
    result = gate().evaluate(
        conviction=60,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed
    assert result.status.value == "REJECT"


def test_empty_evidence_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=[],
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed


def test_missing_bull_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=False,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed


def test_missing_bear_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=False,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed


def test_excessive_contradictions_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=True,
        contradictions=["c1", "c2", "c3", "c4"],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed


def test_stale_market_data_rejects():
    old_time = datetime.now(timezone.utc)
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=old_time,
    )
    # The test time is now, so old_time is stale
    assert not result.passed


def test_missing_timestamp_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=None,
    )
    assert not result.passed


def test_low_evidence_score_rejects():
    result = gate().evaluate(
        conviction=85,
        evidence=make_evidence(quality=40, freshness=40),
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed


def test_missing_required_category_rejects():
    # Evidence missing RISK category
    evidence = [
        EvidenceItem(
            evidence_id="E001",
            kind="TECHNICAL",
            source="test",
            title="Regime",
            observed_at=datetime.now(timezone.utc),
            summary="Test",
            relevance=90,
            quality=85,
            freshness=95,
            corroboration_count=1,
            primary_source=True,
        ),
    ]
    result = gate().evaluate(
        conviction=85,
        evidence=evidence,
        bull_present=True,
        bear_present=True,
        contradictions=[],
        market_data_timestamp=datetime.now(timezone.utc),
    )
    assert not result.passed