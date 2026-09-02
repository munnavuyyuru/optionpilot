from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from alpaca.data.requests import OptionChainRequest
from alpaca.trading.requests import GetOptionContractsRequest

from alpaca_connection import (
    create_client,
    create_option_data_client,
)


@dataclass(frozen=True)
class OptionContractData:
    symbol: str
    contract_id: str
    underlying_symbol: str
    expiration_date: date
    strike_price: float
    option_type: str
    tradable: bool
    open_interest: int


@dataclass(frozen=True)
class OptionSnapshotData:
    symbol: str

    bid: float
    ask: float
    last: float | None

    implied_volatility: float | None

    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None

    @property
    def midpoint(self) -> float | None:
        if self.bid <= 0 or self.ask <= 0:
            return None

        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float | None:
        midpoint = self.midpoint

        if midpoint is None:
            return None

        return self.ask - self.bid

    @property
    def spread_pct(self) -> float | None:
        midpoint = self.midpoint
        spread = self.spread

        if midpoint is None or spread is None:
            return None

        return spread / midpoint


def get_option_contracts(
    symbol: str,
    underlying_price: float,
    min_dte: int,
    max_dte: int,
    strike_min_pct: float,
    strike_max_pct: float,
    max_contracts: int,
) -> list[OptionContractData]:
    client = create_client()

    today = date.today()

    request = GetOptionContractsRequest(
        underlying_symbols=[symbol],
        expiration_date_gte=(
            today + timedelta(days=min_dte)
        ),
        expiration_date_lte=(
            today + timedelta(days=max_dte)
        ),
        strike_price_gte=str(
            underlying_price * strike_min_pct
        ),
        strike_price_lte=str(
            underlying_price * strike_max_pct
        ),
        limit=max_contracts,
    )

    response = client.get_option_contracts(request)

    contracts = response.option_contracts or []

    result: list[OptionContractData] = []

    for contract in contracts:
        contract_type = str(contract.type).lower()

        if "call" in contract_type:
            option_type = "call"
        elif "put" in contract_type:
            option_type = "put"
        else:
            continue

        result.append(
            OptionContractData(
                symbol=contract.symbol,
                contract_id=str(contract.id),
                underlying_symbol=contract.underlying_symbol,
                expiration_date=contract.expiration_date,
                strike_price=float(contract.strike_price),
                option_type=option_type,
                tradable=bool(contract.tradable),
                open_interest=int(
                    contract.open_interest or 0
                ),
            )
        )

    return result


def get_option_chain(
    symbol: str,
    underlying_price: float,
    min_dte: int,
    max_dte: int,
    strike_min_pct: float,
    strike_max_pct: float,
) -> dict[str, OptionSnapshotData]:
    client = create_option_data_client()

    today = date.today()

    request = OptionChainRequest(
        underlying_symbol=symbol,
        strike_price_gte=(
            underlying_price * strike_min_pct
        ),
        strike_price_lte=(
            underlying_price * strike_max_pct
        ),
        expiration_date_gte=(
            today + timedelta(days=min_dte)
        ),
        expiration_date_lte=(
            today + timedelta(days=max_dte)
        ),
    )

    snapshots = client.get_option_chain(request)

    result: dict[str, OptionSnapshotData] = {}

    for symbol_key, snapshot in snapshots.items():
        quote = snapshot.latest_quote
        trade = snapshot.latest_trade
        greeks = snapshot.greeks

        if quote is None:
            continue

        result[symbol_key] = OptionSnapshotData(
            symbol=symbol_key,
            bid=float(quote.bid_price or 0.0),
            ask=float(quote.ask_price or 0.0),
            last=(
                float(trade.price)
                if trade is not None
                and trade.price is not None
                else None
            ),
            implied_volatility=(
                float(snapshot.implied_volatility)
                if snapshot.implied_volatility is not None
                else None
            ),
            delta=(
                float(greeks.delta)
                if greeks is not None
                and greeks.delta is not None
                else None
            ),
            gamma=(
                float(greeks.gamma)
                if greeks is not None
                and greeks.gamma is not None
                else None
            ),
            theta=(
                float(greeks.theta)
                if greeks is not None
                and greeks.theta is not None
                else None
            ),
            vega=(
                float(greeks.vega)
                if greeks is not None
                and greeks.vega is not None
                else None
            ),
        )

    return result
