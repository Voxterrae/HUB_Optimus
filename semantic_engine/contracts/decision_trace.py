"""Decision trace contract for Semantic Engine runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DecisionTrace:
    """A single traceable transformation or rule application."""

    step: str
    rule_applied: str
    input_ref: str
    output_ref: str
    reason: str
    uncertainty: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "rule_applied": self.rule_applied,
            "input_ref": self.input_ref,
            "output_ref": self.output_ref,
            "reason": self.reason,
            "uncertainty": self.uncertainty,
            "metadata": dict(self.metadata),
        }
