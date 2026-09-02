from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestQuoteRequest,
)
from alpaca.data.timeframe import TimeFrame

from alpaca_connection import create_stock_data_client


@dataclass(frozen=True)
class PriceBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class UnderlyingMarketData:
    symbol: str
    latest_price: float
    bars: tuple[PriceBar, ...]


def get_daily_bars(
    symbol: str,
    lookback_days: int = 120,
) -> list[PriceBar]:
    client = create_stock_data_client()

    end = datetime.now(UTC)
    start = end - timedelta(days=lookback_days)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        start=start,
        end=end,
        timeframe=TimeFrame.Day,
    )

    response = client.get_stock_bars(request)
    bars = response[symbol]

    return [
        PriceBar(
            timestamp=bar.timestamp,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=int(bar.volume),
        )
        for bar in bars
    ]


def get_latest_price(symbol: str) -> float:
    client = create_stock_data_client()

    request = StockLatestQuoteRequest(
        symbol_or_symbols=symbol,
    )

    quotes = client.get_stock_latest_quote(request)
    quote = quotes[symbol]

    bid = float(quote.bid_price or 0.0)
    ask = float(quote.ask_price or 0.0)

    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0

    if ask > 0:
        return ask

    if bid > 0:
        return bid

    raise RuntimeError(
        f"No usable latest quote for {symbol}"
    )


def get_underlying_market_data(
    symbol: str,
    lookback_days: int = 120,
) -> UnderlyingMarketData:
    bars = get_daily_bars(
        symbol=symbol,
        lookback_days=lookback_days,
    )

    if not bars:
        raise RuntimeError(
            f"No historical bars returned for {symbol}"
        )

    return UnderlyingMarketData(
        symbol=symbol,
        latest_price=get_latest_price(symbol),
        bars=tuple(bars),
    )
