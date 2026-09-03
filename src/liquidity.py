from __future__ import annotations


def bid_ask_spread_pct(
    bid: float,
    ask: float,
) -> float | None:
    if bid <= 0 or ask <= 0:
        return None

    midpoint = (bid + ask) / 2.0

    if midpoint <= 0:
        return None

    return (ask - bid) / midpoint


def validate_bid_ask(
    bid: float,
    ask: float,
    max_spread_pct: float,
) -> tuple[bool, float | None, str]:
    spread = bid_ask_spread_pct(bid, ask)

    if spread is None:
        return False, None, "Bid/ask data is missing or invalid."

    if spread > max_spread_pct:
        return (
            False,
            spread,
            (
                f"Bid/ask spread {spread:.2%} exceeds "
                f"limit {max_spread_pct:.2%}."
            ),
        )

    return True, spread, "Bid/ask spread is within policy."


def validate_liquidity(
    open_interest: int | None,
    volume: int | None,
    min_open_interest: int,
    min_volume: int,
) -> tuple[bool, str]:
    if open_interest is None:
        return False, "Open interest is missing."

    if volume is None:
        return False, "Volume is missing."

    if open_interest < min_open_interest:
        return (
            False,
            (
                f"Open interest {open_interest} is below "
                f"minimum {min_open_interest}."
            ),
        )

    if volume < min_volume:
        return (
            False,
            (
                f"Volume {volume} is below "
                f"minimum {min_volume}."
            ),
        )

    return True, "Liquidity is within policy."


def validate_dte(
    dte: int | None,
    min_dte: int,
    max_dte: int,
) -> tuple[bool, str]:
    if dte is None:
        return False, "DTE is missing."

    if dte < min_dte:
        return (
            False,
            f"DTE {dte} is below minimum {min_dte}.",
        )

    if dte > max_dte:
        return (
            False,
            f"DTE {dte} is above maximum {max_dte}.",
        )

    return True, "DTE is within policy."