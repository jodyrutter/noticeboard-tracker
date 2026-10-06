from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import psycopg2
import pytest
from fastapi.testclient import TestClient

import auth
import main
from auth_models import User
from services import auth_service, trainee_service, plan_service, progress_service, notification_service


ROUTES = [
    ("GET", "/trainees", None, {"HR", "MANAGER"}, 200),
    ("GET", "/cohorts", None, {"HR", "MANAGER"}, 200),
    ("GET", "/plans", None, {"MANAGER", "TRAINEE"}, 200),
    ("GET", "/progress/trainee/7", None, {"MANAGER"}, 200),
    ("GET", "/notifications/8", None, {"TRAINEE"}, 200),
    ("GET", "/dashboard", None, {"MANAGER"}, 200),
    ("GET", "/dashboard/trainees", None, {"MANAGER"}, 200),
    ("POST", "/trainees", {"user_id": 8, "cohort_id": 1, "status": "ACTIVE", "onboarding_date": "2026-10-06"}, {"HR"}, 201),
    ("PATCH", "/trainees/7", {"status": "ACTIVE", "cohort_id": 2}, {"HR"}, 200),
    ("POST", "/cohorts", {"name": "Fall", "start_date": "2026-10-06", "end_date": None}, {"HR"}, 201),
    ("POST", "/plans", {"title": "SQL", "description": None, "due_date": None}, {"MANAGER"}, 201),
    ("POST", "/plans/3/assign/trainee/7", None, {"MANAGER"}, 201),
    ("POST", "/plans/3/assign/cohort/1", None, {"MANAGER"}, 201),
    ("POST", "/progress", {"trainee_id": 7, "plan_id": 3, "status": "IN_PROGRESS", "comments": None}, {"TRAINEE"}, 201),
    ("POST", "/notifications", {"user_id": 8, "message": "Reminder"}, set(), 403),
    ("PUT", "/notifications/12/read", None, {"TRAINEE"}, 200),
]


@pytest.fixture(autouse=True)
def block_database(monkeypatch):
    monkeypatch.setattr(psycopg2, "connect", Mock(side_effect=AssertionError("No live DB in tests")))


@pytest.fixture
def user():
    user = User(user_id=8, name="Test", email="test@example.com", role="TRAINEE")
    main.app.dependency_overrides[auth.get_current_user] = lambda: user
    yield user
    main.app.dependency_overrides.pop(auth.get_current_user, None)


@pytest.fixture
def client():
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def services(monkeypatch):
    names = [
        "get_all_trainees", "get_all_cohorts", "get_all_plans", "get_assigned_plans",
        "get_progress_by_trainee", "get_notifications_by_user", "get_dashboard_summary",
        "get_trainee_overview", "create_trainee", "update_trainee", "create_cohort",
        "create_plan", "assign_plan_to_trainee", "assign_plan_to_cohort",
        "create_progress_report", "mark_notification_as_read",
    ]
    mocks = {name: Mock(return_value=12) for name in names}
    for name, mock in mocks.items():
        monkeypatch.setattr(main, name, mock)
    return mocks


@pytest.mark.parametrize("method,path,body,roles,success", ROUTES)
@pytest.mark.parametrize("role", ["HR", "MANAGER", "TRAINEE"])
def test_role_matrix(client, user, services, method, path, body, roles, success, role):
    user.role = role
    response = client.request(method, path, json=body)
    assert response.status_code == (success if role in roles else 403), response.text
    if role not in roles:
        for service in services.values():
            service.assert_not_called()


@pytest.mark.parametrize("method,path,body,roles,success", ROUTES)
def test_anonymous_cannot_access_business_routes(client, services, method, path, body, roles, success):
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    for service in services.values():
        service.assert_not_called()


def test_matrix_covers_every_business_route(client):
    operations = {(method, path) for method, path, *_ in ROUTES}
    actual = {(method.upper(), path) for path, methods in client.get("/openapi.json").json()["paths"].items()
              if not path.startswith("/api/") for method in methods}
    normalized = {(method, path.replace("/trainees/7", "/trainees/{trainee_id}")
                   .replace("/trainee/7", "/trainee/{trainee_id}")
                   .replace("/notifications/8", "/notifications/{user_id}")
                   .replace("/notifications/12", "/notifications/{notification_id}")
                   .replace("/plans/3", "/plans/{plan_id}")
                   .replace("/cohort/1", "/cohort/{cohort_id}")) for method, path in operations}
    assert normalized == actual


def test_trainee_plans_are_filtered(client, user, services):
    services["get_assigned_plans"].return_value = []
    assert client.get("/plans").json() == []
    services["get_assigned_plans"].assert_called_once_with(8)
    services["get_all_plans"].assert_not_called()


def test_plan_author_cannot_be_spoofed(client, user, services):
    user.role = "MANAGER"
    body = {"title": "SQL", "description": None, "due_date": None}
    assert client.post("/plans", json={**body, "created_by": 99}).status_code == 422
    services["create_plan"].assert_not_called()
    assert client.post("/plans", json=body).status_code == 201
    services["create_plan"].assert_called_once_with("SQL", None, None, 8)


