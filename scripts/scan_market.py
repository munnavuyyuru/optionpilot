from __future__ import annotations

import argparse

from market_data import get_underlying_market_data
from options_data import (
    get_option_chain,
    get_option_contracts,
)
from options_selector import select_candidates
from scoring import rank_candidates
from signals import calculate_market_signal
from risk import validate_candidate


UNIVERSE = (
    "SPY",
    "QQQ",
    "NVDA",
    "AAPL",
    "MSFT",
    "TSLA",
)


def scan_symbol(symbol: str) -> None:
    symbol = symbol.upper()

    print()
    print("=" * 70)
    print(f"OPTIONPILOT PHASE 2 — {symbol}")
    print("=" * 70)

    market = get_underlying_market_data(
        symbol=symbol,
        lookback_days=120,
    )

    print(
        f"Underlying: ${market.latest_price:.2f}"
    )
    print(
        f"Historical bars: {len(market.bars)}"
    )

    signal = calculate_market_signal(
        symbol=symbol,
        bars=list(market.bars),
    )

    print(
        f"Direction: {signal.direction.upper()}"
    )

    if signal.score is None:
        print("Signal score: INCOMPLETE")
    else:
        print(
            f"Signal score: {signal.score:.2f}"
        )

    print()
    print("Signal components:")

    for component in signal.components:
        if component.score is None:
            print(
                f"  {component.name}: UNAVAILABLE"
            )
        else:
            print(
                f"  {component.name}: "
                f"{component.score:.2f}"
            )

    if signal.direction == "neutral":
        print()
        print("DECISION: NO TRADE")
        return

    contracts = get_option_contracts(
        symbol=symbol,
        underlying_price=market.latest_price,
        min_dte=21,
        max_dte=45,
        strike_min_pct=0.90,
        strike_max_pct=1.10,
        max_contracts=500,
    )

    chain = get_option_chain(
        symbol=symbol,
        underlying_price=market.latest_price,
        min_dte=21,
        max_dte=45,
        strike_min_pct=0.90,
        strike_max_pct=1.10,
    )

    candidates = select_candidates(
        direction=signal.direction,
        contracts=contracts,
        chain=chain,
        min_dte=21,
        max_dte=45,
        min_open_interest=100,
        max_spread_pct=0.10,
    )

    print()
    print(
        f"Filtered option candidates: "
        f"{len(candidates)}"
    )

    scored = rank_candidates(
        market_signal=signal,
        candidates=candidates,
        threshold=75.0,
    )

    for index, candidate in enumerate(
        scored[:5],
        start=1,
    ):
        option = candidate.option
        contract = option.contract
        snapshot = option.snapshot

        print()
        print(
            f"#{index} {contract.symbol}"
        )
        print(
            f"  Type: {contract.option_type.upper()}"
        )
        print(
            f"  Strike: ${contract.strike_price:.2f}"
        )
        print(
            f"  Expiration: "
            f"{contract.expiration_date}"
        )
        print(
            f"  DTE: {option.dte}"
        )
        print(
            f"  Bid: ${snapshot.bid:.2f}"
        )
        print(
            f"  Ask: ${snapshot.ask:.2f}"
        )

        if snapshot.spread_pct is not None:
            print(
                f"  Spread: "
                f"{snapshot.spread_pct:.2%}"
            )

        print(
            f"  Open interest: "
            f"{contract.open_interest}"
        )

        if snapshot.implied_volatility is not None:
            print(
                f"  IV: "
                f"{snapshot.implied_volatility:.2%}"
            )

        if snapshot.delta is not None:
            print(
                f"  Delta: "
                f"{snapshot.delta:.4f}"
            )

        print(
            f"  Market score: "
            f"{candidate.market_score:.2f}"
        )

        print(
            f"  Options score: "
            f"{candidate.options_score:.2f}"
        )

        print(
            f"  Total score: "
            f"{candidate.total_score:.2f}"
        )

        print(
            f"  Candidate: "
            f"{'YES' if candidate.eligible else 'NO'}"
        )

        risk = validate_candidate(
            candidate=option,
            max_debit_usd=1000.0,
            max_contracts=1,
        )

        print(
            f"  Risk: "
            f"{'APPROVED' if risk.approved else 'REJECTED'}"
        )

        for failure in risk.failures:
            print(
                f"    ! {failure}"
            )

    print()
    print("ORDER SUBMISSION: DISABLED")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbol",
        choices=UNIVERSE,
        help="Scan one symbol.",
    )

    args = parser.parse_args()

    if args.symbol:
        scan_symbol(args.symbol)
        return

    for symbol in UNIVERSE:
        try:
            scan_symbol(symbol)
        except Exception as exc:
            print(
                f"[ERROR] {symbol}: "
                f"{type(exc).__name__}: {exc}"
            )


if __name__ == "__main__":
    main()