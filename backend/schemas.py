from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CommandOutcome:
    response: str
    action_status: str
    sentiment: str = "neutral"
    pending_command: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