def test_progress_checks_owner_and_assignment(client, user, services):
    services["create_progress_report"].return_value = None
    body = {"trainee_id": 99, "plan_id": 3, "status": "IN_PROGRESS", "comments": None}
    assert client.post("/progress", json=body).status_code == 403
    services["create_progress_report"].assert_called_once_with(99, 3, "IN_PROGRESS", None, 8)


def test_notifications_are_recipient_only(client, user, services):
    assert client.get("/notifications/99").status_code == 403
    services["get_notifications_by_user"].assert_not_called()
    services["mark_notification_as_read"].return_value = False
    assert client.put("/notifications/12/read").status_code == 404
    services["mark_notification_as_read"].assert_called_once_with(12, 8)


@pytest.mark.parametrize("body", [{}, {"role": "HR"}, {"user_id": 99}, {"status": None}, {"onboarding_date": None}])
def test_hr_update_rejects_invalid_fields(client, user, services, body):
    user.role = "HR"
    assert client.patch("/trainees/7", json=body).status_code == 422
    services["update_trainee"].assert_not_called()


@pytest.mark.parametrize("changes", [{"cohort_id": 2}, {"cohort_id": None}, {"status": "ACTIVE"}])
def test_hr_partial_update(client, user, services, changes):
    user.role = "HR"
    assert client.patch("/trainees/7", json=changes).status_code == 200
    services["update_trainee"].assert_called_once_with(7, changes)


def test_hr_update_not_found(client, user, services):
    user.role = "HR"
    services["update_trainee"].return_value = None
    assert client.patch("/trainees/7", json={"cohort_id": 2}).status_code == 404


def test_hr_cannot_enroll_staff_user(client, user, services):
    user.role = "HR"
    services["create_trainee"].side_effect = trainee_service.InvalidTraineeUserError
    body = {"user_id": 99, "cohort_id": 1, "status": "ACTIVE", "onboarding_date": "2026-10-06"}
    assert client.post("/trainees", json=body).status_code == 400


def test_unknown_cohort_is_client_error(client, user, services):
    user.role = "HR"
    services["update_trainee"].side_effect = trainee_service.InvalidCohortError
    assert client.patch("/trainees/7", json={"cohort_id": 999}).status_code == 400


def test_real_token_uses_current_db_role_and_revocation(client, monkeypatch, services):
    monkeypatch.setenv("NOTICEBOARD_JWT_SECRET", "permissions-test-only-secret-1234567890")
    manager = User(user_id=8, name="Test", email="test@example.com", role="MANAGER")
    token = auth.encode_session_token(manager, "test-session", datetime.now(timezone.utc))
    current = Mock(return_value=manager)
    monkeypatch.setattr(auth_service, "session_user", current)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/dashboard", headers=headers).status_code == 200
    current.return_value = manager.model_copy(update={"role": "TRAINEE"})
    assert client.get("/dashboard", headers=headers).status_code == 403
    current.return_value = None
    assert client.get("/dashboard", headers=headers).status_code == 401
    services["get_dashboard_summary"].assert_called_once()


@pytest.fixture
def db(monkeypatch):
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    for module in (trainee_service, plan_service, progress_service, notification_service):
        monkeypatch.setattr(module, "get_connection", lambda: connection)
    return connection, cursor


def test_progress_sql_checks_owner_and_assignment_in_same_write(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    assert progress_service.create_progress_report(7, 3, "ACTIVE", None, 8) is None
    sql, params = cursor.execute.call_args.args
    assert "t.user_id = %s" in sql and "pa.trainee_id = t.id AND pa.plan_id = %s" in sql
    assert params == (3, "ACTIVE", None, 7, 8, 3)
    connection.close.assert_called_once()


def test_notification_sql_scopes_update_to_owner(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    assert notification_service.mark_notification_as_read(12, 8) is False
    sql, params = cursor.execute.call_args.args
    assert "WHERE id = %s AND user_id = %s" in sql
    assert params == (12, 8)
    connection.close.assert_called_once()


def test_assigned_plans_sql_is_user_scoped(db):
    _, cursor = db
    cursor.fetchall.return_value = []
    assert plan_service.get_assigned_plans(8) == []
    sql, params = cursor.execute.call_args.args
    assert "pa.plan_id = p.id AND t.user_id = %s" in sql
    assert params == (8,)


def test_enrollment_sql_requires_trainee_role(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    with pytest.raises(trainee_service.InvalidTraineeUserError):
        trainee_service.create_trainee(8, 1, "ACTIVE", "2026-10-06")
    assert "role = 'TRAINEE'" in cursor.execute.call_args.args[0]
    assert connection.__exit__.call_args.args[0] is trainee_service.InvalidTraineeUserError
    connection.close.assert_called_once()


def test_update_only_changes_supplied_fields(db):
    connection, cursor = db
    cursor.fetchone.return_value = (7,)
    assert trainee_service.update_trainee(7, {"cohort_id": None}) == 7
    assert cursor.execute.call_args.args[1] == (None, 7)
    connection.close.assert_called_once()
