import pytest
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from auth_routes import limiter


@pytest.fixture(autouse=True)
def isolated_rate_limits(monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr(limiter, "_storage", storage)
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(storage))
