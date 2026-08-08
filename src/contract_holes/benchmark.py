from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import platform
import time
import tracemalloc
from typing import Iterable

from .compiler import CompilerError, ForgeCompiler, find_project_root
from .models import Finding
from .project import ProjectIndex, ProjectIndexError
from .scanner import ScanError, Scanner, discover_sources
from .source import SoliditySource


PERFORMANCE_REGRESSION_RATIO = 1.20
PERFORMANCE_REGRESSION_PERCENT = round(
    (PERFORMANCE_REGRESSION_RATIO - 1.0) * 100.0, 2
)


class BenchmarkError(RuntimeError):
    pass


def benchmark_paths(
    paths: Iterable[Path | str],
    *,
    include_dependencies: bool = False,
    offline: bool = False,
    expectations_path: Path | str | None = None,
    baseline_path: Path | str | None = None,
    compiler: ForgeCompiler | None = None,
) -> dict[str, object]:
    discovery_start = time.perf_counter_ns()
    try:
        files = discover_sources(paths, include_dependencies=include_dependencies)
    except ScanError as exc:
        raise BenchmarkError(str(exc)) from exc
    discovery_seconds = _elapsed(discovery_start)
    if not files:
        raise BenchmarkError("no Solidity source files found to benchmark")
    root = find_project_root(files)
    scanner = Scanner()

    source_start = time.perf_counter_ns()
    tracemalloc.start()
    try:
        source_findings = _scan_source_only(scanner, files)
        source_duration = _elapsed(source_start)
        _, source_peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    compiler_start = time.perf_counter_ns()
    tracemalloc.start()
    try:
        compile_start = time.perf_counter_ns()
        compilation = (compiler or ForgeCompiler()).compile(
            files,
            project_root=root,
            offline=offline,
        )
        compile_duration = _elapsed(compile_start)

        index_start = time.perf_counter_ns()
        project = ProjectIndex(compilation)
        index_duration = _elapsed(index_start)

        scan_start = time.perf_counter_ns()
        compiler_findings = _scan_compiler_sources(scanner, project, files)
        compiler_scan_duration = _elapsed(scan_start)
        compiler_duration = _elapsed(compiler_start)
        _, compiler_peak = tracemalloc.get_traced_memory()
    except (CompilerError, ProjectIndexError, ScanError) as exc:
        raise BenchmarkError(str(exc)) from exc
    finally:
        tracemalloc.stop()

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "benchmark_version": "1.0",
        "project_root": str(root),
        "inputs": {
            "files": len(files),
            "paths": [_relative(path, root) for path in files],
            "discovery_duration_seconds": discovery_seconds,
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "modes": {
            "source_only": {
                "duration_seconds": source_duration,
                "python_peak_bytes": source_peak,
                "findings": finding_summary(source_findings),
            },
            "compiler": {
                "duration_seconds": compiler_duration,
                "python_peak_bytes": compiler_peak,
                "compiler_versions": list(compilation.compiler_versions),
                "compiled_sources": len(compilation.sources),
                "diagnostics": len(compilation.diagnostics),
                "phases": {
                    "compile_duration_seconds": compile_duration,
                    "index_duration_seconds": index_duration,
                    "scan_duration_seconds": compiler_scan_duration,
                },
                "findings": finding_summary(compiler_findings),
            },
        },
    }
    resolved_expectations = _expectations_path(expectations_path, root)
    payload["correctness"] = evaluate_correctness(payload, resolved_expectations, root)
    payload["performance_comparison"] = compare_with_baseline(
        payload, Path(baseline_path) if baseline_path is not None else None, root
    )
    return payload


def benchmark_exit_status(payload: dict[str, object]) -> int:
    correctness = payload.get("correctness")
    if isinstance(correctness, dict) and correctness.get("status") == "failed":
        return 1
    return 0


def finding_summary(findings: Iterable[Finding]) -> dict[str, object]:
    values = tuple(findings)
    by_rule = Counter(finding.rule_id for finding in values)
    by_severity = Counter(str(finding.severity) for finding in values)
    return {
        "finding_count": len(values),
        "rule_counts": dict(sorted(by_rule.items())),
        "severity_counts": dict(sorted(by_severity.items())),
    }


