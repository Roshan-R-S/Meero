import json
import logging
from logging.handlers import RotatingFileHandler
import os
import threading
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)

def _resolve_audit_log_path() -> str:
    configured = getattr(config, "AUDIT_LOG_PATH", None)
    if configured:
        return os.path.abspath(configured)
    data_dir = getattr(config, "DATA_DIR", None)
    if data_dir:
        return os.path.abspath(os.path.join(data_dir, "audit.jsonl"))
    return os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "data", "audit.jsonl"
    ))

AUDIT_LOG_PATH = _resolve_audit_log_path()

_handler_lock = threading.Lock()
_cached_handler = None
_cached_handler_path = None

def _get_rotating_handler(path: str) -> RotatingFileHandler:
    global _cached_handler, _cached_handler_path
    with _handler_lock:
        if _cached_handler is not None and _cached_handler_path == path:
            return _cached_handler
        if _cached_handler is not None:
            try:
                _cached_handler.close()
            except Exception:
                pass
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handler = RotatingFileHandler(
            path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        _cached_handler = handler
        _cached_handler_path = path
        return _cached_handler

def log_audit_event(
    command: str,
    action_status: str,
    response: str,
    engine: str,
    sentiment: str,
    confidence: float = None,
    intent: str = None,
    latency_ms: float = 0.0,
    confirmation_phrase: Optional[str] = None,
):
    if not getattr(config, "AUDIT_LOG_ENABLED", True):
        return
    try:
        current_path = AUDIT_LOG_PATH
        os.makedirs(os.path.dirname(current_path), exist_ok=True)
        event = {
            "timestamp": time.time(),
            "action_status": action_status,
            "engine": engine,
            "sentiment": sentiment,
            "confidence": confidence,
            "intent": intent,
            "latency_ms": latency_ms,
        }
        if confirmation_phrase:
            event["confirmation_phrase"] = confirmation_phrase
        if getattr(config, "AUDIT_LOG_COMMAND_TEXT", False):
            event["command"] = command
            event["response"] = response

        handler = _get_rotating_handler(current_path)
        record = logging.LogRecord(
            name="meero.audit",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=json.dumps(event),
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        handler.flush()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
