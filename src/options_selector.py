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