from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from conviction_models import Direction


class ExecutionStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(StrEnum):
    DAY = "day"
    GTC = "gtc"
    OPG = "opg"
    CLS = "cls"
    IOC = "ioc"
    FOK = "fok"


@dataclass(frozen=True)
class OptionLeg:
    symbol: str
    side: OrderSide
    quantity: int
    ratio: int = 1


@dataclass(frozen=True)
class AlpacaOrderRequest:
    client_order_id: str
    symbol: str
    legs: tuple[OptionLeg, ...]
    order_type: OrderType
    limit_price: Decimal | None
    quantity: int
    time_in_force: TimeInForce
    order_class: str


@dataclass(frozen=True)
class ExecutionIntent:
    intent_id: str
    decision_id: str
    candidate_id: str
    symbol: str
    direction: str
    strategy: str
    legs: tuple[OptionLeg, ...]
    option_contracts: tuple[str, ...]
    quantity: int
    order_type: OrderType
    limit_price: Decimal
    max_loss_usd: float
    max_reward_usd: float
    created_at: datetime


@dataclass(frozen=True)
class AlpacaOrderRequest:
    client_order_id: str
    symbol: str
    legs: tuple[OptionLeg, ...]
    order_type: OrderType
    limit_price: Decimal | None
    quantity: int
    time_in_force: TimeInForce
    order_class: str


@dataclass(frozen=True)
class ExecutionRecord:
    execution_id: str
    intent_id: str
    decision_id: str
    candidate_id: str

    symbol: str
    strategy: str
    direction: str

    status: str

    requested_quantity: int
    filled_quantity: int

    requested_limit_price: Decimal | None
    average_fill_price: Decimal | None

    alpaca_order_id: str | None

    submitted_at: datetime | None
    filled_at: datetime | None
    verified_at: datetime | None

    error_code: str | None
    error_message: str | None

    paper: bool = True


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    intent_id: str
    decision_id: str
    status: str
    alpaca_order_id: str | None
    filled_quantity: int
    average_fill_price: Decimal | None
    filled_at: datetime | None
    verified: bool
    error_code: str | None
    error_message: str | None