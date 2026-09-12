"""Compatibility facade for the command orchestrator."""

from __future__ import annotations

import logging

from .orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

_orchestrator = None
_init_error = None

try:
    _orchestrator = AIOrchestrator()
except Exception as exc:
    _init_error = exc
    logger.error("Command orchestrator initialization failed: %s", exc)


def execute_command(query: str, **kwargs):
    """Execute a command through the single deterministic-first gateway."""
    if _orchestrator is None:
        raise RuntimeError(f"Command orchestrator unavailable: {_init_error}")
    return _orchestrator.execute(query, **kwargs)
