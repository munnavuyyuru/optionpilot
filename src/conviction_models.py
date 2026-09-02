from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Direction(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class Decision(StrEnum):
    TRADE = "TRADE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


class EvidenceKind(StrEnum):
    MARKET_DATA = "MARKET_DATA"
    NEWS = "NEWS"
    FUNDAMENTAL = "FUNDAMENTAL"
    OPTIONS = "OPTIONS"
    TECHNICAL = "TECHNICAL"
    RISK = "RISK"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=3)
    kind: EvidenceKind
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    observed_at: datetime
    summary: str = Field(min_length=1)
    relevance: int = Field(ge=0, le=100)
    quality: int = Field(ge=0, le=100)
    freshness: int = Field(ge=0, le=100)
    corroboration_count: int = Field(ge=0)
    primary_source: bool = False
    contradicts_evidence_ids: tuple[str, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class EvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[EvidenceItem, ...] = ()

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(item.evidence_id for item in self.items)

    def get(self, evidence_id: str) -> EvidenceItem:
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item
        raise KeyError(evidence_id)

    def validate_refs(self, refs: tuple[str, ...]) -> None:
        missing = sorted(set(refs) - self.ids)
        if missing:
            raise ValueError(f"unknown evidence references: {missing}")

    @property
    def average_quality(self) -> float:
        if not self.items:
            return 0.0
        return sum(item.quality for item in self.items) / len(self.items)

    @property
    def average_freshness(self) -> float:
        if not self.items:
            return 0.0
        return sum(item.freshness for item in self.items) / len(self.items)

    @property
    def unresolved_contradictions(self) -> int:
        return sum(1 for item in self.items if item.contradicts_evidence_ids)


class OptionCandidate(BaseModel):
    """
    Immutable Phase 2 contract.

    Phase 3 agents can discuss this object but cannot mutate its trading fields.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=3)
    underlying: str = Field(min_length=1)
    direction: Direction
    strategy: str = Field(min_length=1)
    contracts: tuple[str, ...] = Field(min_length=1)
    expiry: str = Field(min_length=1)
    strikes: tuple[float, ...] = Field(min_length=1)
    quantity: int = Field(gt=0)
    max_loss: float = Field(ge=0)
    max_reward: float = Field(ge=0)
    signal_score: float = Field(ge=0, le=100)
    evidence: EvidencePackage

    @property
    def risk_reward(self) -> float:
        if self.max_loss == 0:
            return float("inf")
        return self.max_reward / self.max_loss


class ThesisBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    key_points: tuple[str, ...] = Field(min_length=1)
    invalidation_conditions: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    confidence: int = Field(ge=0, le=100)
    uncertainty: tuple[str, ...] = ()


class BullThesis(ThesisBase):
    catalysts: tuple[str, ...] = ()


class BearThesis(ThesisBase):
    counterarguments: tuple[str, ...] = Field(min_length=1)
    risk_flags: tuple[str, ...] = ()


class CIODecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    conviction: int = Field(ge=0, le=100)
    rationale: str = Field(min_length=1)
    strongest_bull_point: str = Field(min_length=1)
    strongest_bear_point: str = Field(min_length=1)
    unresolved_contradictions: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class ConvictionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=3)
    created_at: datetime
    candidate: OptionCandidate
    bull: BullThesis
    bear: BearThesis
    cio: CIODecision
    evidence_quality: float = Field(ge=0, le=100)
    evidence_freshness: float = Field(ge=0, le=100)
    policy_reason: str = Field(min_length=1)
