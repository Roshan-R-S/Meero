"""Privacy-safe orchestration decision trace."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DecisionStep:
    stage: str
    status: str
    reason: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None


@dataclass
class DecisionTrace:
    steps: list[DecisionStep] = field(default_factory=list)

    def add(self, stage: str, status: str, **details) -> None:
        allowed = {
            key: value
            for key, value in details.items()
            if key in {"reason", "intent", "confidence", "latency_ms"} and value is not None
        }
        self.steps.append(DecisionStep(stage=stage, status=status, **allowed))

    def to_list(self) -> list[dict]:
        return [
            {key: value for key, value in asdict(step).items() if value is not None}
            for step in self.steps
        ]
