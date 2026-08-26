#!/usr/bin/env python3
"""
OptionPilot - Alpaca Environment Verification Script

Verifies all Alpaca connectivity and data access for paper trading.
Collects all results and reports at the end.
"""

import os
import sys
from typing import NamedTuple

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, OptionChainRequest


class CheckResult(NamedTuple):
    name: str
    passed: bool
    message: str = ""


def load_environment() -> None:
    """Load environment variables from .env file."""
    load_dotenv()


def check_environment() -> CheckResult:
    """[1] Verify ENVIRONMENT=paper and ALPACA_PAPER_TRADE=true."""
    env = os.getenv("ENVIRONMENT", "").lower()
    paper = os.getenv("ALPACA_PAPER_TRADE", "").lower()

    if env != "paper":
        return CheckResult("Environment", False, f"ENVIRONMENT='{env}' (expected 'paper')")
    if paper != "true":
        return CheckResult("Paper trading enabled", False, f"ALPACA_PAPER_TRADE='{paper}' (expected 'true')")

    return CheckResult("Environment", True, "ENVIRONMENT=paper, ALPACA_PAPER_TRADE=true")


def check_credentials() -> CheckResult:
    """[2] Verify API credentials exist."""
    api_key = os.getenv("ALPACA_API_KEY", "")
    secret_key = os.getenv("ALPACA_SECRET_KEY", "")

    if not api_key:
        return CheckResult("API authentication", False, "ALPACA_API_KEY not set")
    if not secret_key:
        return CheckResult("API authentication", False, "ALPACA_SECRET_KEY not set")
    if api_key == "your_paper_api_key_here":
        return CheckResult("API authentication", False, "ALPACA_API_KEY is placeholder")
    if secret_key == "your_paper_secret_key_here":
        return CheckResult("API authentication", False, "ALPACA_SECRET_KEY is placeholder")

    return CheckResult("API authentication", True, f"API key: {api_key[:8]}...")


def check_paper_endpoint() -> CheckResult:
    """[3] Verify paper trading endpoint configured."""
    base_url = os.getenv("ALPACA_API_BASE_URL", "")

    if "paper-api.alpaca.markets" not in base_url:
        return CheckResult("Paper endpoint", False, f"ALPACA_API_BASE_URL='{base_url}' (expected paper-api.alpaca.markets)")

    return CheckResult("Paper endpoint", True, base_url)


def create_trading_client() -> TradingClient:
    """Create authenticated paper trading client."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return TradingClient(api_key=api_key, secret_key=secret_key, paper=True)


def create_data_client() -> StockHistoricalDataClient:
    """Create market data client."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)


