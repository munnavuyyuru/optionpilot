from __future__ import annotations


def validate_total_options_exposure(
    current_exposure_usd: float,
    proposed_risk_usd: float,
    limit_usd: float,
) -> tuple[bool, float, str]:
    projected = current_exposure_usd + proposed_risk_usd

    if projected >= limit_usd:
        return (
            False,
            projected,
            (
                f"Projected total options exposure ${projected:.2f} "
                f"meets/exceeds limit ${limit_usd:.2f}."
            ),
        )

    return True, projected, "Total options exposure is within policy."


def validate_symbol_exposure(
    current_symbol_exposure_usd: float,
    proposed_risk_usd: float,
    limit_usd: float,
) -> tuple[bool, float, str]:
    projected = current_symbol_exposure_usd + proposed_risk_usd

    if projected >= limit_usd:
        return (
            False,
            projected,
            (
                f"Projected symbol exposure ${projected:.2f} "
                f"meets/exceeds limit ${limit_usd:.2f}."
            ),
        )

    return True, projected, "Symbol exposure is within policy."


def validate_open_positions(
    current_open_positions: int,
    will_open_new_position: bool,
    limit: int,
) -> tuple[bool, int, str]:
    projected = current_open_positions + (1 if will_open_new_position else 0)

    if projected >= limit:
        return (
            False,
            projected,
            (
                f"Projected open positions {projected} "
                f"meet/exceed limit {limit}."
            ),
        )

    return True, projected, "Open-position count is within policy."


def validate_daily_loss(
    realized_daily_loss_usd: float,
    max_daily_loss_usd: float,
) -> tuple[bool, float, str]:
    if realized_daily_loss_usd < 0:
        loss = abs(realized_daily_loss_usd)
    else:
        loss = 0.0

    if loss >= max_daily_loss_usd:
        return (
            False,
            loss,
            (
                f"Daily loss ${loss:.2f} has reached/exceeded "
                f"limit ${max_daily_loss_usd:.2f}."
            ),
        )

    return True, loss, "Daily loss is within policy."


def validate_duplicate_exposure(
    symbol: str,
    existing_symbols: set[str],
    existing_order_symbols: set[str],
) -> tuple[bool, str]:
    if symbol in existing_symbols:
        return (
            False,
            f"Existing position already exposes {symbol}.",
        )

    if symbol in existing_order_symbols:
        return (
            False,
            f"Existing open order already exposes {symbol}.",
        )

    return True, "No duplicate exposure detected."