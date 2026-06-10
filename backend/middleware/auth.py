"""API-key and local-request authorization helpers."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, Request

import config

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def client_host(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host


def is_local_request(request: Request) -> bool:
    host = client_host(request)
    return host in LOCAL_HOSTS or host.startswith("127.")


def require_api_key(x_meero_api_key: Optional[str] = Header(default=None)) -> None:
    configured_key = getattr(config, "MEERO_API_KEY", "") or os.environ.get("MEERO_API_KEY", "")
    if getattr(config, "REQUIRE_API_KEY", False) and not configured_key:
        raise HTTPException(status_code=500, detail="API key is required but not configured")
    if configured_key and x_meero_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
