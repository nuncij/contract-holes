from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from .compiler import CompilerError, ForgeCompiler
from .models import Finding, Severity
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
    ):
        self.rules = tuple(rules)
        self.compiler = compiler or ForgeCompiler()

    def scan_source(self, source: SoliditySource) -> list[Finding]:
        findings = [finding for rule in self.rules for finding in rule.scan(source)]
        return sorted(findings, key=_finding_sort_key)

    def scan_paths(
        self,
        paths: Iterable[Path | str],
        *,
        minimum_severity: Severity = Severity.INFO,
        include_dependencies: bool = False,
        compile_sources: bool = False,
        compiler_offline: bool = False,
    ) -> tuple[list[Finding], int]:
        files = discover_sources(paths, include_dependencies=include_dependencies)
        project_index: ProjectIndex | None = None
        if compile_sources:
            try:
                compilation = self.compiler.compile(files, offline=compiler_offline)
                project_index = ProjectIndex(compilation)
            except (CompilerError, ProjectIndexError) as exc:
                raise ScanError(str(exc)) from exc
        findings: list[Finding] = []
        for path in files:
            try:
                indexed = project_index.source_for_path(path) if project_index else None
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
