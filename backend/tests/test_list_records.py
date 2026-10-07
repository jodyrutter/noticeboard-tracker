from unittest.mock import MagicMock

import pytest
from psycopg2.extras import RealDictCursor

from services import cohort_service, notification_service, plan_service, progress_service, trainee_service


@pytest.mark.parametrize("module,function,args", [
    (cohort_service, "get_all_cohorts", ()),
    (trainee_service, "get_all_trainees", ()),
    (plan_service, "get_all_plans", ()),
    (plan_service, "get_assigned_plans", (8,)),
    (notification_service, "get_notifications_by_user", (8,)),
    (progress_service, "get_progress_by_trainee", (7,)),
    (progress_service, "get_progress_by_plan", (3,)),
])
def test_list_readers_request_named_records(monkeypatch, module, function, args):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = {"id": 3}
    cursor.fetchall.return_value = [{"id": 3, "name": "Example"}]
    monkeypatch.setattr(module, "get_connection", lambda: connection)

    rows = getattr(module, function)(*args)

    connection.cursor.assert_called_once_with(cursor_factory=RealDictCursor)
    assert rows == [{"id": 3, "name": "Example"}]
    connection.close.assert_called_once()
