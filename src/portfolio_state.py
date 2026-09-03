from __future__ import annotations

from datetime import datetime, timezone

from alpaca.trading.client import TradingClient

from alpaca_connection import create_client
from phase4_models import PortfolioRiskInput


def get_portfolio_state(
    trading_client: TradingClient | None = None,
) -> PortfolioRiskInput:
    if trading_client is None:
        trading_client = create_client()

    account = trading_client.get_account()
    positions = trading_client.get_all_positions()
    open_orders = trading_client.get_orders(status="open")

    # Daily P&L from today's filled orders
    today = datetime.now(timezone.utc).date()
    daily_loss_usd = 0.0
    total_exposure_usd = 0.0
    existing_symbols = set()
    existing_order_symbols = set()

    for pos in positions:
        symbol = pos.symbol
        existing_symbols.add(symbol)

        # Calculate position exposure (market value)
        try:
            market_value = float(pos.market_value or 0.0)
            total_exposure_usd += abs(market_value)
        except (ValueError, TypeError):
            pass

    for order in open_orders:
        existing_order_symbols.add(order.symbol)

    # Daily P&L from filled orders today
    filled_orders = trading_client.get_orders(status="filled", limit=500)
    for order in filled_orders:
        filled_at = order.filled_at
        if filled_at:
            fill_date = filled_at.date() if hasattr(filled_at, 'date') else None
            if fill_date == today:
                try:
                    filled_qty = float(order.filled_qty or 0)
                    filled_price = float(order.filled_avg_price or 0)
                    if order.side.value == "sell":
                        daily_loss_usd -= filled_qty * filled_price
                    else:
                        daily_loss_usd += filled_qty * filled_price
                except (ValueError, TypeError):
                    pass

    return PortfolioRiskInput(
        daily_loss_usd=daily_loss_usd,
        total_options_exposure_usd=total_exposure_usd,
        symbol_exposure_usd=0.0,  # Will be set per-symbol in pipeline
        open_positions=len(positions),
        duplicate_symbol=False,  # Will be set per-symbol in pipeline
    )


def get_symbol_exposure(
    trading_client: TradingClient,
    symbol: str,
) -> float:
    """Get current exposure for a specific symbol."""
    try:
        positions = trading_client.get_all_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return abs(float(pos.market_value or 0.0))
    except Exception:
        pass
    return 0.0


def check_duplicate_symbol(
    trading_client: TradingClient,
    symbol: str,
) -> bool:
    """Check if symbol already has position or open order."""
    existing_symbols = set()
    existing_order_symbols = set()

    try:
        positions = trading_client.get_all_positions()
        for pos in positions:
            existing_symbols.add(pos.symbol)
    except Exception:
        pass

    try:
        orders = trading_client.get_orders(status="open", limit=100)
        for order in orders:
            existing_order_symbols.add(order.symbol)
    except Exception:
        pass

    return symbol in existing_symbols or symbol in existing_order_symbols