from __future__ import annotations

from dataclasses import dataclass

from options_selector import OptionCandidate


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reasons: tuple[str, ...]
    failures: tuple[str, ...]


def validate_candidate(
    candidate: OptionCandidate,
    max_debit_usd: float,
    max_contracts: int,
) -> RiskDecision:
    failures: list[str] = []
    reasons: list[str] = []

    snapshot = candidate.snapshot

    midpoint = snapshot.midpoint

    if midpoint is None:
        failures.append(
            "No valid bid/ask midpoint."
        )
    else:
        estimated_debit = midpoint * 100.0

        if estimated_debit > max_debit_usd:
            failures.append(
                "Estimated single-contract debit "
                "exceeds configured risk limit."
            )
        else:
            reasons.append(
                "Estimated debit is within risk limit."
            )

    if max_contracts < 1:
        failures.append(
            "max_contracts must be at least 1."
        )

    if candidate.contract.open_interest <= 0:
        failures.append(
            "Open interest is zero."
        )
    else:
        reasons.append(
            "Open interest is positive."
        )

    if snapshot.spread_pct is None:
        failures.append(
            "Bid/ask spread cannot be calculated."
        )
    else:
        reasons.append(
            f"Spread={snapshot.spread_pct:.2%}"
        )

    return RiskDecision(
        approved=not failures,
        reasons=tuple(reasons),
        failures=tuple(failures),
    )
