from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

import jwt
import psycopg2
import pytest
from fastapi.testclient import TestClient

import auth
import main
from auth_models import SignupRequest, User
from auth_routes import limiter
from services import auth_service

SECRET = "test-only-not-a-deployment-secret-1234567890"
SIGNUP = {"name": "Trainee", "email": "trainee@example.com", "password": "Password!123"}


@pytest.fixture(autouse=True)
def isolated_auth(monkeypatch):
    monkeypatch.setenv("NOTICEBOARD_JWT_SECRET", SECRET)
    monkeypatch.setattr(psycopg2, "connect", Mock(side_effect=AssertionError("No live DB in tests")))
    # Never reset an externally configured Redis store.
    from limits.storage import MemoryStorage
    monkeypatch.setattr(limiter, "_storage", MemoryStorage())
    from limits.strategies import FixedWindowRateLimiter
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(limiter._storage))


@pytest.fixture
def client():
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def session_store(monkeypatch):
    sessions = {}
    users = {1: User(user_id=1, name="Trainee", email="trainee@example.com", role="TRAINEE")}

    def create(sid, user_id, now, expires):
        sessions[sid] = (user_id, now, expires)

    def current(sid, user_id, now, idle):
        session = sessions.get(sid)
        if session is None or session[0] != user_id or session[2] <= now or session[1] <= now - idle:
            return None
        sessions[sid] = (user_id, now, session[2])
        return users.get(user_id)

    def revoke(sid, user_id):
        if sid in sessions and sessions[sid][0] == user_id:
            del sessions[sid]

    monkeypatch.setattr(auth_service, "create_session", create)
    monkeypatch.setattr(auth_service, "session_user", current)
    monkeypatch.setattr(auth_service, "revoke_session", revoke)
    monkeypatch.setattr(auth_service, "authenticate", lambda email, password: users[1] if password == SIGNUP["password"] else None)
    return sessions, users


def login(client):
    response = client.post("/api/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    return response.json()["access_token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup(client, monkeypatch):
    create = Mock(return_value=User(user_id=1, name="Trainee", email=SIGNUP["email"], role="TRAINEE"))
    monkeypatch.setattr(auth_service, "create_user", create)
    response = client.post("/api/signup", json=SIGNUP)
    assert response.status_code == 201
    assert response.json() == {"user_id": 1, "name": "Trainee", "email": SIGNUP["email"], "role": "TRAINEE"}
    assert "password" not in response.text
    create.assert_called_once()


@pytest.mark.parametrize("extra", [{"role": "HR"}, {"role": "MANAGER"}, {"admin": True}, {"user_id": 99}])
def test_signup_cannot_choose_privileges(client, extra):
    response = client.post("/api/signup", json={**SIGNUP, **extra})
    assert response.status_code == 422
    assert SIGNUP["password"] not in response.text


@pytest.mark.parametrize("changes", [{"password": "short"}, {"password": "abcdefgh"}, {"email": "bad"}, {"name": "  "}])
def test_signup_validation(client, changes):
    response = client.post("/api/signup", json={**SIGNUP, **changes})
    assert response.status_code == 422
    assert '"input"' not in response.text


def test_duplicate_email(client, monkeypatch):
    monkeypatch.setattr(auth_service, "create_user", Mock(side_effect=auth_service.EmailAlreadyExistsError))
    assert client.post("/api/signup", json=SIGNUP).status_code == 409


def test_signin_me_logout_revokes_only_current_session(client, session_store):
    first, second = login(client), login(client)
    assert client.get("/api/me", headers=bearer(first)).json()["role"] == "TRAINEE"
    response = client.post("/api/logout", headers=bearer(first))
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/me", headers=bearer(first)).status_code == 401
    assert client.get("/api/me", headers=bearer(second)).status_code == 200
    assert client.post("/api/logout", headers=bearer(first)).status_code == 204


@pytest.mark.parametrize("role", ["HR", "MANAGER"])
def test_current_role_comes_from_database(client, session_store, role):
    token = login(client)
    session_store[1][1] = session_store[1][1].model_copy(update={"role": role})
    assert client.get("/api/me", headers=bearer(token)).json()["role"] == role
    assert client.get("/api/me", headers=bearer(login(client))).json()["role"] == role


def test_bad_password(client, session_store):
    response = client.post("/api/login", json={"email": SIGNUP["email"], "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic nonsense"}, bearer("nonsense")])
def test_missing_or_invalid_credentials(client, headers):
    assert client.get("/api/me", headers=headers).status_code == 401
    assert client.post("/api/logout", headers=headers).status_code == 401


