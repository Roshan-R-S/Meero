"""Redis-backed distributed rate-limit initialization and checks."""

from __future__ import annotations

import inspect
import logging
import os

from fastapi import HTTPException, Request

import config

logger = logging.getLogger(__name__)

try:
    from fastapi_limiter import FastAPILimiter
    from fastapi_limiter.depends import RateLimiter
    import redis.asyncio as redis
except Exception:
    FastAPILimiter = None
    RateLimiter = None
    redis = None

ready = False


async def initialize() -> None:
    global ready
    ready = False
    if FastAPILimiter is None or redis is None:
        logger.info("Rate limiter libraries not available; skipping init")
        return
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        init_result = FastAPILimiter.init(redis_client)
        if inspect.isawaitable(init_result):
            await init_result
        ready = True
        logger.info("Rate limiter initialized with Redis: %s", redis_url)
    except Exception:
        ready = False
        logger.warning("Redis unavailable at %s; disabling distributed rate limiting", redis_url)


def _handle_unavailable() -> None:
    if getattr(config, "RATE_LIMIT_FAIL_OPEN", True):
        return
    raise HTTPException(status_code=503, detail="Rate limiter unavailable")


async def check(request: Request) -> None:
    if RateLimiter is None or FastAPILimiter is None or not ready:
        return _handle_unavailable()
    if not getattr(FastAPILimiter, "redis", None):
        return _handle_unavailable()
    try:
        await RateLimiter(times=10, seconds=60)(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Rate limiter check failed")
        return _handle_unavailable()
