from unittest.mock import MagicMock, patch
from recovery import ExecutionRecovery, RecoveryResult


def test_reconcile_no_pending():
    mock_client = MagicMock()
    mock_ledger = MagicMock()
    mock_ledger.load_pending_executions.return_value = []

    recovery = ExecutionRecovery()
    recovery.client = mock_client
    result = recovery.reconcile()

    assert result.reconciled
    assert result.actions_taken == ()
    assert result.discrepancies == ()


def test_reconcile_updates_status():
    mock_client = MagicMock()
    mock_ledger = MagicMock()

    mock_order = MagicMock()
    mock_order.status.value = "FILLED"
    mock_client.get_order_by_id.return_value = mock_order

    with patch.object(ExecutionRecovery, '_load_pending_executions') as mock_load:
        mock_load.return_value = [
            {"execution_id": "EXE-001", "alpaca_order_id": "ALP-001", "status": "SUBMITTED"}
        ]

        recovery = ExecutionRecovery()
        recovery.client = mock_client
        result = recovery.reconcile()

        assert "Updated" in " ".join(result.actions_taken)