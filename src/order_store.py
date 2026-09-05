"""
Order Store - Persistent JSON storage for order traceability.

Stores orders in orders.json with atomic writes and file locking.
Maintains per-(date, symbol, order_type) sequence counters.
"""

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False

from order_id import generate_client_order_id

DEFAULT_STORE_PATH = Path("orders.json")


class OrderStore:
    """
    Thread-safe order persistence with atomic writes.
    
    File structure:
    {
        "version": 1,
        "orders": {
            "OP-20260824-AAPL-STOCK-0001": { ...order data... }
        },
        "counters": {
            "2026-08-24": {
                "AAPL": {"STOCK": 1, "CALL": 0}
            }
        }
    }
    """

    def __init__(self, path: Path | str = DEFAULT_STORE_PATH):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._file_lock = None
        self._data: dict[str, Any] = {"version": 1, "orders": {}, "counters": {}}
        self._load()

    def _get_file_lock(self):
        """Get or create file lock for cross-process safety."""
        if HAS_PORTALOCKER and self._file_lock is None:
            lock_path = self.path.with_suffix(".lock")
            self._file_lock = portalocker.Lock(str(lock_path), timeout=10)
        return self._file_lock

    def _load(self) -> None:
        """Load orders from JSON file."""
        with self._lock:
            if self.path.exists():
                try:
                    with open(self.path) as f:
                        if HAS_PORTALOCKER:
                            lock = self._get_file_lock()
                            with lock:
                                self._data = json.load(f)
                        else:
                            self._data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    self._data = {"version": 1, "orders": {}, "counters": {}}
            else:
                self._data = {"version": 1, "orders": {}, "counters": {}}

            # Ensure required keys exist
            self._data.setdefault("version", 1)
            self._data.setdefault("orders", {})
            self._data.setdefault("counters", {})

    def _save(self) -> None:
        """Atomically save orders to JSON file."""
        with self._lock:
            # Write to temp file then rename for atomicity
            temp_path = self.path.with_suffix(".tmp")
            try:
                if HAS_PORTALOCKER:
                    lock = self._get_file_lock()
                    with lock:
                        with open(temp_path, "w") as f:
                            json.dump(self._data, f, indent=2, default=str)
                        os.replace(temp_path, self.path)
                else:
                    with open(temp_path, "w") as f:
                        json.dump(self._data, f, indent=2, default=str)
                    os.replace(temp_path, self.path)
            except OSError:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                raise

    def _get_date_key(self, dt: datetime | None = None) -> str:
        """Get date key in YYYY-MM-DD format."""
        if dt is None:
            dt = datetime.now(UTC)
        return dt.strftime("%Y-%m-%d")

    def _increment_counter(
        self,
        symbol: str,
        order_type: str,
        date: datetime | None = None
    ) -> int:
        """Increment and return the sequence counter for (date, symbol, order_type)."""
        date_key = self._get_date_key(date)
        symbol_upper = symbol.upper()
        type_upper = order_type.upper()

        if date_key not in self._data["counters"]:
            self._data["counters"][date_key] = {}
        if symbol_upper not in self._data["counters"][date_key]:
            self._data["counters"][date_key][symbol_upper] = {}
        if type_upper not in self._data["counters"][date_key][symbol_upper]:
            self._data["counters"][date_key][symbol_upper][type_upper] = 0

        self._data["counters"][date_key][symbol_upper][type_upper] += 1
        return self._data["counters"][date_key][symbol_upper][type_upper]

    def generate_and_reserve_id(
        self,
        symbol: str,
        order_type: str,
        date: datetime | None = None
    ) -> str:
        """
        Generate a client_order_id and reserve the sequence number.
        This ensures uniqueness even under concurrent access.
        """
        sequence = self._increment_counter(symbol, order_type, date)
        return generate_client_order_id(symbol, order_type, date, sequence)

    def save_order(
        self,
        client_order_id: str,
        alpaca_order: dict | Any,
        metadata: dict | None = None,
    ) -> dict:
        """
        Save order with full traceability.
        
        Args:
            client_order_id: Our structured client order ID
            alpaca_order: Alpaca order object (dict or object with attributes)
            metadata: Optional traceability metadata (ai_decision_id, risk_check_id, strategy, signal_id)
        
        Returns:
            The saved order record
        """
        # Convert Alpaca order to dict if needed
        if hasattr(alpaca_order, "__dict__"):
            order_dict = {
                k: v for k, v in alpaca_order.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(alpaca_order, dict):
            order_dict = alpaca_order
        else:
            order_dict = {"raw": str(alpaca_order)}

        # Extract key fields
        alpaca_order_id = order_dict.get("id") or order_dict.get("order_id")
        symbol = order_dict.get("symbol")
        side = order_dict.get("side")
        order_type = order_dict.get("order_type") or order_dict.get("type")
        qty = str(order_dict.get("qty", "0"))
        status = order_dict.get("status")
        filled_price = order_dict.get("filled_avg_price")
        filled_qty = order_dict.get("filled_qty", "0")
        created_at = order_dict.get("created_at") or order_dict.get("submitted_at")
        filled_at = order_dict.get("filled_at")

        record = {
            "client_order_id": client_order_id,
            "alpaca_order_id": alpaca_order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "qty": qty,
            "status": status,
            "filled_price": filled_price,
            "filled_qty": str(filled_qty),
            "created_at": created_at,
            "filled_at": filled_at,
            "metadata": metadata or {},
            "raw_alpaca_response": order_dict,
            "stored_at": datetime.now(UTC).isoformat(),
        }

        with self._lock:
            self._data["orders"][client_order_id] = record
            self._save()

        return record

    def update_order_status(
        self,
        client_order_id: str,
        status: str,
        filled_price: float | None = None,
        filled_qty: str | None = None,
        filled_at: str | None = None,
    ) -> bool:
        """Update order status after fill/cancel/reject."""
        with self._lock:
            if client_order_id not in self._data["orders"]:
                return False

            record = self._data["orders"][client_order_id]
            record["status"] = status
            if filled_price is not None:
                record["filled_price"] = filled_price
            if filled_qty is not None:
                record["filled_qty"] = filled_qty
            if filled_at is not None:
                record["filled_at"] = filled_at
            record["updated_at"] = datetime.now(UTC).isoformat()

            self._save()
            return True

    def get_order(self, client_order_id: str) -> dict | None:
        """Get order by client_order_id."""
        with self._lock:
            return self._data["orders"].get(client_order_id)

    def get_order_by_alpaca_id(self, alpaca_order_id: str) -> dict | None:
        """Reverse lookup: find order by Alpaca order ID."""
        with self._lock:
            for record in self._data["orders"].values():
                if record.get("alpaca_order_id") == alpaca_order_id:
                    return record
            return None

    def list_orders(
        self,
        symbol: str | None = None,
        date: str | None = None,  # YYYY-MM-DD
        status: str | None = None,
        order_type: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List orders with optional filters."""
        with self._lock:
            results = []
            for record in self._data["orders"].values():
                if symbol and record.get("symbol") != symbol.upper():
                    continue
                if date and record.get("client_order_id", "").split("-")[1] != date.replace("-", ""):
                    continue
                if status and record.get("status") != status:
                    continue
                if order_type and record.get("type") != order_type:
                    continue
                results.append(record)

            # Sort by created_at descending (newest first)
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results[:limit]

    def get_orders_for_model_learning(
        self,
        symbol: str | None = None,
        days_back: int = 30,
    ) -> list[dict]:
        """
        Get orders formatted for model training/analysis.
        Includes P&L, timing, and outcome data.
        """
        with self._lock:
            cutoff_date = datetime.now(UTC)
            results = []

            for record in self._data["orders"].values():
                if symbol and record.get("symbol") != symbol.upper():
                    continue

                # Filter by date
                created_str = record.get("created_at", "")
                try:
                    created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    if (cutoff_date - created_dt).days > days_back:
                        continue
                except (ValueError, AttributeError):
                    pass

                # Compute P&L if filled
                pnl = None
                if record.get("filled_price") and record.get("filled_qty"):
                    try:
                        fill_price = float(record["filled_price"])
                        fill_qty = float(record["filled_qty"])
                        side_mult = 1 if record.get("side") == "buy" else -1
                        pnl = side_mult * fill_price * fill_qty
                    except (ValueError, TypeError):
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

    def get_counter(self, symbol: str, order_type: str, date: datetime | None = None) -> int:
        """Get current counter value without incrementing."""
        date_key = self._get_date_key(date)
        symbol_upper = symbol.upper()
        type_upper = order_type.upper()

        return self._data["counters"].get(date_key, {}).get(symbol_upper, {}).get(type_upper, 0)

    def sync_from_alpaca(self, alpaca_orders: list[dict]) -> int:
        """
        Sync orders from Alpaca API (for orders placed outside this system).
        Returns number of new orders synced.
        """
        synced = 0
        with self._lock:
            for order in alpaca_orders:
                alpaca_id = order.get("id")
                if not alpaca_id:
                    continue

                # Check if already tracked
                if self.get_order_by_alpaca_id(alpaca_id):
                    continue

                # Generate a client_order_id for historical order
                symbol = order.get("symbol", "UNKNOWN")
                order_type = order.get("order_class", "STOCK").upper()
                if order_type not in ["STOCK", "CALL", "PUT", "SPREAD", "BRACKET", "OCO", "OTO"]:
                    order_type = "STOCK"

                # Use order creation date for counter
                created_str = order.get("created_at") or order.get("submitted_at")
                try:
                    created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    created_dt = datetime.now(UTC)

                client_order_id = self.generate_and_reserve_id(symbol, order_type, created_dt)

                # Save with minimal metadata
                self.save_order(client_order_id, order, metadata={"synced": True})
                synced += 1

            if synced > 0:
                self._save()

        return synced

    def export_for_training(self, filepath: Path | str) -> int:
        """Export orders in format suitable for ML training."""
        data = self.get_orders_for_model_learning()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return len(data)


# Global instance
_store: OrderStore | None = None


def get_order_store(path: Path | str = DEFAULT_STORE_PATH) -> OrderStore:
    """Get or create the global order store instance."""
    global _store
    if _store is None:
        _store = OrderStore(path)
    return _store
