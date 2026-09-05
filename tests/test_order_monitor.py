from unittest.mock import MagicMock, patch
from order_monitor import OrderMonitor, FillResult
from alpaca.trading.enums import OrderStatus
import time


def test_wait_for_fill_success():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.status = OrderStatus.FILLED
    mock_order.filled_qty = 1
    mock_order.filled_avg_price = 4.20
    mock_order.filled_at = MagicMock()
    mock_order.filled_at.isoformat.return_value = "2024-01-01T12:00:00Z"
    mock_client.get_order_by_id.return_value = mock_order

    monitor = OrderMonitor(client=mock_client, poll_interval=0.01)
    result = monitor.wait_for_fill("ALP-001", timeout=5)

    assert result.status == "filled"
    assert result.filled_quantity == 1
    assert result.filled_avg_price == 4.20


def test_wait_for_fill_cancelled():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.status = OrderStatus.CANCELED
    mock_order.filled_qty = 0
    mock_client.get_order_by_id.return_value = mock_order

    monitor = OrderMonitor(client=mock_client, poll_interval=0.01)
    result = monitor.wait_for_fill("ALP-001", timeout=5)

    assert result.status == "canceled"
    assert result.filled_quantity == 0


def test_wait_for_fill_timeout():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.status = OrderStatus.NEW
    mock_client.get_order_by_id.return_value = mock_order

    monitor = OrderMonitor(client=mock_client, poll_interval=0.01)
    result = monitor.wait_for_fill("ALP-001", timeout=0.1)

    assert result.status == "TIMEOUT"
    assert result.filled_quantity == 0