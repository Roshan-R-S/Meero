import asyncio
import types

import pytest
from fastapi import HTTPException

from backend.middleware import rate_limit


def run(coroutine):
    return asyncio.run(coroutine)


def test_unavailable_limiter_fails_open_when_configured(monkeypatch):
    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", True)
    monkeypatch.setattr(rate_limit, "RateLimiter", None)
    monkeypatch.setattr(rate_limit, "FastAPILimiter", None)
    monkeypatch.setattr(rate_limit, "ready", False)

    run(rate_limit.check(object()))


def test_unavailable_limiter_fails_closed_when_configured(monkeypatch):
    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", False)
    monkeypatch.setattr(rate_limit, "RateLimiter", None)
    monkeypatch.setattr(rate_limit, "FastAPILimiter", None)
    monkeypatch.setattr(rate_limit, "ready", False)

    with pytest.raises(HTTPException) as exc_info:
        run(rate_limit.check(object()))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Rate limiter unavailable"


def test_failed_limiter_initialization_resets_ready_and_fails_closed(monkeypatch):
    class UnavailableRedisClient:
        async def ping(self):
            raise ConnectionError("private redis failure")

    fake_redis = types.SimpleNamespace(
        from_url=lambda *_args, **_kwargs: UnavailableRedisClient(),
    )
    monkeypatch.setattr(rate_limit, "redis", fake_redis)
    monkeypatch.setattr(rate_limit, "FastAPILimiter", types.SimpleNamespace(init=lambda _client: None))
    monkeypatch.setattr(rate_limit, "RateLimiter", object)
    monkeypatch.setattr(rate_limit, "ready", True)
    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", False)

    run(rate_limit.initialize())

    assert rate_limit.ready is False
    with pytest.raises(HTTPException, match="Rate limiter unavailable"):
        run(rate_limit.check(object()))


def test_runtime_limiter_failure_obeys_fail_open_and_fail_closed(monkeypatch):
    class FailingRateLimiter:
        def __init__(self, **_kwargs):
            pass

        async def __call__(self, _request):
            raise ConnectionError("private redis failure")

    monkeypatch.setattr(rate_limit, "RateLimiter", FailingRateLimiter)
    monkeypatch.setattr(rate_limit, "FastAPILimiter", types.SimpleNamespace(redis=object()))
    monkeypatch.setattr(rate_limit, "ready", True)

    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", True)
    run(rate_limit.check(object()))

    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", False)
    with pytest.raises(HTTPException) as exc_info:
        run(rate_limit.check(object()))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Rate limiter unavailable"


def test_limiter_http_response_passes_through(monkeypatch):
    class LimitedRateLimiter:
        def __init__(self, **_kwargs):
            pass

        async def __call__(self, _request):
            raise HTTPException(status_code=429, detail="Too many requests")

    monkeypatch.setattr(rate_limit, "RateLimiter", LimitedRateLimiter)
    monkeypatch.setattr(rate_limit, "FastAPILimiter", types.SimpleNamespace(redis=object()))
    monkeypatch.setattr(rate_limit, "ready", True)
    monkeypatch.setattr(rate_limit.config, "RATE_LIMIT_FAIL_OPEN", False)

    with pytest.raises(HTTPException) as exc_info:
        run(rate_limit.check(object()))

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Too many requests"
