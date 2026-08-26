import os


def assert_paper_environment() -> None:
    environment = os.getenv("ENVIRONMENT", "").lower()
    paper_trade = os.getenv("ALPACA_PAPER_TRADE", "").lower()

    if environment != "paper":
        raise RuntimeError(
            "SAFETY STOP: ENVIRONMENT must be 'paper'."
        )

    if paper_trade != "true":
        raise RuntimeError(
            "SAFETY STOP: ALPACA_PAPER_TRADE must be 'true'."
        )
