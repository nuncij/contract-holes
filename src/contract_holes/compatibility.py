from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Sequence


COMPATIBILITY_SCHEMA_VERSION = "1.0"
COMPATIBILITY_POLICY_VERSION = "1.0"

PYTHON_MINIMUM = (3, 10, 0)
PYTHON_MAXIMUM_EXCLUSIVE = (3, 15, 0)
SOLIDITY_MINIMUM = (0, 8, 20)
SOLIDITY_MAXIMUM_EXCLUSIVE = (0, 8, 37)
FOUNDRY_MINIMUM = (1, 5, 0)
FOUNDRY_MAXIMUM_EXCLUSIVE = (1, 8, 0)
SUPPORTED_EVM_TARGETS = ("paris", "shanghai", "cancun", "prague", "osaka")

REFERENCE_MATRIX = (
    {
        "foundry": "1.5.0",
        "solidity": "0.8.20",
        "evm_target": "paris",
    },
    {
        "foundry": "1.7.1",
        "solidity": "0.8.25",
        "evm_target": "shanghai",
    },
    {
        "foundry": "1.7.1",
        "solidity": "0.8.29",
        "evm_target": "cancun",
    },
    {
        "foundry": "1.7.1",
        "solidity": "0.8.31",
        "evm_target": "prague",
    },
    {
        "foundry": "1.7.1",
        "solidity": "0.8.36",
        "evm_target": "osaka",
    },
)

_SEMANTIC_VERSION = re.compile(r"(?<![0-9])v?([0-9]+)\.([0-9]+)\.([0-9]+)")


def compatibility_payload() -> dict[str, object]:
    return {
        "schema_version": COMPATIBILITY_SCHEMA_VERSION,
        "policy_version": COMPATIBILITY_POLICY_VERSION,
        "supported": {
            "python": _range_payload(PYTHON_MINIMUM, PYTHON_MAXIMUM_EXCLUSIVE),
            "solidity": _range_payload(
                SOLIDITY_MINIMUM,
                SOLIDITY_MAXIMUM_EXCLUSIVE,
            ),
            "foundry": _range_payload(
                FOUNDRY_MINIMUM,
                FOUNDRY_MAXIMUM_EXCLUSIVE,
            ),
            "evm_targets": list(SUPPORTED_EVM_TARGETS),
        },
        "reference_matrix": [dict(entry) for entry in REFERENCE_MATRIX],
        "observed": {
            "python": _observed_python(),
            "foundry": _observed_tool(
                "forge",
                ("--version",),
                FOUNDRY_MINIMUM,
                FOUNDRY_MAXIMUM_EXCLUSIVE,
            ),
            "solidity": _observed_tool(
                "solc",
                ("--version",),
                SOLIDITY_MINIMUM,
                SOLIDITY_MAXIMUM_EXCLUSIVE,
            ),
        },
        "notes": [
            "Foundry is optional for source-only scans.",
            "The solc executable on PATH is informational; Foundry may select a project-specific compiler.",
            "EVM compatibility describes compilation targets, not chain-state simulation.",
        ],
    }


def parse_version(output: str) -> tuple[int, int, int] | None:
    match = _SEMANTIC_VERSION.search(output)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def version_is_supported(
    version: Sequence[int],
    minimum: Sequence[int],
    maximum_exclusive: Sequence[int],
) -> bool:
    normalized = tuple(version[:3])
    return tuple(minimum) <= normalized < tuple(maximum_exclusive)


def _range_payload(
    minimum: tuple[int, int, int],
    maximum_exclusive: tuple[int, int, int],
) -> dict[str, str]:
    return {
        "minimum": _format_version(minimum),
        "maximum_exclusive": _format_version(maximum_exclusive),
    }


def _observed_python() -> dict[str, object]:
    version = tuple(sys.version_info[:3])
    return {
        "version": _format_version(version),
        "status": (
            "supported"
            if version_is_supported(
                version,
                PYTHON_MINIMUM,
                PYTHON_MAXIMUM_EXCLUSIVE,
            )
            else "unsupported"
        ),
    }


def _observed_tool(
    executable: str,
    arguments: tuple[str, ...],
    minimum: tuple[int, int, int],
    maximum_exclusive: tuple[int, int, int],
) -> dict[str, object]:
    resolved = shutil.which(executable)
    if resolved is None:
        return {"version": None, "status": "unavailable"}
    try:
        process = subprocess.run(
            [resolved, *arguments],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"version": None, "status": "unavailable"}
    version = parse_version("\n".join((process.stdout, process.stderr)))
    if process.returncode != 0 or version is None:
        return {"version": None, "status": "unrecognized"}
    return {
        "version": _format_version(version),
        "status": (
            "supported"
            if version_is_supported(version, minimum, maximum_exclusive)
            else "unsupported"
        ),
    }


def _format_version(version: Sequence[int]) -> str:
    return ".".join(str(part) for part in version)
