import json
import os
import time
import logging

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "data", "audit.jsonl"
))

def log_audit_event(
    command: str,
    action_status: str,
    response: str,
    engine: str,
    sentiment: str,
    confidence: float = None,
    intent: str = None,
    latency_ms: float = 0.0
):
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        event = {
            "timestamp": time.time(),
            "command": command,
            "action_status": action_status,
            "response": response,
            "engine": engine,
            "sentiment": sentiment,
            "confidence": confidence,
            "intent": intent,
            "latency_ms": latency_ms
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
