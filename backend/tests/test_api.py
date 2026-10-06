from datetime import date, datetime
import asyncio
import json
from unittest.mock import Mock

import psycopg2
import pytest
from fastapi.testclient import TestClient

import main
from lambda_function import lambda_handler


@pytest.fixture(autouse=True)
def block_database(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("API tests must not connect to the database")
    monkeypatch.setattr(psycopg2, "connect", fail)


@pytest.fixture
def client():
    with TestClient(main.app) as client:
        yield client


@pytest.mark.parametrize("path,service,args", [
    ("/trainees", "get_all_trainees", ()),
    ("/cohorts", "get_all_cohorts", ()),
    ("/plans", "get_all_plans", ()),
    ("/progress/trainee/7", "get_progress_by_trainee", (7,)),
    ("/notifications/8", "get_notifications_by_user", (8,)),
    ("/dashboard", "get_dashboard_summary", ()),
    ("/dashboard/trainees", "get_trainee_overview", ()),
])
def test_read_routes(client, monkeypatch, path, service, args):
    result = {"total_trainees": 3} if path == "/dashboard" else [[7, "example"]]
    mock = Mock(return_value=result)
    monkeypatch.setattr(main, service, mock)
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == result
    mock.assert_called_once_with(*args)


@pytest.mark.parametrize("path,body,service,args,result,expected", [
    ("/trainees", {"user_id": 2, "cohort_id": 1, "status": "ACTIVE", "onboarding_date": "2026-10-06"},
     "create_trainee", (2, 1, "ACTIVE", date(2026, 10, 6)), 12, {"id": 12, "message": "Trainee created"}),
    ("/cohorts", {"name": "Fall", "start_date": "2026-10-06", "end_date": "2026-12-01"},
     "create_cohort", ("Fall", date(2026, 10, 6), date(2026, 12, 1)), 12, {"id": 12, "message": "Cohort created"}),
    ("/plans", {"title": "Practice", "description": "SQL", "due_date": "2026-10-06", "created_by": 2},
     "create_plan", ("Practice", "SQL", date(2026, 10, 6), 2), 12, {"id": 12, "message": "Plan created"}),
    ("/plans/3/assign/trainee/7", None, "assign_plan_to_trainee", (3, 7), 12,
     {"id": 12, "message": "Plan assigned to trainee"}),
    ("/plans/3/assign/cohort/1", None, "assign_plan_to_cohort", (3, 1), [12, 13],
     {"assignment_ids": [12, 13], "message": "Plan assigned to cohort"}),
    ("/progress", {"trainee_id": 7, "plan_id": 3, "status": "IN_PROGRESS", "comments": "Started"},
     "create_progress_report", (7, 3, "IN_PROGRESS", "Started"), 12, {"id": 12, "message": "Progress report created"}),
    ("/notifications", {"user_id": 2, "message": "Reminder"}, "create_notification", (2, "Reminder"), 12,
     {"id": 12, "message": "Notification created"}),
])
def test_create_routes(client, monkeypatch, path, body, service, args, result, expected):
    mock = Mock(return_value=result)
    monkeypatch.setattr(main, service, mock)
    response = client.post(path, json=body)
    assert response.status_code == 201
    assert response.json() == expected
    mock.assert_called_once_with(*args)


def test_mark_read(client, monkeypatch):
    mock = Mock()
    monkeypatch.setattr(main, "mark_notification_as_read", mock)
    response = client.put("/notifications/12/read")
    assert response.status_code == 200
    assert response.json() == {"message": "Notification marked as read"}
    mock.assert_called_once_with(12)


@pytest.mark.parametrize("path", ["/trainees", "/cohorts", "/plans", "/progress", "/notifications"])
def test_missing_fields_rejected(client, path):
    assert client.post(path, json={}).status_code == 422


def test_invalid_values_rejected_before_service(client, monkeypatch):
    mock = Mock()
    monkeypatch.setattr(main, "create_trainee", mock)
    body = {"user_id": 2, "cohort_id": 1, "status": "ACTIVE", "onboarding_date": "not-a-date"}
    assert client.post("/trainees", json=body).status_code == 422
    body.update(onboarding_date="2026-10-06", user_id="abc")
    assert client.post("/trainees", json=body).status_code == 422
    mock.assert_not_called()
    assert client.get("/progress/trainee/abc").status_code == 422
    assert client.post("/notifications", content="{", headers={"Content-Type": "application/json"}).status_code == 422


def test_serialization(client, monkeypatch):
    monkeypatch.setattr(main, "get_all_trainees", lambda: [(1, date(2026, 10, 6), datetime(2026, 10, 6, 9, 30))])
    assert client.get("/trainees").json() == [[1, "2026-10-06", "2026-10-06T09:30:00"]]


def test_docs_and_routing(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert sum(len(methods) for path, methods in schema["paths"].items() if not path.startswith("/api/")) == 15
    assert client.get("/missing").status_code == 404
    assert client.delete("/trainees").status_code == 405
    assert client.get("/notifications/1/extra").status_code == 404


def test_lambda_adapter(monkeypatch):
    monkeypatch.setattr(main, "get_dashboard_summary", lambda: {"total_trainees": 3})
    event = {
        "version": "2.0", "routeKey": "GET /dashboard", "rawPath": "/dashboard",
        "rawQueryString": "", "headers": {"host": "localhost"},
        "requestContext": {"http": {"method": "GET", "path": "/dashboard", "sourceIp": "127.0.0.1"}},
        "body": None, "isBase64Encoded": False,
    }
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = lambda_handler(event, None)
    finally:
        loop.close()
        asyncio.set_event_loop(None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"total_trainees": 3}
