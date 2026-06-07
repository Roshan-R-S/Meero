"""Private-by-default FastAPI exception handling."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse

import config

logger = logging.getLogger(__name__)


async def global_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("Unhandled exception during request: %s %s", request.method, request.url)
    content = {"error": "Internal server error"}
    if getattr(config, "DEBUG_ERRORS", False):
        content["detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)
