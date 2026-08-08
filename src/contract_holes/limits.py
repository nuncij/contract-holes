from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class ScanLimits:
    max_files: int = 5_000
    max_source_bytes: int = 100 * 1024 * 1024
    compiler_timeout_seconds: float = 120.0
    scan_timeout_seconds: float = 300.0
    max_python_memory_bytes: int = 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        integer_values = {
            "max_files": self.max_files,
            "max_source_bytes": self.max_source_bytes,
            "max_python_memory_bytes": self.max_python_memory_bytes,
        }
        for name, value in integer_values.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        time_values = {
            "compiler_timeout_seconds": self.compiler_timeout_seconds,
            "scan_timeout_seconds": self.scan_timeout_seconds,
        }
        for name, value in time_values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a positive finite number")
        if self.compiler_timeout_seconds > self.scan_timeout_seconds:
            raise ValueError(
                "compiler_timeout_seconds must not exceed scan_timeout_seconds"
            )
