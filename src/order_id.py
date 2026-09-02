"""
Client Order ID Generator for OptionPilot.

Format: OP-YYYYMMDD-SYMBOL-TYPE-SEQ
Examples:
  OP-20260824-AAPL-STOCK-0001
  OP-20260824-AAPL-CALL-0001
  OP-20260824-SPY-PUT-0002
  OP-20260824-TSLA-SPREAD-0001
"""

from datetime import datetime
from typing import Literal

OrderType = Literal["STOCK", "CALL", "PUT", "SPREAD", "BRACKET", "OCO", "OTO"]


def generate_client_order_id(
    symbol: str,
    order_type: OrderType,
    date: datetime | None = None,
    sequence: int | None = None,
) -> str:
    """
    Generate a structured client order ID.
    
    Args:
        symbol: Trading symbol (e.g., AAPL, SPY)
        order_type: Type of order (STOCK, CALL, PUT, SPREAD, BRACKET, OCO, OTO)
        date: Date for the ID (defaults to now UTC)
        sequence: Optional explicit sequence number (for testing/replay)
    
    Returns:
        Formatted client order ID string
    """
    if date is None:
        date = datetime.utcnow()

    date_str = date.strftime("%Y%m%d")
    symbol_clean = symbol.upper().replace("/", "-").replace(":", "-")
    type_clean = order_type.upper()

    if sequence is not None:
        seq_str = f"{sequence:04d}"
    else:
        seq_str = "0000"  # Placeholder, will be replaced by order_store

    return f"OP-{date_str}-{symbol_clean}-{type_clean}-{seq_str}"


def parse_client_order_id(client_order_id: str) -> dict | None:
    """
    Parse a client order ID into its components.
    
    Returns dict with: prefix, date, symbol, order_type, sequence
    Returns None if format is invalid.
    """
    try:
        parts = client_order_id.split("-")
        if len(parts) != 5 or parts[0] != "OP":
            return None

        return {
            "prefix": parts[0],
            "date": parts[1],  # YYYYMMDD
            "symbol": parts[2],
            "order_type": parts[3],
            "sequence": int(parts[4]),
        }
    except (ValueError, IndexError):
        return None


def get_date_from_client_order_id(client_order_id: str) -> str | None:
    """Extract date string (YYYYMMDD) from client order ID."""
    parsed = parse_client_order_id(client_order_id)
    return parsed["date"] if parsed else None


def get_symbol_from_client_order_id(client_order_id: str) -> str | None:
    """Extract symbol from client order ID."""
    parsed = parse_client_order_id(client_order_id)
    return parsed["symbol"] if parsed else None


def get_order_type_from_client_order_id(client_order_id: str) -> str | None:
    """Extract order type from client order ID."""
    parsed = parse_client_order_id(client_order_id)
    return parsed["order_type"] if parsed else None


def is_valid_client_order_id(client_order_id: str) -> bool:
    """Validate client order ID format."""
    return parse_client_order_id(client_order_id) is not None
