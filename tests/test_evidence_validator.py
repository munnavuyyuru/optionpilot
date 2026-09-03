from datetime import datetime, timezone

from conviction_models import EvidenceItem, EvidenceKind
from src.evidence_validator import validate_evidence, REQUIRED_CATEGORIES


def make_evidence():
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
            quality=85,
            freshness=95,
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
            quality=85,
            freshness=95,
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
            quality=85,
            freshness=95,
            corroboration_count=1,
            primary_source=True,
        ),
    ]


def test_valid_evidence_passes():
    result = validate_evidence(make_evidence())
    assert result.valid
    assert not result.missing_categories
    assert not result.invalid_reasons


def test_missing_category_rejects():
    # Missing RISK category
    evidence = [
        EvidenceItem(
            evidence_id="E001",
            kind=EvidenceKind.TECHNICAL,
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
        EvidenceItem(
            evidence_id="E002",
            kind=EvidenceKind.OPTIONS,
            source="test",
            title="Options",
            observed_at=datetime.now(timezone.utc),
            summary="Test",
            relevance=85,
            quality=85,
            freshness=95,
            corroboration_count=1,
            primary_source=True,
        ),
    ]
    result = validate_evidence(evidence)
    assert not result.valid
    assert "RISK" in result.missing_categories


def test_missing_evidence_id_rejects():
    evidence = [
        EvidenceItem(
            evidence_id="",
            kind=EvidenceKind.TECHNICAL,
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
    result = validate_evidence(evidence)
    assert not result.valid
    assert any("evidence_id" in r for r in result.invalid_reasons)


def test_missing_source_rejects():
    evidence = [
        EvidenceItem(
            evidence_id="E001",
            kind=EvidenceKind.TECHNICAL,
            source="",
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
    result = validate_evidence(evidence)
    assert not result.valid
    assert any("source" in r for r in result.invalid_reasons)


def test_missing_summary_rejects():
    evidence = [
        EvidenceItem(
            evidence_id="E001",
            kind=EvidenceKind.TECHNICAL,
            source="test",
            title="Regime",
            observed_at=datetime.now(timezone.utc),
            summary="",
            relevance=90,
            quality=85,
            freshness=95,
            corroboration_count=1,
            primary_source=True,
        ),
    ]
    result = validate_evidence(evidence)
    assert not result.valid
    assert any("summary" in r for r in result.invalid_reasons)