def create_option_data_client() -> OptionHistoricalDataClient:
    """Create options data client."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return OptionHistoricalDataClient(api_key=api_key, secret_key=secret_key)


def check_account(client: TradingClient) -> CheckResult:
    """[4] Verify account is active and accessible."""
    try:
        account = client.get_account()
        if account.status.value != "ACTIVE":
            return CheckResult("Account active", False, f"Account status: {account.status.value}")
        return CheckResult("Account active", True, f"Account {account.id}, status={account.status.value}, equity={account.equity}")
    except Exception as e:
        return CheckResult("Account active", False, str(e))


def check_account_data(client: TradingClient) -> CheckResult:
    """[4b] Verify we can read account data fields."""
    try:
        account = client.get_account()
        required_fields = ["id", "status", "currency", "buying_power", "equity", "cash"]
        for field in required_fields:
            if not hasattr(account, field) or getattr(account, field) is None:
                return CheckResult("Account data", False, f"Missing field: {field}")
        return CheckResult("Account data", True, f"Currency={account.currency}, BuyingPower={account.buying_power}, Equity={account.equity}, Cash={account.cash}")
    except Exception as e:
        return CheckResult("Account data", False, str(e))


def check_clock(client: TradingClient) -> CheckResult:
    """[5] Verify market clock accessible."""
    try:
        clock = client.get_clock()
        status = "OPEN" if clock.is_open else "CLOSED"
        return CheckResult("Market clock", True, f"Market {status}, next_open={clock.next_open}, next_close={clock.next_close}")
    except Exception as e:
        return CheckResult("Market clock", False, str(e))


def check_aapl_asset(data_client: StockHistoricalDataClient) -> CheckResult:
    """[6] Verify AAPL asset is tradable."""
    try:
        # Use get_asset via trading client for asset info
        # For data client, we check via latest trade
        request = StockLatestTradeRequest(symbol_or_symbols="AAPL")
        trade = data_client.get_stock_latest_trade(request)
        if "AAPL" not in trade or not trade["AAPL"]:
            return CheckResult("AAPL asset", False, "No trade data for AAPL")
        price = trade["AAPL"].price
        return CheckResult("AAPL asset", True, f"AAPL latest trade: ${price}")
    except Exception as e:
        return CheckResult("AAPL asset", False, str(e))


def check_market_data(data_client: StockHistoricalDataClient) -> CheckResult:
    """[7] Verify market data accessible for AAPL."""
    try:
        request = StockLatestTradeRequest(symbol_or_symbols="AAPL")
        trade = data_client.get_stock_latest_trade(request)
        if "AAPL" not in trade:
            return CheckResult("AAPL market data", False, "No trade data returned")
        t = trade["AAPL"]
        return CheckResult("AAPL market data", True, f"Price=${t.price}, Size={t.size}, Time={t.timestamp}")
    except Exception as e:
        return CheckResult("AAPL market data", False, str(e))


def check_options_data(option_client: OptionHistoricalDataClient) -> CheckResult:
    """[8] Verify options data accessible for AAPL."""
    try:
        request = OptionChainRequest(underlying_symbol="AAPL")
        response = option_client.get_option_chain(request)
        if not response or not isinstance(response, dict):
            return CheckResult("Options data", False, "No option contracts returned (empty or invalid response)")
        # Response is a flat dict: {symbol: OptionSnapshot, ...}
        contract_symbols = list(response.keys())
        if not contract_symbols:
            return CheckResult("Options data", False, "No AAPL option contracts in response")
        # Get first contract details from symbol (format: AAPL260826C00205000)
        first_symbol = contract_symbols[0]
        first_contract = response[first_symbol]
        # Parse symbol for strike/type: AAPL + YYMMDD + C/P + strike*1000
        # e.g., AAPL260826C00205000 -> exp=2026-08-26, type=Call, strike=205.00
        symbol = first_contract.symbol
        exp_str = symbol[4:10]  # YYMMDD
        opt_type = "Call" if symbol[10] == 'C' else "Put"
        strike_str = symbol[11:17]  # 6 digits, strike * 1000
        strike = int(strike_str) / 1000
        return CheckResult("Options data", True, f"Contracts: {len(contract_symbols)}, First: {symbol}, Exp=20{exp_str[:2]}-{exp_str[2:4]}-{exp_str[4:6]}, Type={opt_type}, Strike={strike}")
    except Exception as e:
        return CheckResult("Options data", False, str(e))


def run_verification() -> list[CheckResult]:
    """Run all verification checks and collect results."""
    results = []

    # [1] Environment
    results.append(check_environment())

    # [2] Credentials
    results.append(check_credentials())

    # [3] Paper endpoint
    results.append(check_paper_endpoint())

    # Initialize clients for API checks
    try:
        trading_client = create_trading_client()
        data_client = create_data_client()
        option_client = create_option_data_client()
    except Exception as e:
        results.append(CheckResult("Client initialization", False, str(e)))
        return results

    # [4] Account
    results.append(check_account(trading_client))
    results.append(check_account_data(trading_client))

    # [5] Clock
    results.append(check_clock(trading_client))

    # [6] AAPL Asset
    results.append(check_aapl_asset(data_client))

    # [7] Market Data
    results.append(check_market_data(data_client))

    # [8] Options Data
    results.append(check_options_data(option_client))

    return results


def print_results(results: list[CheckResult]) -> int:
    """Print formatted results and return exit code."""
    width = 44
    print("=" * width)
    print("OptionPilot - Alpaca Verification")
    print("=" * width)
    print()

    all_passed = True
    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        print(f"{status} {r.name}")
        if r.message:
            print(f"       {r.message}")
        if not r.passed:
            all_passed = False

    print()
    print("=" * width)
    if all_passed:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")
    print("=" * width)

    return 0 if all_passed else 1


def main() -> int:
    load_environment()
    results = run_verification()
    return print_results(results)


if __name__ == "__main__":
    sys.exit(main())