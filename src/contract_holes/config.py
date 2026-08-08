from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    tomllib = None

from .models import Severity
from .limits import ScanLimits
from .rules import DEFAULT_RULES


class ConfigError(RuntimeError):
    pass


RULE_IDS = frozenset(rule.info.rule_id for rule in DEFAULT_RULES)


@dataclass(frozen=True, slots=True)
class HolesConfig:
    source: Path | None = None
    paths: tuple[Path, ...] = ()
    exclude: tuple[str, ...] = ()
    include_dependencies: bool = False
    minimum_severity: Severity = Severity.INFO
    enabled_rules: tuple[str, ...] | None = None
    disabled_rules: tuple[str, ...] = ()
    severity_overrides: dict[str, Severity] = field(default_factory=dict)
    compiler_enabled: bool = False
    compiler_offline: bool = False
    limits: ScanLimits = ScanLimits()


def discover_config(start: Path | str | None = None) -> Path | None:
    current = Path(start or Path.cwd()).resolve()
    if current.is_file() or not current.is_dir():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / ".holes.toml"
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | str) -> HolesConfig:
    source = Path(path).resolve()
    if not source.is_file():
        raise ConfigError(f"configuration file does not exist: {source}")
    try:
        raw = source.read_bytes()
        payload = (
            tomllib.loads(raw.decode("utf-8"))
            if tomllib is not None
            else _parse_toml_subset(raw.decode("utf-8"), source)
        )
    except (OSError, UnicodeError) as exc:
        raise ConfigError(f"could not read configuration {source}: {exc}") from exc
    except Exception as exc:
        if tomllib is not None and isinstance(exc, tomllib.TOMLDecodeError):
            raise ConfigError(f"invalid TOML in {source}: {exc}") from exc
        if isinstance(exc, ConfigError):
            raise
        raise
    return _validate_config(payload, source)


def selected_rules(config: HolesConfig):
    enabled = set(config.enabled_rules or RULE_IDS)
    enabled.difference_update(config.disabled_rules)
    return tuple(rule for rule in DEFAULT_RULES if rule.info.rule_id in enabled)


def _validate_config(payload: object, source: Path) -> HolesConfig:
    root = _table(payload, "configuration root")
    _unknown_keys(
        root, {"schema_version", "scan", "rules", "compiler", "limits"}, "root"
    )
    schema_version = root.get("schema_version", 1)
    if isinstance(schema_version, bool) or schema_version != 1:
        raise ConfigError("schema_version must be 1")

    scan = _table(root.get("scan", {}), "[scan]")
    rules = _table(root.get("rules", {}), "[rules]")
    compiler = _table(root.get("compiler", {}), "[compiler]")
    limits = _table(root.get("limits", {}), "[limits]")
    _unknown_keys(
        scan,
        {"paths", "exclude", "include_dependencies", "minimum_severity"},
        "[scan]",
    )
    _unknown_keys(rules, {"enabled", "disabled", "severity"}, "[rules]")
    _unknown_keys(compiler, {"enabled", "offline"}, "[compiler]")
    _unknown_keys(
        limits,
        {
            "max_files",
            "max_source_bytes",
            "compiler_timeout_seconds",
            "scan_timeout_seconds",
            "max_python_memory_mb",
        },
        "[limits]",
    )

    raw_paths = _string_list(scan.get("paths", []), "scan.paths")
    paths = tuple(
        candidate if candidate.is_absolute() else source.parent / candidate
        for candidate in (Path(value) for value in raw_paths)
    )
    exclude = tuple(_string_list(scan.get("exclude", []), "scan.exclude"))
    include_dependencies = _boolean(
        scan.get("include_dependencies", False), "scan.include_dependencies"
    )
    minimum_severity = _severity(
        scan.get("minimum_severity", "info"), "scan.minimum_severity"
    )

    enabled_values = rules.get("enabled")
    enabled = (
        tuple(_rule_list(enabled_values, "rules.enabled"))
        if enabled_values is not None
        else None
    )
    disabled = tuple(_rule_list(rules.get("disabled", []), "rules.disabled"))
    overlap = set(enabled or ()) & set(disabled)
    if overlap:
        raise ConfigError(
            "rules cannot be both enabled and disabled: " + ", ".join(sorted(overlap))
        )
    severity_table = _table(rules.get("severity", {}), "[rules.severity]")
    unknown_rule_ids = set(severity_table) - RULE_IDS
    if unknown_rule_ids:
        raise ConfigError(
            "unknown rule ID in rules.severity: "
            + ", ".join(sorted(unknown_rule_ids))
        )
    severity_overrides = {
        rule_id: _severity(value, f"rules.severity.{rule_id}")
        for rule_id, value in severity_table.items()
    }

    compiler_enabled = _boolean(
        compiler.get("enabled", False), "compiler.enabled"
    )
    compiler_offline = _boolean(
        compiler.get("offline", False), "compiler.offline"
    )
    if compiler_offline and not compiler_enabled:
        raise ConfigError("compiler.offline = true requires compiler.enabled = true")

    defaults = ScanLimits()
    try:
        scan_limits = ScanLimits(
            max_files=_positive_integer(
                limits.get("max_files", defaults.max_files), "limits.max_files"
            ),
            max_source_bytes=_positive_integer(
                limits.get("max_source_bytes", defaults.max_source_bytes),
                "limits.max_source_bytes",
            ),
            compiler_timeout_seconds=_positive_number(
                limits.get(
                    "compiler_timeout_seconds", defaults.compiler_timeout_seconds
                ),
                "limits.compiler_timeout_seconds",
            ),
            scan_timeout_seconds=_positive_number(
                limits.get("scan_timeout_seconds", defaults.scan_timeout_seconds),
                "limits.scan_timeout_seconds",
            ),
            max_python_memory_bytes=_positive_integer(
                limits.get(
                    "max_python_memory_mb",
                    defaults.max_python_memory_bytes // (1024 * 1024),
                ),
                "limits.max_python_memory_mb",
            )
            * 1024
            * 1024,
        )
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    return HolesConfig(
        source=source,
        paths=tuple(path.resolve() for path in paths),
        exclude=exclude,
        include_dependencies=include_dependencies,
        minimum_severity=minimum_severity,
        enabled_rules=enabled,
        disabled_rules=disabled,
        severity_overrides=severity_overrides,
        compiler_enabled=compiler_enabled,
        compiler_offline=compiler_offline,
        limits=scan_limits,
    )


