from unittest.mock import MagicMock
from fill_verifier import FillVerifier, VerificationResult
from alpaca.trading.enums import OrderStatus


def test_verify_success():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.filled_qty = 1
    mock_order.filled_avg_price = 4.20
    mock_client.get_order_by_id.return_value = mock_order

    mock_position = MagicMock()
    mock_position.symbol = "QQQ"
    mock_client.get_open_position.return_value = mock_position

    verifier = FillVerifier(client=mock_client)
    result = verifier.verify("ALP-001", "QQQ", 1, 420.0)

    assert result.verified
    assert "fill_quantity" in result.checks
    assert "position_exists" in result.checks


def test_verify_wrong_quantity():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.filled_qty = 2  # Wrong quantity
    mock_client.get_order_by_id.return_value = mock_order

    verifier = FillVerifier(client=mock_client)
    result = verifier.verify("ALP-001", "QQQ", 1, 420.0)

    assert not result.verified
    assert any("quantity" in d for d in result.discrepancies)


def test_verify_missing_position():
    mock_client = MagicMock()
    mock_order = MagicMock()
    mock_order.filled_qty = 1
    mock_client.get_order_by_id.return_value = mock_order

    mock_client.get_open_position.side_effect = Exception("No position")

    verifier = FillVerifier(client=mock_client)
    result = verifier.verify("ALP-001", "QQQ", 1, 420.0)

    assert not result.verified
    assert any("Position check failed" in d for d in result.discrepancies)