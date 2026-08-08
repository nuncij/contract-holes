from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path
import time
import tracemalloc

from .compiler import CompilerError, ForgeCompiler
from .limits import ScanLimits
from .models import Finding, RuleInfo, Severity
from .project import ProjectIndex, ProjectIndexError
from .rules import DEFAULT_RULES, Rule
from .source import SoliditySource


DEFAULT_EXCLUDES = frozenset(
    {".git", ".venv", "node_modules", "lib", "vendor", "out", "cache", "artifacts"}
)


class ScanError(RuntimeError):
    pass


class Scanner:
    def __init__(
        self,
        rules: Sequence[Rule] = DEFAULT_RULES,
        compiler: ForgeCompiler | None = None,
        severity_overrides: dict[str, Severity] | None = None,
        limits: ScanLimits = ScanLimits(),
    ):
        self.rules = tuple(rules)
        self.compiler = compiler or ForgeCompiler(
            timeout=limits.compiler_timeout_seconds
        )
        self.severity_overrides = dict(severity_overrides or {})
        self.limits = limits

    @property
    def rule_infos(self) -> list[RuleInfo]:
        return [
            replace(
                rule.info,
                severity=self.severity_overrides.get(
                    rule.info.rule_id, rule.info.severity
                ),
            )
            for rule in self.rules
        ]

    def scan_source(self, source: SoliditySource) -> list[Finding]:
        findings = [
            replace(
                finding,
                severity=self.severity_overrides.get(
                    finding.rule_id, finding.severity
                ),
            )
            for rule in self.rules
            for finding in rule.scan(source)
        ]
        return sorted(findings, key=_finding_sort_key)

    def scan_paths(
        self,
        paths: Iterable[Path | str],
        *,
        minimum_severity: Severity = Severity.INFO,
        include_dependencies: bool = False,
        exclude_patterns: Sequence[str] = (),
        compile_sources: bool = False,
        compiler_offline: bool = False,
    ) -> tuple[list[Finding], int]:
        started = time.monotonic()
        already_tracing = tracemalloc.is_tracing()
        if not already_tracing:
            tracemalloc.start()
        memory_baseline, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        try:
            files = discover_sources(
                paths,
                include_dependencies=include_dependencies,
                exclude_patterns=exclude_patterns,
                max_files=self.limits.max_files,
            )
            self._check_limits(started, memory_baseline, "source discovery")
            self._check_source_bytes(files)
            self._check_limits(started, memory_baseline, "source sizing")
            project_index: ProjectIndex | None = None
            if compile_sources:
                try:
                    compilation = self.compiler.compile(
                        files, offline=compiler_offline
                    )
                    self._check_limits(started, memory_baseline, "compilation")
                    project_index = ProjectIndex(compilation)
                    self._check_limits(started, memory_baseline, "project indexing")
                except (CompilerError, ProjectIndexError) as exc:
                    raise ScanError(str(exc)) from exc
            findings: list[Finding] = []
            for path in files:
                try:
                    indexed = (
                        project_index.source_for_path(path)
                        if project_index
                        else None
                    )
                    if indexed:
                        source = SoliditySource(
                            path,
                            indexed.source.text,
                            ast=indexed.ast,
                            project_index=project_index,
                            compilation_id=indexed.compilation_id,
                        )
                    elif project_index:
                        raise ScanError(
                            f"compiler produced no AST for requested source: {path}"
                        )
                    else:
                        source = SoliditySource.from_path(path)
                except (OSError, UnicodeError) as exc:
                    raise ScanError(f"could not read {path}: {exc}") from exc
                findings.extend(
                    finding
                    for finding in self.scan_source(source)
                    if finding.severity >= minimum_severity
                )
                self._check_limits(started, memory_baseline, f"scanning {path}")
            return sorted(findings, key=_finding_sort_key), len(files)
        finally:
            if not already_tracing:
                tracemalloc.stop()

    def _check_source_bytes(self, files: Sequence[Path]) -> None:
        total = 0
        for path in files:
            try:
                total += path.stat().st_size
            except OSError as exc:
                raise ScanError(f"could not inspect source size {path}: {exc}") from exc
            if total > self.limits.max_source_bytes:
                raise ScanError(
                    "resource limit exceeded [source-bytes]: discovered Solidity "
                    f"sources total {total} bytes; maximum is "
                    f"{self.limits.max_source_bytes}"
                )

    def _check_limits(
        self, started: float, memory_baseline: int, phase: str
    ) -> None:
        elapsed = time.monotonic() - started
        if elapsed > self.limits.scan_timeout_seconds:
            raise ScanError(
                "resource limit exceeded [scan-time]: scan took "
                f"{elapsed:.3f} seconds by {phase}; maximum is "
                f"{self.limits.scan_timeout_seconds:g} seconds"
            )
        _, absolute_peak = tracemalloc.get_traced_memory()
        peak = max(0, absolute_peak - memory_baseline)
        if peak > self.limits.max_python_memory_bytes:
            raise ScanError(
                "resource limit exceeded [python-memory]: Python peak allocated "
                f"memory reached {peak} bytes by {phase}; maximum is "
                f"{self.limits.max_python_memory_bytes} bytes"
            )


def discover_sources(
    paths: Iterable[Path | str],
    *,
    include_dependencies: bool = False,
    exclude_patterns: Sequence[str] = (),
    max_files: int | None = None,
) -> list[Path]:
    discovered: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise ScanError(f"path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() != ".sol":
                raise ScanError(f"expected a .sol file: {path}")
            if _excluded(path.name, exclude_patterns):
                continue
            discovered.add(path)
            _check_file_limit(discovered, max_files)
            continue
        for candidate in path.rglob("*.sol"):
            relative_parts = candidate.relative_to(path).parts
            if not include_dependencies and any(
                part in DEFAULT_EXCLUDES for part in relative_parts[:-1]
            ):
                continue
            if _excluded(Path(*relative_parts).as_posix(), exclude_patterns):
                continue
            discovered.add(candidate)
            _check_file_limit(discovered, max_files)
    return sorted(discovered, key=lambda item: str(item))


def _finding_sort_key(finding: Finding) -> tuple[int, str, int, int, str]:
    return (
        -int(finding.severity),
        str(finding.path),
        finding.line,
        finding.column,
        finding.rule_id,
    )


def _excluded(relative_path: str, patterns: Sequence[str]) -> bool:
    return any(
        fnmatchcase(relative_path, pattern)
        or fnmatchcase(Path(relative_path).name, pattern)
        for pattern in patterns
    )


def _check_file_limit(discovered: set[Path], maximum: int | None) -> None:
    if maximum is not None and len(discovered) > maximum:
        raise ScanError(
            "resource limit exceeded [files]: discovered more than "
            f"{maximum} Solidity files"
        )
