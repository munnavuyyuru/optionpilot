from __future__ import annotations

import os


def assert_paper_environment() -> None:
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    paper_trade = os.getenv("ALPACA_PAPER_TRADE", "").strip().lower()

    if environment != "paper":
        raise RuntimeError(
            "SAFETY STOP: ENVIRONMENT must be 'paper'."
        )

    if paper_trade != "true":
        raise RuntimeError(
            "SAFETY STOP: ALPACA_PAPER_TRADE must be 'true'."
        )


def assert_phase2_execution_disabled() -> None:
    """
    Phase 2 is analysis-only.

    There is intentionally no autonomous order path here.
    """
    raise RuntimeError(
        "PHASE 2 SAFETY STOP: order execution is disabled. "
        "Phase 2 only generates and evaluates candidates."
    )
