"""Compatibility facade for the command orchestrator."""

from __future__ import annotations

from .orchestrator import AIOrchestrator

_orchestrator = AIOrchestrator()


def execute_command(query: str, **kwargs):
    """Execute a command through the single deterministic-first gateway."""
    return _orchestrator.execute(query, **kwargs)