@pytest.mark.parametrize("change", ["expired", "signature", "missing_sid", "bad_role", "bad_sub", "bad_algorithm"])
def test_invalid_jwt(client, session_store, change):
    payload = jwt.decode(login(client), SECRET, algorithms=["HS256"])
    secret, algorithm = SECRET, "HS256"
    if change == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif change == "signature":
        secret = "another-long-test-secret-12345678901234567890"
    elif change == "missing_sid":
        del payload["sid"]
    elif change == "bad_role":
        payload["role"] = "ADMIN"
    elif change == "bad_sub":
        payload["sub"] = "not-an-id"
    elif change == "bad_algorithm":
        algorithm = "HS384"
        secret = "a" * 48
    token = jwt.encode(payload, secret, algorithm=algorithm)
    assert client.get("/api/me", headers=bearer(token)).status_code == 401


def test_idle_expired_or_deleted_user(client, session_store):
    token = login(client)
    sid = jwt.decode(token, SECRET, algorithms=["HS256"])["sid"]
    user_id, now, expires = session_store[0][sid]
    session_store[0][sid] = (user_id, now - timedelta(minutes=31), expires)
    assert client.get("/api/me", headers=bearer(token)).status_code == 401
    session_store[0][sid] = (user_id, now, expires)
    del session_store[1][1]
    assert client.get("/api/me", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize("path,limit", [("/api/signup", 3), ("/api/login", 5), ("/api/logout", 30)])
def test_rate_limits_count_invalid_requests_and_ignore_forwarded_spoofing(client, path, limit):
    for _ in range(limit):
        assert client.post(path, json={}).status_code in (401, 422)
    response = client.post(path, json={}, headers={"X-Forwarded-For": "198.51.100.15"})
    assert response.status_code == 429
    assert "retry-after" in response.headers


def test_login_limit_before_password_work(client, monkeypatch):
    verify = Mock(return_value=None)
    monkeypatch.setattr(auth_service, "authenticate", verify)
    for _ in range(5):
        assert client.post("/api/login", json={"email": SIGNUP["email"], "password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"email": SIGNUP["email"], "password": "wrong"}).status_code == 429
    assert verify.call_count == 5


def test_missing_secret_fails_before_db(client, monkeypatch):
    monkeypatch.delenv("NOTICEBOARD_JWT_SECRET")
    assert client.post("/api/signup", json=SIGNUP).status_code == 503
    assert client.post("/api/login", json={"email": SIGNUP["email"], "password": "wrong"}).status_code == 503


@pytest.fixture
def database_double(monkeypatch):
    connection, cursor = MagicMock(), MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(auth_service, "get_connection", lambda: connection)
    return connection, cursor


def test_create_user_hashes_password_and_fixes_role(database_double):
    connection, cursor = database_double
    cursor.fetchone.return_value = (1, "Trainee", SIGNUP["email"], "TRAINEE")
    request = SignupRequest(**{**SIGNUP, "email": " TRAINEE@EXAMPLE.COM "})
    user = auth_service.create_user(request)
    sql, params = cursor.execute.call_args.args
    assert "'TRAINEE'" in sql and "ON CONFLICT" in sql
    assert params[1] == SIGNUP["email"]
    assert params[2] != SIGNUP["password"]
    assert auth_service.password_hasher.verify(SIGNUP["password"], params[2])
    assert user.role == "TRAINEE"
    connection.close.assert_called_once()


def test_duplicate_insert_closes_and_rolls_back(database_double):
    connection, cursor = database_double
    cursor.fetchone.return_value = None
    with pytest.raises(auth_service.EmailAlreadyExistsError):
        auth_service.create_user(SignupRequest(**SIGNUP))
    assert connection.__exit__.call_args.args[0] is auth_service.EmailAlreadyExistsError
    connection.close.assert_called_once()


@pytest.mark.parametrize("scenario", ["good", "wrong", "missing", "placeholder"])
def test_real_password_verification(database_double, scenario):
    _, cursor = database_double
    hashed = auth_service.password_hasher.hash(SIGNUP["password"])
    cursor.fetchone.return_value = None if scenario == "missing" else (1, "Trainee", SIGNUP["email"], "TRAINEE", "temporary" if scenario == "placeholder" else hashed)
    result = auth_service.authenticate(" TRAINEE@EXAMPLE.COM ", "wrong" if scenario == "wrong" else SIGNUP["password"])
    assert (result is not None) == (scenario == "good")
    assert cursor.execute.call_args.args[1] == (SIGNUP["email"],)
