from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import tempfile

from .models import Finding


class BaselineError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BaselineComparison:
    new_findings: tuple[Finding, ...]
    existing_findings: tuple[Finding, ...]
    resolved_fingerprints: tuple[str, ...]

    def summary(self) -> dict[str, int]:
        return {
            "new": len(self.new_findings),
            "existing": len(self.existing_findings),
            "resolved": len(self.resolved_fingerprints),
        }


def create_baseline(
    findings: list[Finding], baseline_path: Path | str
) -> dict[str, object]:
    path = Path(baseline_path).resolve()
    entries: dict[str, dict[str, object]] = {}
    for finding in findings:
        fingerprint = normalized_fingerprint(finding, path.parent)
        entries.setdefault(
            fingerprint,
            {
                "fingerprint": fingerprint,
                "rule_id": finding.rule_id,
                "path": _relative_path(finding.path, path.parent),
                "line": finding.line,
                "column": finding.column,
            },
        )
    return {
        "schema_version": "1.0",
        "baseline_version": "1.0",
        "path_base": "baseline-directory",
        "findings": sorted(
            entries.values(),
            key=lambda item: (
                str(item["path"]),
                int(item["line"]),
                int(item["column"]),
                str(item["rule_id"]),
            ),
        ),
    }


def write_baseline(
    findings: list[Finding],
    baseline_path: Path | str,
    *,
    overwrite: bool = False,
) -> dict[str, object]:
    path = Path(baseline_path).resolve()
    if path.exists() and not overwrite:
        raise BaselineError(
            f"refusing to overwrite baseline {path}; use --update-baseline"
        )
    if path.exists() and not path.is_file():
        raise BaselineError(f"baseline path is not a file: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = create_baseline(findings, path)
        rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(rendered)
        os.replace(temporary, path)
    except OSError as exc:
        if "temporary" in locals():
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise BaselineError(f"could not write baseline {path}: {exc}") from exc
    return payload


def load_baseline(path: Path | str) -> dict[str, object]:
    source = Path(path).resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BaselineError(f"could not read baseline {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BaselineError("baseline root must be an object")
    if payload.get("schema_version") != "1.0":
        raise BaselineError("unsupported baseline schema_version")
    if payload.get("baseline_version") != "1.0":
        raise BaselineError("unsupported baseline_version")
    if payload.get("path_base") != "baseline-directory":
        raise BaselineError("unsupported baseline path_base")
    entries = payload.get("findings")
    if not isinstance(entries, list):
        raise BaselineError("baseline findings must be an array")
    fingerprints: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(
            entry.get("fingerprint"), str
        ):
            raise BaselineError(
                f"baseline findings[{index}] must contain a fingerprint"
            )
        fingerprint = str(entry["fingerprint"])
        if fingerprint in fingerprints:
            raise BaselineError(f"duplicate baseline fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)
    return payload


def compare_baseline(
    findings: list[Finding],
    baseline: dict[str, object],
    baseline_path: Path | str,
) -> BaselineComparison:
    root = Path(baseline_path).resolve().parent
    entries = baseline["findings"]
    known = {str(entry["fingerprint"]) for entry in entries}
    current = {
        normalized_fingerprint(finding, root): finding for finding in findings
    }
    new_findings = tuple(
        finding
        for fingerprint, finding in current.items()
        if fingerprint not in known
    )
    existing_findings = tuple(
        finding
        for fingerprint, finding in current.items()
        if fingerprint in known
    )
    return BaselineComparison(
        new_findings=tuple(sorted(new_findings, key=_finding_sort_key)),
        existing_findings=tuple(sorted(existing_findings, key=_finding_sort_key)),
        resolved_fingerprints=tuple(sorted(known - set(current))),
    )


def normalized_fingerprint(finding: Finding, root: Path | str) -> str:
    relative = _relative_path(finding.path, Path(root).resolve())
    return replace(finding, path=Path(relative)).fingerprint


def _relative_path(path: Path, root: Path) -> str:
    absolute = path.resolve()
    try:
        return absolute.relative_to(root).as_posix()
    except ValueError:
        return Path(os.path.relpath(absolute, root)).as_posix()


def _finding_sort_key(finding: Finding) -> tuple[int, str, int, int, str]:
    return (
        -int(finding.severity),
        str(finding.path),
        finding.line,
        finding.column,
        finding.rule_id,
    )
