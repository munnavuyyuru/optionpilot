from unittest.mock import MagicMock, patch
from recovery import ExecutionRecovery, RecoveryResult


def test_reconcile_no_pending():
    mock_client = MagicMock()
    mock_ledger = MagicMock()
    mock_ledger.load_pending_executions.return_value = []

    recovery = ExecutionRecovery(client=mock_client, ledger=mock_ledger)
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

    mock_ledger.load_pending_executions.return_value = [
        {"execution_id": "EXE-001", "alpaca_order_id": "ALP-001", "status": "SUBMITTED"}
    ]

    recovery = ExecutionRecovery(client=mock_client, ledger=mock_ledger)
    result = recovery.reconcile()

    assert "Updated" in " ".join(result.actions_taken)