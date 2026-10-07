from unittest.mock import MagicMock
import pytest
from services import promotion_service


@pytest.fixture
def db(monkeypatch):
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(promotion_service, "get_connection", lambda: connection)
    return connection, cursor


def test_promotion_list_groups_and_queries_assignments(db):
    connection, cursor = db
    rows = [{"user_id":1,"role":"HR"},{"user_id":2,"role":"MANAGER"},{"user_id":3,"role":"TRAINEE"}]
    cursor.fetchall.return_value = rows
    assert promotion_service.get_promotion_users() == {"staff": rows[:2], "eligible": rows[2:]}
    query = cursor.execute.call_args.args[0]
    assert "JOIN plan_assignments" in query and "NOT EXISTS" in query
    assert "t.user_id = u.id" in query
    assert "password" not in query
    connection.close.assert_called_once()


def test_promotion_checks_assignments_again_on_write(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [{"id":3}, None]
    with pytest.raises(promotion_service.AssignedTrainingError):
        promotion_service.update_user_role(3, "HR")
    query, args = cursor.execute.call_args.args
    assert "NOT EXISTS" in query and "JOIN plan_assignments" in query
    assert args == ("HR",3)
    assert connection.__exit__.call_args.args[0] is promotion_service.AssignedTrainingError


def test_role_update_returns_public_fields(db):
    connection, cursor = db
    result = {"user_id":3,"role":"HR","email":"user@example.com","name":"User"}
    cursor.fetchone.side_effect = [{"id":3},result]
    assert promotion_service.update_user_role(3,"HR") == result


def test_role_update_missing_user(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    assert promotion_service.update_user_role(3,"HR") is None
    assert cursor.execute.call_count == 1
