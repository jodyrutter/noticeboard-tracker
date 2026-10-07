from unittest.mock import MagicMock
from services import dashboard_service


def test_dashboard_includes_not_started_reports(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.fetchone.side_effect = [(10,), (8,), (2,), (4,), (3,), (1,), (2,), (5,)]
    monkeypatch.setattr(dashboard_service, "get_connection", lambda: connection)
    result = dashboard_service.get_dashboard_summary()
    assert result["not_started_reports"] == 5
    assert result["missing_reports"] == 2
    assert "status = 'NOT_STARTED'" in cursor.execute.call_args.args[0]
    connection.close.assert_called_once()
