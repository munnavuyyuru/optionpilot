"""
Alpaca Connection Module for OptionPilot.

Simple authenticated paper trading client with order placement and traceability.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
)

load_dotenv()

ORDERS_FILE = Path("orders.json")


def create_client() -> TradingClient:
    """Create authenticated paper trading client."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key:
        raise RuntimeError("ALPACA_API_KEY is not configured")
    if not secret_key:
        raise RuntimeError("ALPACA_SECRET_KEY is not configured")

    if os.getenv("ALPACA_PAPER_TRADE", "true").lower() != "true":
        raise RuntimeError("ALPACA_PAPER_TRADE must be true")

    return TradingClient(api_key=api_key, secret_key=secret_key, paper=True)


def _generate_client_order_id(symbol: str, order_type: str) -> str:
    """Generate structured client_order_id: OP-YYYYMMDD-SYMBOL-TYPE-SEQ"""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    symbol = symbol.upper().replace("/", "-").replace(":", "-")
    order_type = order_type.upper()
    
    # Find max sequence from existing orders
    max_seq = 0
    if ORDERS_FILE.exists():
        try:
            data = json.loads(ORDERS_FILE.read_text())
            for oid in data.get("orders", {}).keys():
                if oid.startswith(f"OP-{date_str}-{symbol}-{order_type}-"):
                    parts = oid.split("-")
                    if len(parts) >= 5:
                        try:
                            seq = int(parts[4])
                            max_seq = max(max_seq, seq)
                        except ValueError:
                            pass
        except Exception:
            pass
    
    return f"OP-{date_str}-{symbol}-{order_type}-{max_seq + 1:04d}"


def _save_order_record(record: dict) -> None:
    """Save order record to JSON file."""
    data = {"orders": {}, "counters": {}}
    if ORDERS_FILE.exists():
        try:
            data = json.loads(ORDERS_FILE.read_text())
        except Exception:
            pass
    
    data.setdefault("orders", {})
    data.setdefault("counters", {})
    data["orders"][record["client_order_id"]] = record
    
    # Atomic write
    tmp = ORDERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(ORDERS_FILE)


def _load_orders() -> dict:
    """Load all orders from JSON file."""
    if ORDERS_FILE.exists():
        try:
            return json.loads(ORDERS_FILE.read_text())
        except Exception:
            pass
    return {"orders": {}, "counters": {}}


