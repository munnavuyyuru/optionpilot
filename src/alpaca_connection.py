from __future__ import annotations

import os
from functools import lru_cache

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

from safety import assert_paper_environment

load_dotenv()


def _credentials() -> tuple[str, str]:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key:
        raise RuntimeError("ALPACA_API_KEY is not configured")

    if not secret_key:
        raise RuntimeError("ALPACA_SECRET_KEY is not configured")

    return api_key, secret_key


@lru_cache(maxsize=1)
def create_client() -> TradingClient:
    """
    Create the single Alpaca TradingClient used by OptionPilot.

    Phase 2 is paper-only.
    """
    assert_paper_environment()

    api_key, secret_key = _credentials()

    return TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True,
    )


@lru_cache(maxsize=1)
def create_stock_data_client() -> StockHistoricalDataClient:
    """
    Create the single stock market-data client.
    """
    assert_paper_environment()

    api_key, secret_key = _credentials()

    return StockHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key,
    )


@lru_cache(maxsize=1)
def create_option_data_client() -> OptionHistoricalDataClient:
    """
    Create the single options market-data client.
    """
    assert_paper_environment()

    api_key, secret_key = _credentials()

    return OptionHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key,
    )


def main() -> None:
    client = create_client()
    account = client.get_account()

    print("Connected to Alpaca paper trading")
    print(f"Account ID: {account.id}")
    print(f"Status: {account.status}")
    print(f"Currency: {account.currency}")
    print(f"Buying Power: {account.buying_power}")
    print(f"Equity: {account.equity}")


if __name__ == "__main__":
    main()
