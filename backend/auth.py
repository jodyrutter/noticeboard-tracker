import os
from datetime import datetime, timezone, timedelta
from secrets import token_urlsafe
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt.exceptions import InvalidTokenError

from auth_models import User
from services import auth_service

JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=30)
IDLE_TIMEOUT = timedelta(minutes=30)
bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def authentication_error() -> HTTPException:
    return HTTPException(status_code=401, detail="Missing, invalid, or expired login", headers={"WWW-Authenticate": "Bearer"})


def get_jwt_secret() -> str:
    secret = os.environ.get("NOTICEBOARD_JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return secret


def encode_session_token(user: User, session_id: str, now: datetime) -> str:
    payload = {
        "sub": str(user.user_id),
        "username": user.email,
        "role": user.role,
        "sid": session_id,
        "jti": token_urlsafe(32),
        "exp": now + TOKEN_LIFETIME,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_credentials(credentials: BearerCredentials) -> dict:
    if credentials is None:
        raise authentication_error()
    try:
        payload = jwt.decode(
            credentials.credentials, get_jwt_secret(), algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "username", "role", "sid", "jti", "exp"]},
        )
        if not isinstance(payload["sub"], str) or not 0 < int(payload["sub"]) <= 9223372036854775807:
            raise authentication_error()
        if not isinstance(payload["username"], str):
            raise authentication_error()
        if payload["role"] not in ("TRAINEE", "HR", "MANAGER"):
            raise authentication_error()
        if not isinstance(payload["sid"], str) or not payload["sid"]:
            raise authentication_error()
        if not isinstance(payload["jti"], str) or not payload["jti"]:
            raise authentication_error()
        return payload
    except (InvalidTokenError, ValueError, TypeError):
        raise authentication_error() from None


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    session_id = token_urlsafe(32)
    token = encode_session_token(user, session_id, now)
    auth_service.create_session(session_id, user.user_id, now, now + TOKEN_LIFETIME)
    return token


def get_current_user(credentials: BearerCredentials) -> User:
    payload = decode_credentials(credentials)
    # Read the current role from the database.
    user = auth_service.session_user(payload["sid"], int(payload["sub"]), datetime.now(timezone.utc), IDLE_TIMEOUT)
    if user is None:
        raise authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    def check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Your role cannot perform this action")
        return current_user
    return check


HRUser = Annotated[User, Depends(require_roles("HR"))]
ManagerUser = Annotated[User, Depends(require_roles("MANAGER"))]
TraineeUser = Annotated[User, Depends(require_roles("TRAINEE"))]
StaffUser = Annotated[User, Depends(require_roles("HR", "MANAGER"))]
PlanReader = Annotated[User, Depends(require_roles("MANAGER", "TRAINEE"))]


def logout_session(credentials: BearerCredentials) -> None:
    payload = decode_credentials(credentials)
    auth_service.revoke_session(payload["sid"], int(payload["sub"]))