def evaluate_correctness(
    payload: dict[str, object], expectations_path: Path | None, root: Path
) -> dict[str, object]:
    if expectations_path is None:
        return {
            "status": "not_checked",
            "expectations_path": None,
            "mismatches": [],
        }
    expectations = _load_json(expectations_path, "expectations")
    expected_modes = expectations.get("benchmark_expectations")
    if not isinstance(expected_modes, dict):
        return {
            "status": "not_checked",
            "expectations_path": _relative(expectations_path, root),
            "mismatches": ["expectations contain no benchmark_expectations object"],
        }

    mismatches: list[str] = []
    modes = payload.get("modes", {})
    for mode_name in ("source_only", "compiler"):
        expected = expected_modes.get(mode_name)
        actual_mode = modes.get(mode_name) if isinstance(modes, dict) else None
        actual = actual_mode.get("findings") if isinstance(actual_mode, dict) else None
        if not isinstance(expected, dict) or not isinstance(actual, dict):
            mismatches.append(f"{mode_name}: missing expected or actual finding summary")
            continue
        for field in ("finding_count", "rule_counts"):
            if actual.get(field) != expected.get(field):
                mismatches.append(
                    f"{mode_name}.{field}: expected {expected.get(field)!r}, "
                    f"got {actual.get(field)!r}"
                )
    return {
        "status": "failed" if mismatches else "passed",
        "expectations_path": _relative(expectations_path, root),
        "mismatches": mismatches,
    }


def compare_with_baseline(
    payload: dict[str, object], baseline_path: Path | None, root: Path
) -> dict[str, object]:
    if baseline_path is None:
        return {
            "status": "not_compared",
            "baseline_path": None,
            "regression_threshold_percent": PERFORMANCE_REGRESSION_PERCENT,
            "metrics": [],
            "regressions": [],
        }
    baseline = _load_json(baseline_path, "benchmark baseline")
    metric_paths = (
        "modes.source_only.duration_seconds",
        "modes.source_only.python_peak_bytes",
        "modes.compiler.duration_seconds",
        "modes.compiler.python_peak_bytes",
        "modes.compiler.phases.compile_duration_seconds",
        "modes.compiler.phases.index_duration_seconds",
        "modes.compiler.phases.scan_duration_seconds",
    )
    metrics: list[dict[str, object]] = []
    regressions: list[str] = []
    for metric_path in metric_paths:
        current = _nested_number(payload, metric_path)
        previous = _nested_number(baseline, metric_path)
        if current is None or previous is None or previous <= 0:
            classification = "unavailable"
            ratio = None
            change_percent = None
        else:
            ratio = current / previous
            change_percent = (ratio - 1.0) * 100.0
            if ratio > PERFORMANCE_REGRESSION_RATIO:
                classification = "regression"
                regressions.append(metric_path)
            elif ratio < 1.0 / PERFORMANCE_REGRESSION_RATIO:
                classification = "improvement"
            else:
                classification = "stable"
        metrics.append(
            {
                "name": metric_path,
                "baseline": previous,
                "current": current,
                "ratio": round(ratio, 4) if ratio is not None else None,
                "change_percent": (
                    round(change_percent, 2) if change_percent is not None else None
                ),
                "classification": classification,
            }
        )
    return {
        "status": "reported",
        "baseline_path": _relative(baseline_path, root),
        "regression_threshold_percent": PERFORMANCE_REGRESSION_PERCENT,
        "metrics": metrics,
        "regressions": regressions,
    }


def _scan_source_only(scanner: Scanner, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    try:
        for path in files:
            findings.extend(scanner.scan_source(SoliditySource.from_path(path)))
    except (OSError, UnicodeError) as exc:
        raise BenchmarkError(f"could not read Solidity source: {exc}") from exc
    return findings


def _scan_compiler_sources(
    scanner: Scanner, project: ProjectIndex, files: list[Path]
) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        indexed = project.source_for_path(path)
        if indexed is None:
            raise BenchmarkError(f"compiler produced no AST for requested source: {path}")
        source = SoliditySource(
            path,
            indexed.source.text,
            ast=indexed.ast,
            project_index=project,
            compilation_id=indexed.compilation_id,
        )
        findings.extend(scanner.scan_source(source))
    return findings


def _expectations_path(value: Path | str | None, root: Path) -> Path | None:
    if value is not None:
        path = Path(value)
        if not path.is_file():
            raise BenchmarkError(f"expectations file does not exist: {path}")
        return path.resolve()
    automatic = root / "expectations.json"
    return automatic if automatic.is_file() else None


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError(f"could not load {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkError(f"{label} must contain a JSON object: {path}")
    return payload


def _nested_number(payload: dict[str, object], dotted_path: str) -> float | None:
    current: object = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if isinstance(current, bool) or not isinstance(current, (int, float)):
        return None
    return float(current)


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _elapsed(start_ns: int) -> float:
    return round((time.perf_counter_ns() - start_ns) / 1_000_000_000, 6)
