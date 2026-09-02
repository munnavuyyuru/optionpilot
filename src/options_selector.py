from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from options_data import (
    OptionContractData,
    OptionSnapshotData,
)


@dataclass(frozen=True)
class OptionCandidate:
    contract: OptionContractData
    snapshot: OptionSnapshotData
    dte: int
    liquidity_score: float
    options_score: float
    reasons: tuple[str, ...]


def _dte(expiration: date) -> int:
    return (
        expiration - date.today()
    ).days


def _liquidity_score(
    contract: OptionContractData,
    snapshot: OptionSnapshotData,
    max_spread_pct: float,
    min_open_interest: int,
) -> float | None:
    spread_pct = snapshot.spread_pct

    if spread_pct is None:
        return None

    if spread_pct > max_spread_pct:
        return None

    if contract.open_interest < min_open_interest:
        return None

    spread_score = max(
        0.0,
        min(
            100.0,
            100.0
            * (
                1.0
                - spread_pct / max_spread_pct
            ),
        ),
    )

    oi_score = min(
        100.0,
        (
            contract.open_interest
            / min_open_interest
        )
        * 50.0,
    )

    return (
        spread_score * 0.70
        + oi_score * 0.30
    )


def select_candidates(
    direction: str,
    contracts: list[OptionContractData],
    chain: dict[str, OptionSnapshotData],
    min_dte: int,
    max_dte: int,
    min_open_interest: int,
    max_spread_pct: float,
) -> list[OptionCandidate]:
    if direction == "neutral":
        return []

    required_type = (
        "call"
        if direction == "bullish"
        else "put"
    )

    candidates: list[OptionCandidate] = []

    for contract in contracts:
        if contract.option_type != required_type:
            continue

        if not contract.tradable:
            continue

        dte = _dte(contract.expiration_date)

        if dte < min_dte or dte > max_dte:
            continue

        snapshot = chain.get(contract.symbol)

        if snapshot is None:
            continue

        liquidity = _liquidity_score(
            contract=contract,
            snapshot=snapshot,
            max_spread_pct=max_spread_pct,
            min_open_interest=min_open_interest,
        )

        if liquidity is None:
            continue

        delta_score = 50.0

        if snapshot.delta is not None:
            delta_score = min(
                100.0,
                abs(snapshot.delta) * 100.0,
            )

        iv_score = 50.0

        if snapshot.implied_volatility is not None:
            iv = snapshot.implied_volatility

            if iv <= 0.30:
                iv_score = 80.0
            elif iv <= 0.50:
                iv_score = 60.0
            else:
                iv_score = 30.0

        options_score = (
            liquidity * 0.50
            + delta_score * 0.30
            + iv_score * 0.20
        )

        candidates.append(
            OptionCandidate(
                contract=contract,
                snapshot=snapshot,
                dte=dte,
                liquidity_score=liquidity,
                options_score=options_score,
                reasons=(
                    f"direction={direction}",
                    f"DTE={dte}",
                    f"liquidity_score={liquidity:.2f}",
                    f"options_score={options_score:.2f}",
                ),
            )
        )

    candidates.sort(
        key=lambda candidate: candidate.options_score,
        reverse=True,
    )

    return candidates


def build_debit_spread(
    direction: str,
    long_contract: OptionContractData,
    chain: dict[str, OptionSnapshotData],
    width: float = 5.0,
) -> tuple[OptionContractData, OptionContractData] | None:
    """
    Build a debit spread from a long option contract.

    Bullish: long call at K, short call at K + width
    Bearish: long put at K, short put at K - width

    Returns (long_leg, short_leg) or None if short leg not found.
    """
    if direction == "bullish":
        required_type = "call"
        short_strike = long_contract.strike_price + width
    else:
        required_type = "put"
        short_strike = long_contract.strike_price - width

    # Find short leg with same expiry, different strike
    for symbol, contract in chain.items():
        parsed = _parse_contract_symbol(symbol)
        if not parsed:
            continue

        if (parsed["type"] == required_type
            and abs(parsed["strike"] - short_strike) < 0.01
            and parsed["expiry"] == long_contract.expiration_date):

            short_contract = OptionContractData(
                symbol=symbol,
                contract_id=contract.get("contract_id", ""),
                underlying_symbol=long_contract.underlying_symbol,
                expiration_date=long_contract.expiration_date,
                strike_price=parsed["strike"],
                option_type=required_type,
                tradable=True,
                open_interest=int(contract.get("open_interest", 0)),
            )
            return (long_contract, short_contract)

    return None


def _parse_contract_symbol(symbol: str) -> dict | None:
    """Parse OCC option symbol to extract type, strike, expiry."""
    import re
    match = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', symbol)
    if not match:
        return None

    underlying, date_str, opt_type, strike_str = match.groups()
    year = 2000 + int(date_str[:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    strike = int(strike_str) / 1000

    return {
        "underlying": underlying,
        "expiry": date(year, month, day),
        "type": "call" if opt_type == "C" else "put",
        "strike": strike,
    }