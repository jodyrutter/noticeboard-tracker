import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import auth
from auth import CurrentUser, BearerCredentials
from auth_models import SignupRequest, LoginRequest, User, TokenResponse
from services import auth_service

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("NOTICEBOARD_RATE_LIMIT_STORAGE_URI", "memory://"),
    headers_enabled=True,
)

# Count malformed requests before FastAPI validates the body.
AUTH_LIMITS = {"/api/signup": "3/minute", "/api/login": "5/minute", "/api/logout": "30/minute", "/api/me": "60/minute"}


@lru_cache
def rate_check(name: str, limit: str):
    # FastAPI builds routes again on inclusion; register each limiter only once.
    def check(request: Request, response: Response):
        return response

    check.__name__ = name + "_rate_check"
    return limiter.limit(limit)(check)


class AuthRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        limit = AUTH_LIMITS.get(self.path)
        if limit is None:
            return original

        limited_check = rate_check(self.endpoint.__name__, limit)

        async def handle(request: Request):
            headers = Response()
            await run_in_threadpool(limited_check, request, headers)
            response = await original(request)
            for key, value in headers.headers.items():
                if key.startswith("x-ratelimit-") or key == "retry-after":
                    response.headers[key] = value
            response.headers["Cache-Control"] = "no-store"
            return response

        return handle


router = APIRouter(tags=["auth"], route_class=AuthRoute)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return _rate_limit_exceeded_handler(request, exc)


@router.post("/api/signup", response_model=User, status_code=201)
def signup(request: Request, response: Response, user_data: SignupRequest) -> User:
    auth.get_jwt_secret()
    try:
        return auth_service.create_user(user_data)
    except auth_service.EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None


@router.post("/api/login", response_model=TokenResponse)
def signin(request: Request, response: Response, credentials: LoginRequest) -> dict[str, str]:
    auth.get_jwt_secret()
    user = auth_service.authenticate(credentials.email, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    token = auth.create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/api/logout", status_code=204)
def logout(request: Request, response: Response, credentials: BearerCredentials) -> Response:
    auth.logout_session(credentials)
    return Response(status_code=204)


@router.get("/api/me", response_model=User)
def get_me(current_user: CurrentUser) -> User:
    return current_user
