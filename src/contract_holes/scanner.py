from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from .models import Finding, Severity
from .rules import DEFAULT_RULES, Rule
from .source import SoliditySource


DEFAULT_EXCLUDES = frozenset(
    {".git", ".venv", "node_modules", "lib", "vendor", "out", "cache", "artifacts"}
)


class ScanError(RuntimeError):
    pass


class Scanner:
    def __init__(self, rules: Sequence[Rule] = DEFAULT_RULES):
        self.rules = tuple(rules)

    def scan_source(self, source: SoliditySource) -> list[Finding]:
        findings = [finding for rule in self.rules for finding in rule.scan(source)]
        return sorted(findings, key=_finding_sort_key)

    def scan_paths(
        self,
        paths: Iterable[Path | str],
        *,
        minimum_severity: Severity = Severity.INFO,
        include_dependencies: bool = False,
    ) -> tuple[list[Finding], int]:
        files = discover_sources(paths, include_dependencies=include_dependencies)
        findings: list[Finding] = []
        for path in files:
            try:
                source = SoliditySource.from_path(path)
            except (OSError, UnicodeError) as exc:
                raise ScanError(f"could not read {path}: {exc}") from exc
            findings.extend(
                finding
                for finding in self.scan_source(source)
                if finding.severity >= minimum_severity
            )
        return sorted(findings, key=_finding_sort_key), len(files)


def discover_sources(
    paths: Iterable[Path | str], *, include_dependencies: bool = False
) -> list[Path]:
    discovered: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            raise ScanError(f"path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() != ".sol":
                raise ScanError(f"expected a .sol file: {path}")
            discovered.add(path)
            continue
        for candidate in path.rglob("*.sol"):
            relative_parts = candidate.relative_to(path).parts
            if not include_dependencies and any(
                part in DEFAULT_EXCLUDES for part in relative_parts[:-1]
            ):
                continue
            discovered.add(candidate)
    return sorted(discovered, key=lambda item: str(item))


def _finding_sort_key(finding: Finding) -> tuple[int, str, int, int, str]:
    return (-int(finding.severity), str(finding.path), finding.line, finding.column, finding.rule_id)
