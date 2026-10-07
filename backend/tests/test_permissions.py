from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import psycopg2
import pytest
from fastapi.testclient import TestClient

import auth
import main
from auth_models import User
from services import auth_service, trainee_service, plan_service, progress_service, notification_service, cohort_service


ROUTES = [
    ("GET", "/dashboard/tracking", None, {"MANAGER"}, 200),
    ("GET", "/notifications/8/unread-count", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("GET", "/plans/3/assignments", None, {"MANAGER"}, 200),
    ("PATCH", "/plans/3/assignments", {"add": [7], "remove": []}, {"MANAGER"}, 200),
    ("PATCH", "/cohorts/1/members", {"add": [7], "remove": []}, {"HR"}, 200),
    ("GET", "/users/promotion", None, {"HR"}, 200),
    ("PATCH", "/users/9/role", {"role": "MANAGER"}, {"HR"}, 200),
    ("GET", "/users/unenrolled", None, {"HR"}, 200),
    ("GET", "/trainees/7", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("PUT", "/trainees/7", {"status": "ACTIVE", "cohort_id": 2, "onboarding_date": "2026-10-06"}, {"HR"}, 200),
    ("GET", "/cohorts/1", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("GET", "/plans/3", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("PUT", "/plans/3", {"title": "SQL", "description": None, "due_date": None}, {"MANAGER"}, 200),
    ("DELETE", "/plans/3", None, {"MANAGER"}, 204),
    ("GET", "/progress/plan/3", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("GET", "/trainees", None, {"HR", "MANAGER"}, 200),
    ("GET", "/cohorts", None, {"HR", "MANAGER"}, 200),
    ("GET", "/plans", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("GET", "/progress/trainee/7", None, {"HR", "MANAGER", "TRAINEE"}, 200),
    ("GET", "/notifications/8", None, {"HR", "MANAGER", "TRAINEE"}, 200),
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
    ("PUT", "/notifications/12/read", None, {"HR", "MANAGER", "TRAINEE"}, 200),
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
        "get_tracking", "get_unread_count", "get_plan_assignments", "update_plan_assignments", "update_cohort_members", "get_promotion_users", "update_user_role", "get_unenrolled_users", "get_own_trainee", "get_own_cohort", "get_own_progress",
        "get_trainee", "get_cohort", "get_plan", "update_plan", "delete_plan", "get_progress_by_plan",
        "get_all_trainees", "get_all_cohorts", "get_all_plans", "get_assigned_plans",
        "get_progress_by_trainee", "get_notifications_by_user", "get_dashboard_summary",
        "get_trainee_overview", "create_trainee", "update_trainee", "create_cohort",
        "create_plan", "assign_plan_to_trainee", "assign_plan_to_cohort",
        "create_progress_report", "mark_notification_as_read",
    ]
    mocks = {name: Mock(return_value=12) for name in names}
    mocks["get_own_trainee"].return_value = {"id": 7, "user_id": 8, "cohort_id": 1}
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
                   .replace("/users/9/role", "/users/{user_id}/role")
                   .replace("/notifications/8", "/notifications/{user_id}")
                   .replace("/notifications/12", "/notifications/{notification_id}")
                   .replace("/plans/3", "/plans/{plan_id}")
                   .replace("/cohort/1", "/cohort/{cohort_id}")
                   .replace("/cohorts/1", "/cohorts/{cohort_id}")
                   .replace("/plan/3", "/plan/{plan_id}")) for method, path in operations}
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
    services["get_own_trainee"].return_value = {"id": 99}
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
    for module in (trainee_service, plan_service, progress_service, notification_service, cohort_service):
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


@pytest.mark.parametrize("path,service", [("/trainees/7", "get_trainee"), ("/cohorts/1", "get_cohort"), ("/plans/3", "get_plan"), ("/progress/plan/3", "get_progress_by_plan")])
def test_new_reads_not_found(client, user, services, path, service):
    user.role = "MANAGER"
    services[service].return_value = None
    assert client.get(path).status_code == 404


def test_plan_detail_ownership(client, user, services):
    services["get_plan"].return_value = None
    assert client.get("/plans/3").status_code == 404
    services["get_plan"].assert_called_once_with(3, 8)
    services["get_plan"].reset_mock()
    user.role = "MANAGER"
    services["get_plan"].return_value = {"id": 3, "title": "SQL"}
    assert client.get("/plans/3").json() == {"id": 3, "title": "SQL"}
    services["get_plan"].assert_called_once_with(3, None)


def test_progress_plan_empty(client, user, services):
    user.role = "MANAGER"
    services["get_progress_by_plan"].return_value = []
    assert client.get("/progress/plan/3").json() == []
    services["get_progress_by_plan"].assert_called_once_with(3)


@pytest.mark.parametrize("path,role,body,service", [
    ("/trainees/7", "HR", {"cohort_id": None, "status": "ACTIVE", "onboarding_date": "2026-10-06"}, "update_trainee"),
    ("/plans/3", "MANAGER", {"title": "SQL", "description": None, "due_date": None}, "update_plan"),
])
def test_put_requires_all_fields_and_rejects_identity_changes(client, user, services, path, role, body, service):
    user.role = role
    for field in body:
        assert client.put(path, json={key: value for key, value in body.items() if key != field}).status_code == 422
    for field in ("user_id", "created_by", "role"):
        assert client.put(path, json={**body, field: 99}).status_code == 422
    services[service].assert_not_called()
    services[service].return_value = None
    assert client.put(path, json=body).status_code == 404


def test_put_plan_preserves_creator(client, user, services):
    user.role = "MANAGER"
    body = {"title": "Updated", "description": None, "due_date": None}
    assert client.put("/plans/3", json=body).json() == {"id": 12, "message": "Plan updated"}
    services["update_plan"].assert_called_once_with(3, "Updated", None, None)


def test_delete_responses(client, user, services):
    user.role = "MANAGER"
    response = client.delete("/plans/3")
    assert response.status_code == 204 and response.content == b""
    services["delete_plan"].return_value = False
    assert client.delete("/plans/3").status_code == 404
    services["delete_plan"].side_effect = plan_service.PlanInUseError
    assert client.delete("/plans/3").status_code == 409


@pytest.mark.parametrize("module,function", [(trainee_service, "get_trainee"), (cohort_service, "get_cohort")])
def test_detail_storage_returns_named_fields(db, module, function):
    connection, cursor = db
    cursor.fetchone.return_value = {"id": 7}
    assert getattr(module, function)(7) == {"id": 7}
    assert cursor.execute.call_args.args[1] == (7,)
    connection.close.assert_called_once()


def test_plan_detail_sql_filters_assignment(db):
    connection, cursor = db
    cursor.fetchone.return_value = None
    assert plan_service.get_plan(3, 8) is None
    sql, params = cursor.execute.call_args.args
    assert "pa.plan_id = p.id AND t.user_id = %s" in sql
    assert params == (3, 8)
    connection.close.assert_called_once()


def test_plan_edit_sql_changes_only_editable_fields(db):
    connection, cursor = db
    cursor.fetchone.return_value = (3,)
    assert plan_service.update_plan(3, "SQL", None, None) == 3
    sql, params = cursor.execute.call_args_list[1].args
    assert "created_by" not in sql
    assert params == ("SQL", None, None, 3, "SQL", None, None)
    connection.close.assert_called_once()


@pytest.mark.parametrize("state", ["missing", "referenced", "unused"])
def test_delete_storage_preserves_referenced_plans(db, state):
    connection, cursor = db
    cursor.fetchone.side_effect = [None] if state == "missing" else [(3,), (state == "referenced",)]
    if state == "referenced":
        with pytest.raises(plan_service.PlanInUseError):
            plan_service.delete_plan(3)
        assert connection.__exit__.call_args.args[0] is plan_service.PlanInUseError
    else:
        assert plan_service.delete_plan(3) is (state == "unused")
    queries = [call.args[0] for call in cursor.execute.call_args_list]
    assert "FOR UPDATE" in queries[0]
    assert any("DELETE FROM plans" in query for query in queries) is (state == "unused")
    if state != "missing":
        assert "plan_assignments" in queries[1] and "progress_reports" in queries[1]
    connection.close.assert_called_once()


def test_delete_foreign_key_conflict_rolls_back(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(3,), (False,)]
    cursor.execute.side_effect = [None, None, psycopg2.errors.ForeignKeyViolation()]
    with pytest.raises(plan_service.PlanInUseError):
        plan_service.delete_plan(3)
    assert connection.__exit__.call_args.args[0] is psycopg2.errors.ForeignKeyViolation
    connection.close.assert_called_once()


@pytest.mark.parametrize("exists", [True, False])
def test_progress_by_plan_storage(db, exists):
    connection, cursor = db
    cursor.fetchone.return_value = (3,) if exists else None
    cursor.fetchall.return_value = []
    assert progress_service.get_progress_by_plan(3) == ([] if exists else None)
    if exists:
        assert "WHERE plan_id = %s" in cursor.execute.call_args.args[0]
        assert cursor.execute.call_args.args[1] == (3,)
    else:
        cursor.fetchall.assert_not_called()
    connection.close.assert_called_once()


def test_no_new_me_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(path.startswith("/api/me/") for path in paths)
    assert set(paths["/api/me"]) == {"get"}


@pytest.mark.parametrize("path,service,args", [
    ("/trainees/7", "get_own_trainee", (8, 7)),
    ("/cohorts/1", "get_own_cohort", (8, 1)),
    ("/plans/3", "get_plan", (3, 8)),
])
def test_owned_detail_does_not_expose_other_users(client, user, services, path, service, args):
    services[service].return_value = None
    assert client.get(path).status_code == 404
    services[service].assert_called_once_with(*args)


def test_own_trainee_progress(client, user, services):
    services["get_own_progress"].return_value = [{"trainee_id": 7, "comments": "My report"}]
    assert client.get("/progress/trainee/7").json() == [{"trainee_id": 7, "comments": "My report"}]
    services["get_own_trainee"].assert_called_once_with(8, 7)
    services["get_own_progress"].assert_called_once_with(8, trainee_id=7)
    services["get_progress_by_trainee"].assert_not_called()
    services["get_own_trainee"].return_value = None
    services["get_own_progress"].reset_mock()
    assert client.get("/progress/trainee/99").status_code == 404
    services["get_own_progress"].assert_not_called()


def test_own_plan_progress(client, user, services):
    services["get_own_progress"].return_value = []
    assert client.get("/progress/plan/3").json() == []
    services["get_plan"].assert_called_once_with(3, 8)
    services["get_own_progress"].assert_called_once_with(8, plan_id=3)
    services["get_progress_by_plan"].assert_not_called()
    services["get_plan"].return_value = None
    services["get_own_progress"].reset_mock()
    assert client.get("/progress/plan/99").status_code == 404
    services["get_own_progress"].assert_not_called()


@pytest.mark.parametrize("role", ["HR", "MANAGER", "TRAINEE"])
def test_notifications_ownership_for_every_role(client, user, services, role):
    user.role = role
    assert client.get("/notifications/8").status_code == 200
    assert client.get("/notifications/99").status_code == 403
    services["get_notifications_by_user"].assert_called_once_with(8)
    services["mark_notification_as_read"].return_value = False
    assert client.put("/notifications/99/read").status_code == 404
    services["mark_notification_as_read"].assert_called_once_with(99, 8)


def test_progress_can_derive_identity_but_rejects_foreign_id(client, user, services):
    body = {"plan_id": 3, "status": "IN_PROGRESS", "comments": None}
    assert client.post("/progress", json=body).status_code == 201
    services["get_own_trainee"].assert_called_once_with(8, None)
    services["create_progress_report"].assert_called_once_with(7, 3, "IN_PROGRESS", None, 8)
    services["get_own_trainee"].return_value = None
    services["create_progress_report"].reset_mock()
    assert client.post("/progress", json={**body, "trainee_id": 99}).status_code == 403
    services["create_progress_report"].assert_not_called()


def test_personal_sql_always_filters_by_authenticated_user(monkeypatch):
    from services import personal_service
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(personal_service, "get_connection", lambda: connection)
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    assert personal_service.get_own_trainee(8, 99) is None
    query, params = cursor.execute.call_args.args
    assert "user_id = %s" in query and params == (8, 99, 99)
    assert personal_service.get_own_cohort(8, 2) is None
    query, params = cursor.execute.call_args.args
    assert "t.user_id = %s" in query and params == (2, 8)
    assert personal_service.get_own_progress(8, plan_id=3) == []
    query, params = cursor.execute.call_args.args
    assert "t.user_id = %s" in query and params == (8, None, None, 3, 3)


def test_ambiguous_trainee_mapping_is_not_guessed(client, user, services):
    from services.personal_service import MultipleTraineeRecordsError
    services["get_own_trainee"].side_effect = MultipleTraineeRecordsError
    assert client.post("/progress", json={"plan_id": 3, "status": "IN_PROGRESS", "comments": None}).status_code == 409
    services["create_progress_report"].assert_not_called()


def test_unenrolled_users_response(client, user, services):
    user.role = "HR"
    services["get_unenrolled_users"].return_value = [{"user_id": 25, "email": "new@example.com", "name": "New User"}]
    response = client.get("/users/unenrolled")
    assert response.status_code == 200
    assert response.json() == services["get_unenrolled_users"].return_value


def test_unenrolled_users_query_excludes_existing_profiles(db):
    connection, cursor = db
    cursor.fetchall.return_value = []
    assert trainee_service.get_unenrolled_users() == []
    query = cursor.execute.call_args.args[0]
    assert "u.role = 'TRAINEE'" in query
    assert "NOT EXISTS" in query and "t.user_id = u.id" in query
    assert "u.id AS user_id, u.name, u.email" in query
    assert "password" not in query


def test_enrollment_rejects_existing_profile(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(8,), (7,)]
    with pytest.raises(trainee_service.TraineeAlreadyExistsError):
        trainee_service.create_trainee(8, None, "ACTIVE", "2026-10-06")
    assert "pg_advisory_xact_lock" in cursor.execute.call_args_list[0].args[0]
    assert not any("INSERT" in call.args[0] for call in cursor.execute.call_args_list)
    assert connection.__exit__.call_args.args[0] is trainee_service.TraineeAlreadyExistsError


def test_enrollment_of_available_user(db):
    connection, cursor = db
    cursor.fetchone.side_effect = [(8,), None, (7,)]
    assert trainee_service.create_trainee(8, None, "ACTIVE", "2026-10-06") == 7
    assert cursor.execute.call_args_list[-2].args[1] == (None, "ACTIVE", "2026-10-06", 8)


def test_duplicate_enrollment_returns_conflict(client, user, services):
    user.role = "HR"
    services["create_trainee"].side_effect = trainee_service.TraineeAlreadyExistsError
    response = client.post("/trainees", json={"user_id": 8, "cohort_id": None, "status": "ACTIVE", "onboarding_date": "2026-10-06"})
    assert response.status_code == 409
    assert "already enrolled" in response.json()["detail"]


@pytest.mark.parametrize("role", ["HR", "MANAGER", "TRAINEE"])
def test_role_change_forwards_selected_role(client, user, services, role):
    user.role = "HR"
    services["update_user_role"].return_value = {"user_id": 9, "role": role}
    assert client.patch("/users/9/role", json={"role": role}).status_code == 200
    services["update_user_role"].assert_called_once_with(9, role)


def test_role_change_missing_assigned_and_invalid(client, user, services):
    from services.promotion_service import AssignedTrainingError
    user.role = "HR"
    assert client.patch("/users/9/role", json={"role": "ADMIN"}).status_code == 422
    assert client.patch("/users/9/role", json={"role": "HR", "email": "x"}).status_code == 422
    services["update_user_role"].assert_not_called()
    services["update_user_role"].return_value = None
    assert client.patch("/users/9/role", json={"role": "HR"}).status_code == 404
    services["update_user_role"].side_effect = AssignedTrainingError
    assert client.patch("/users/9/role", json={"role": "HR"}).status_code == 409


@pytest.mark.parametrize("method,path,role,body", [
    ("POST", "/trainees", "HR", {"user_id": 8, "cohort_id": None, "onboarding_date": "2026-10-06"}),
    ("PATCH", "/trainees/7", "HR", {}),
    ("PUT", "/trainees/7", "HR", {"cohort_id": None, "onboarding_date": "2026-10-06"}),
    ("POST", "/progress", "TRAINEE", {"plan_id": 3, "comments": None}),
])
@pytest.mark.parametrize("status", ["OTHER", "active", "", None])
def test_invalid_status_rejected(client, user, services, method, path, role, body, status):
    user.role = role
    assert client.request(method, path, json={**body, "status": status}).status_code == 422
    services["create_trainee"].assert_not_called()
    services["update_trainee"].assert_not_called()
    services["create_progress_report"].assert_not_called()


@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE", "COMPLETED", "WITHDRAWN"])
def test_trainee_status_values(client, user, services, status):
    user.role = "HR"
    assert client.patch("/trainees/7", json={"status": status}).status_code == 200


@pytest.mark.parametrize("status", ["NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED"])
def test_progress_status_values(client, user, services, status):
    assert client.post("/progress", json={"trainee_id":7,"plan_id":3,"status":status,"comments":None}).status_code == 201


def test_cohort_member_changes(client, user, services):
    user.role = "HR"
    services["update_cohort_members"].return_value = [7, 9]
    response = client.patch("/cohorts/1/members", json={"add":[7],"remove":[9]})
    assert response.json() == {"updated_ids":[7,9]}
    services["update_cohort_members"].assert_called_once_with(1,[7],[9])
    assert client.patch("/cohorts/1/members", json={"add":[7],"remove":[7]}).status_code == 422
    assert client.patch("/cohorts/1/members", json={"add":[-1]}).status_code == 422
    services["update_cohort_members"].return_value = None
    assert client.patch("/cohorts/1/members", json={"add":[7]}).status_code == 404
    services["update_cohort_members"].side_effect = cohort_service.MissingCohortMemberError
    assert client.patch("/cohorts/1/members", json={"add":[7]}).status_code == 409


def test_assignment_conflicts_are_explained(client, user, services):
    from services.assignment_service import AlreadyAssignedError, AssignmentReferenceError
    user.role = "MANAGER"
    services["assign_plan_to_trainee"].side_effect = AlreadyAssignedError
    response = client.post("/plans/3/assign/trainee/7")
    assert response.status_code == 409
    assert "already assigned" in response.json()["detail"]
    services["assign_plan_to_trainee"].side_effect = AssignmentReferenceError
    assert client.post("/plans/3/assign/trainee/7").status_code == 404


def test_assignment_editor_contract(client, user, services):
    user.role = "MANAGER"
    services["get_plan_assignments"].return_value = [7,9]
    assert client.get("/plans/3/assignments").json() == {"trainee_ids":[7,9]}
    services["update_plan_assignments"].return_value = [9,11]
    assert client.patch("/plans/3/assignments",json={"add":[11],"remove":[7]}).json() == {"trainee_ids":[9,11]}
    services["update_plan_assignments"].assert_called_once_with(3,[11],[7])
    assert client.patch("/plans/3/assignments",json={"add":[7],"remove":[7]}).status_code == 422
    services["get_plan_assignments"].return_value = None
    assert client.get("/plans/3/assignments").status_code == 404
    services["update_plan_assignments"].return_value = None
    assert client.patch("/plans/3/assignments",json={"remove":[7]}).status_code == 404


@pytest.mark.parametrize("role", ["HR", "MANAGER", "TRAINEE"])
def test_hr_cannot_change_own_role(client, user, services, role):
    user.role = "HR"
    response = client.patch(f"/users/{user.user_id}/role", json={"role":role})
    assert response.status_code == 403
    assert "cannot change your own role" in response.json()["detail"]
    services["update_user_role"].assert_not_called()


def test_unread_count_is_owner_only(client, user, services):
    assert client.get("/notifications/9/unread-count").status_code == 403
    services["get_unread_count"].assert_not_called()
    services["get_unread_count"].return_value = 2
    assert client.get("/notifications/8/unread-count").json() == {"unread":2}
    services["get_unread_count"].assert_called_once_with(8)
