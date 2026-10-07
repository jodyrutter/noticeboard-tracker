import asyncio
from unittest.mock import MagicMock, Mock

import psycopg2
import pytest
from fastapi.testclient import TestClient

import auth
import main
from auth_models import User
from security import MAX_REQUEST_BYTES, RequestSecurityMiddleware, SECURITY_HEADERS
from services import cohort_service, dashboard_service, notification_service, plan_service, progress_service, trainee_service


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(psycopg2, "connect", Mock(side_effect=AssertionError("No live DB in tests")))
    main.app.dependency_overrides[auth.get_current_user] = lambda: User(
        user_id=1, name="Manager", email="manager@example.com", role="MANAGER"
    )
    with TestClient(main.app, raise_server_exceptions=False) as client:
        yield client
    main.app.dependency_overrides.pop(auth.get_current_user, None)


@pytest.mark.parametrize("status", [200, 403, 404, 422, 500])
def test_headers_on_success_and_errors(client, monkeypatch, status):
    monkeypatch.setattr(main, "get_all_plans", Mock(return_value=[]))
    if status == 200:
        response = client.get("/plans")
    elif status == 403:
        response = client.get("/users/promotion")
    elif status == 404:
        response = client.get("/not-a-route")
    elif status == 422:
        response = client.post("/plans", json={})
    else:
        monkeypatch.setattr(main, "get_all_plans", Mock(side_effect=RuntimeError("private database details")))
        response = client.get("/plans")
        assert "private database details" not in response.text
    assert response.status_code == status
    for key, value in SECURITY_HEADERS.items():
        assert response.headers[key] == value


def test_large_body_rejected_before_service(client, monkeypatch):
    create = Mock()
    monkeypatch.setattr(main, "create_plan", create)
    response = client.post("/plans", content=b"x" * (MAX_REQUEST_BYTES + 1))
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"
    create.assert_not_called()


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"1")]])
def test_chunked_or_understated_size_cannot_bypass_limit(headers):
    reached_app = Mock()
    async def app(scope, receive, send):
        reached_app()
    chunks = iter([
        {"type": "http.request", "body": b"x" * MAX_REQUEST_BYTES, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": False},
    ])
    sent = []
    async def receive():
        return next(chunks)
    async def send(message):
        sent.append(message)
    asyncio.run(RequestSecurityMiddleware(app)({"type": "http", "headers": headers}, receive, send))
    assert sent[0]["status"] == 413
    reached_app.assert_not_called()


def test_write_budget_shared_across_paths_and_invalid_requests(client, monkeypatch):
    for i in range(120):
        response = client.post("/plans" if i % 2 else "/progress", json={})
        assert response.status_code in (403, 422)
    response = client.patch("/plans/9/assignments", json={"add": [], "remove": []})
    assert response.status_code == 429
    assert "retry-after" in response.headers
    assert response.headers["cache-control"] == "no-store"
    assert client.post("/plans", json={}, headers={"X-Forwarded-For": "192.0.2.99"}).status_code == 429
    monkeypatch.setattr(main, "get_all_plans", lambda: [])
    assert client.get("/plans").status_code == 200
    with TestClient(main.app, client=("192.0.2.2", 1234)) as other_ip:
        assert other_ip.post("/plans", json={}).status_code == 422


@pytest.mark.parametrize("body", [
    {"title": " "}, {"title": "x" * 201}, {"description": "x" * 10_001},
    {"created_by": 999},
])
def test_invalid_plan_input_never_reaches_service(client, monkeypatch, body):
    create = Mock()
    monkeypatch.setattr(main, "create_plan", create)
    response = client.post("/plans", json={"title": "Valid", "description": None, "due_date": None, **body})
    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])
    create.assert_not_called()


@pytest.mark.parametrize("plan_id", ["0", "-1", "2147483648", "999999999999999999999999"])
def test_invalid_identifier_does_not_reach_database(client, monkeypatch, plan_id):
    lookup = Mock()
    monkeypatch.setattr(main, "get_plan", lookup)
    assert client.get(f"/plans/{plan_id}").status_code == 422
    lookup.assert_not_called()


@pytest.mark.parametrize("module,function,args", [
    (cohort_service, "get_all_cohorts", ()),
    (cohort_service, "create_cohort", ("Fall", "2026-10-01", None)),
    (dashboard_service, "get_dashboard_summary", ()),
    (dashboard_service, "get_trainee_overview", ()),
    (notification_service, "create_notification", (1, "Notice")),
    (notification_service, "get_notifications_by_user", (1,)),
    (plan_service, "get_all_plans", ()),
    (plan_service, "create_plan", ("Plan", None, None, 1)),
    (progress_service, "get_progress_by_trainee", (1,)),
    (trainee_service, "get_all_trainees", ()),
])
def test_database_failure_closes_resources(monkeypatch, module, function, args):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    cursor.execute.side_effect = RuntimeError("Database failed")
    monkeypatch.setattr(module, "get_connection", lambda: connection)
    with pytest.raises(RuntimeError):
        getattr(module, function)(*args)
    cursor.close.assert_called_once()
    connection.close.assert_called_once()
    assert connection.__exit__.call_args.args[0] is RuntimeError
