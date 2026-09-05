from unittest.mock import MagicMock, patch
from alpaca_executor import AlpacaExecutor
from alpaca.trading.enums import OrderStatus


def test_submit_order_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.id = "ALP-001"
    mock_client.submit_order.return_value = mock_response

    executor = AlpacaExecutor(client=mock_client)
    mock_request = MagicMock()

    result = executor.submit_order(mock_request)

    assert result.success
    assert result.alpaca_order_id == "ALP-001"
    assert result.error_code is None


def test_submit_order_failure():
    mock_client = MagicMock()
    mock_client.submit_order.side_effect = Exception("API Error")

    executor = AlpacaExecutor(client=mock_client)
    mock_request = MagicMock()

    result = executor.submit_order(mock_request)

    assert not result.success
    assert result.error_code == "SUBMISSION_FAILED"
    assert "API Error" in result.error_message


def test_cancel_order():
    mock_client = MagicMock()
    executor = AlpacaExecutor(client=mock_client)

    result = executor.cancel_order("ALP-001")

    assert result
    mock_client.cancel_order_by_id.assert_called_once_with("ALP-001")


def test_get_position():
    mock_client = MagicMock()
    mock_position = MagicMock()
    mock_position.symbol = "QQQ"
    mock_client.get_open_position.return_value = mock_position

    executor = AlpacaExecutor(client=mock_client)
    position = executor.get_position("QQQ")

    assert position == mock_position