def _table(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a table")
    return value


def _unknown_keys(table: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(table) - allowed
    if unknown:
        raise ConfigError(f"unknown {label} setting: {', '.join(sorted(unknown))}")


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise ConfigError(f"{label} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ConfigError(f"{label} must not contain duplicates")
    return list(value)


def _rule_list(value: object, label: str) -> list[str]:
    values = _string_list(value, label)
    unknown = set(values) - RULE_IDS
    if unknown:
        raise ConfigError(f"unknown rule ID in {label}: {', '.join(sorted(unknown))}")
    return values


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{label} must be true or false")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{label} must be a positive integer")
    return value


def _positive_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{label} must be a positive number")
    result = float(value)
    if result == float("inf") or result != result:
        raise ConfigError(f"{label} must be finite")
    return result


def _severity(value: object, label: str) -> Severity:
    if not isinstance(value, str):
        raise ConfigError(f"{label} must be a severity string")
    try:
        return Severity.parse(value)
    except ValueError as exc:
        raise ConfigError(f"{label}: {exc}") from exc


def _parse_toml_subset(text: str, source: Path) -> dict[str, object]:
    """Parse the CONFIG-001 scalar/string-array subset on Python 3.10."""
    root: dict[str, object] = {}
    table = root
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            table = root
            for name in line[1:-1].split("."):
                name = name.strip()
                if not name:
                    raise ConfigError(f"invalid table at {source}:{line_number}")
                value = table.setdefault(name, {})
                if not isinstance(value, dict):
                    raise ConfigError(f"duplicate table at {source}:{line_number}")
                table = value
            continue
        if "=" not in line:
            raise ConfigError(f"invalid setting at {source}:{line_number}")
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if not key or key in table:
            raise ConfigError(f"invalid or duplicate key at {source}:{line_number}")
        table[key] = _parse_subset_value(raw_value, source, line_number)
    return root


def _strip_comment(line: str) -> str:
    quote = ""
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
        elif character == "\\" and quote == '"':
            escaped = True
        elif character in {'"', "'"}:
            quote = "" if quote == character else character if not quote else quote
        elif character == "#" and not quote:
            return line[:index]
    return line


def _parse_subset_value(value: str, source: Path, line_number: int) -> object:
    if value in {"true", "false"}:
        return value == "true"
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise ConfigError(f"invalid value at {source}:{line_number}") from exc
    if isinstance(parsed, (str, int, float, list)) and not isinstance(parsed, bool):
        return parsed
    raise ConfigError(f"unsupported value at {source}:{line_number}")