def place_order(
    symbol: str,
    side: str,
    order_type: str = "market",
    qty: str = "1",
    limit_price: float | None = None,
    stop_price: float | None = None,
    time_in_force: TimeInForce = TimeInForce.DAY,
    order_class: OrderClass = OrderClass.SIMPLE,
    take_profit: float | None = None,
    stop_loss: float | None = None,
    client_order_id: str | None = None,
    metadata: dict | None = None,
    id_order_type: str = "STOCK",
    client: TradingClient | None = None,
) -> dict:
    """
    Place an order with auto-generated client_order_id and full traceability.
    
    Args:
        symbol: Trading symbol (e.g., AAPL)
        side: "buy" or "sell"
        order_type: "market", "limit", "stop", "stop_limit"
        qty: Quantity as string
        limit_price: Limit price for limit/stop_limit
        stop_price: Stop price for stop/stop_limit
        time_in_force: DAY, GTC, OPG, CLS, IOC, FOK
        order_class: SIMPLE, BRACKET, OCO, OTO
        take_profit: Take profit price (for bracket)
        stop_loss: Stop loss price (for bracket)
        client_order_id: Explicit ID (auto-generated if None)
        metadata: Traceability dict (ai_decision_id, risk_check_id, strategy, signal_id, notes)
        id_order_type: STOCK, CALL, PUT, SPREAD, BRACKET for ID generation
        client: Optional pre-created TradingClient
    
    Returns:
        Dict with client_order_id, alpaca_order_id, status, etc.
    """
    if client is None:
        client = create_client()
    
    # Generate client_order_id
    if client_order_id is None:
        client_order_id = _generate_client_order_id(symbol, id_order_type)
    
    # Build request
    side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    common = {
        "symbol": symbol,
        "side": side_enum,
        "qty": qty,
        "time_in_force": time_in_force,
        "order_class": order_class,
    }
    
    if order_type == "market":
        request = MarketOrderRequest(**common)
    elif order_type == "limit":
        if limit_price is None:
            raise ValueError("limit_price required for limit orders")
        request = LimitOrderRequest(**common, limit_price=limit_price)
    elif order_type == "stop":
        if stop_price is None:
            raise ValueError("stop_price required for stop orders")
        request = StopOrderRequest(**common, stop_price=stop_price)
    elif order_type == "stop_limit":
        if limit_price is None or stop_price is None:
            raise ValueError("limit_price and stop_price required for stop_limit")
        request = StopLimitOrderRequest(**common, limit_price=limit_price, stop_price=stop_price)
    else:
        raise ValueError(f"Unknown order_type: {order_type}")
    
    # Add bracket params
    if order_class == OrderClass.BRACKET:
        if take_profit:
            request.take_profit = {"limit_price": take_profit}
        if stop_loss:
            request.stop_loss = {"stop_price": stop_loss}
    
    request.client_order_id = client_order_id
    
    # Submit to Alpaca
    alpaca_order = client.submit_order(request)
    
    # Save record
    record = {
        "client_order_id": client_order_id,
        "alpaca_order_id": alpaca_order.id,
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "qty": qty,
        "status": alpaca_order.status.value,
        "filled_price": alpaca_order.filled_avg_price,
        "filled_qty": str(alpaca_order.filled_qty or 0),
        "created_at": alpaca_order.created_at.isoformat() if alpaca_order.created_at else None,
        "filled_at": alpaca_order.filled_at.isoformat() if alpaca_order.filled_at else None,
        "metadata": metadata or {},
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    
    _save_order_record(record)
    
    return {
        "client_order_id": client_order_id,
        "alpaca_order_id": alpaca_order.id,
        "status": alpaca_order.status.value,
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "qty": qty,
        "filled_qty": str(alpaca_order.filled_qty or 0),
        "filled_avg_price": alpaca_order.filled_avg_price,
    }


def refresh_order(client_order_id: str, client: TradingClient | None = None) -> dict | None:
    """Fetch latest status from Alpaca and update local store."""
    if client is None:
        client = create_client()
    
    data = _load_orders()
    record = data.get("orders", {}).get(client_order_id)
    if not record:
        return None
    
    alpaca_id = record.get("alpaca_order_id")
    if not alpaca_id:
        return None
    
    try:
        alpaca_order = client.get_order_by_id(alpaca_id)
        record["status"] = alpaca_order.status.value
        record["filled_price"] = alpaca_order.filled_avg_price
        record["filled_qty"] = str(alpaca_order.filled_qty or 0)
        record["filled_at"] = alpaca_order.filled_at.isoformat() if alpaca_order.filled_at else None
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_order_record(record)
        return record
    except Exception:
        return None


def get_order(client_order_id: str) -> dict | None:
    """Get order by client_order_id."""
    data = _load_orders()
    return data.get("orders", {}).get(client_order_id)


def list_orders(symbol: str | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
    """List orders with optional filters."""
    data = _load_orders()
    results = []
    for record in data.get("orders", {}).values():
        if symbol and record.get("symbol") != symbol.upper():
            continue
        if status and record.get("status") != status:
            continue
        results.append(record)
    
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results[:limit]


def get_history(symbol: str | None = None, days_back: int = 30) -> list[dict]:
    """Get orders formatted for model learning with P&L."""
    data = _load_orders()
    cutoff = datetime.now(timezone.utc)
    results = []
    
    for record in data.get("orders", {}).values():
        if symbol and record.get("symbol") != symbol.upper():
            continue
        
        try:
            created = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
            if (cutoff - created).days > days_back:
                continue
        except Exception:
            pass
        
        # Calculate P&L
        pnl = None
        if record.get("filled_price") and record.get("filled_qty"):
            try:
                pnl = float(record["filled_price"]) * float(record["filled_qty"])
                if record.get("side") == "sell":
                    pnl = -pnl
            except Exception:
                pass
        
        results.append({
            "client_order_id": record["client_order_id"],
            "symbol": record.get("symbol"),
            "side": record.get("side"),
            "type": record.get("type"),
            "qty": record.get("qty"),
            "status": record.get("status"),
            "filled_price": record.get("filled_price"),
            "filled_qty": record.get("filled_qty"),
            "pnl": pnl,
            "created_at": record.get("created_at"),
            "filled_at": record.get("filled_at"),
            "metadata": record.get("metadata", {}),
        })
    
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results


def sync_from_alpaca(client: TradingClient | None = None) -> int:
    """Sync orders placed outside this system (e.g., via Alpaca CLI)."""
    if client is None:
        client = create_client()
    
    alpaca_orders = client.get_orders()
    data = _load_orders()
    synced = 0
    
    for order in alpaca_orders:
        alpaca_id = order.id
        if any(r.get("alpaca_order_id") == alpaca_id for r in data.get("orders", {}).values()):
            continue
        
        symbol = order.symbol
        order_type = order.order_class.value.upper() if order.order_class else "STOCK"
        if order_type not in ["STOCK", "CALL", "PUT", "SPREAD", "BRACKET", "OCO", "OTO"]:
            order_type = "STOCK"
        
        try:
            created_dt = datetime.fromisoformat(order.created_at.replace("Z", "+00:00"))
        except Exception:
            created_dt = datetime.now(timezone.utc)
        
        client_order_id = _generate_client_order_id(symbol, order_type)
        
        record = {
            "client_order_id": client_order_id,
            "alpaca_order_id": alpaca_id,
            "symbol": symbol,
            "side": order.side.value,
            "type": order.order_type.value,
            "qty": str(order.qty),
            "status": order.status.value,
            "filled_price": order.filled_avg_price,
            "filled_qty": str(order.filled_qty or 0),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None,
            "metadata": {"synced": True},
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        
        _save_order_record(record)
        synced += 1
    
    return synced


def get_account(client: TradingClient | None = None) -> Any:
    """Get account info."""
    if client is None:
        client = create_client()
    return client.get_account()


if __name__ == "__main__":
    client = create_client()
    account = get_account(client)
    print(f"Account: {account.id} | Status: {account.status} | Equity: {account.equity} | BP: {account.buying_power}")