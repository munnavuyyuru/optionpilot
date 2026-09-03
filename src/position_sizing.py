from __future__ import annotations


def validate_position_risk(
    max_loss_per_contract_usd: float,
    quantity: int,
    max_position_risk_usd: float,
) -> tuple[bool, float, str]:
    if max_loss_per_contract_usd < 0:
        return False, 0.0, "Max loss cannot be negative."

    if quantity <= 0:
        return False, 0.0, "Quantity must be positive."

    total_risk = max_loss_per_contract_usd * quantity

    if total_risk > max_position_risk_usd:
        return (
            False,
            total_risk,
            (
                f"Position risk ${total_risk:.2f} exceeds "
                f"limit ${max_position_risk_usd:.2f}."
            ),
        )

    return True, total_risk, "Position risk is within policy."