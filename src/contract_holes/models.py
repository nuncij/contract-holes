from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
import hashlib
from pathlib import Path
from typing import Any


class Severity(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def parse(cls, value: str) -> "Severity":
        try:
            return cls[value.upper()]
        except KeyError as exc:
            choices = ", ".join(item.name.lower() for item in cls)
            raise ValueError(f"unknown severity {value!r}; choose one of: {choices}") from exc

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    title: str
    message: str
    path: Path
    line: int
    column: int
    excerpt: str
    recommendation: str
    confidence: str = "high"
    end_line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        material = f"{self.rule_id}\0{self.path}\0{self.line}\0{self.excerpt.strip()}"
        return hashlib.sha256(material.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["severity"] = str(self.severity)
        result["path"] = str(self.path)
        result["fingerprint"] = self.fingerprint
        return result


@dataclass(frozen=True, slots=True)
class RuleInfo:
    rule_id: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    confidence: str = "high"

