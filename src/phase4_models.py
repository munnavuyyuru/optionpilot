from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from conviction_models import EvidenceKind, CIODecision, OptionCandidate


class EvidenceStatus(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"


class RiskStatus(StrEnum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


class FinalStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class EvidenceCheck:
    name: str
    passed: bool
    reason: str
    actual: Any = None
    expected: Any = None


@dataclass(frozen=True)
class EvidenceDecision:
    status: EvidenceStatus
    score: float
    completeness: float
    checks: tuple[EvidenceCheck, ...] = ()
    contradictions: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status is EvidenceStatus.PASS


@dataclass(frozen=True)
class RiskCheck:
    name: str
    passed: bool
    reason: str
    actual: Any = None
    limit: Any = None


@dataclass(frozen=True)
class RiskDecision:
    status: RiskStatus
    checks: tuple[RiskCheck, ...] = ()
    blocking_reasons: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        return self.status is RiskStatus.APPROVED


@dataclass(frozen=True)
class ExecutionIntent:
    decision_id: str
    symbol: str
    direction: str
    strategy: str
    option_contracts: tuple[str, ...]
    quantity: int
    max_loss_usd: float
    max_reward_usd: float
    created_at: datetime


@dataclass(frozen=True)
class OptionRiskInput:
    max_loss_per_contract_usd: float
    quantity: int
    dte: int | None
    bid: float
    ask: float
    open_interest: int | None
    volume: int | None
    market_data_fresh: bool


@dataclass(frozen=True)
class PortfolioRiskInput:
    daily_loss_usd: float
    total_options_exposure_usd: float
    symbol_exposure_usd: float
    open_positions: int
    duplicate_symbol: bool


@dataclass(frozen=True)
class Phase4Decision:
    decision_id: str
    symbol: str
    direction: str
    conviction: float
    evidence: EvidenceDecision
    risk: RiskDecision | None
    final_status: FinalStatus
    reasons: tuple[str, ...] = ()
    execution_intent: ExecutionIntent | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)