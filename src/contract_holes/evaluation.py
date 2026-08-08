from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
from typing import Iterable

from .compiler import CompilerError, ForgeCompiler
from .models import Finding
from .project import ProjectIndex, ProjectIndexError
from .rules import DEFAULT_RULES
from .scanner import ScanError, Scanner, discover_sources


class EvaluationError(RuntimeError):
    pass


def load_evaluation_manifest(path: Path | str) -> dict[str, object]:
    manifest_path = Path(path).resolve()
    payload = _load_json(manifest_path, "evaluation manifest")
    if payload.get("schema_version") != "1.0":
        raise EvaluationError("evaluation manifest schema_version must be 1.0")
    if payload.get("evaluation_version") != "1.0":
        raise EvaluationError("evaluation_version must be 1.0")
    for name in ("corpus_version", "solc_version"):
        if not isinstance(payload.get(name), str) or not payload[name]:
            raise EvaluationError(f"evaluation manifest {name} must be a string")
    minimum_precision = _ratio(payload.get("minimum_precision"), "minimum_precision")
    minimum_recall = _ratio(payload.get("minimum_recall"), "minimum_recall")
    rule_ids = payload.get("rule_ids")
    expected_rule_ids = [rule.info.rule_id for rule in DEFAULT_RULES]
    if rule_ids != expected_rule_ids:
        raise EvaluationError(
            "evaluation manifest rule_ids must list every registered rule in order"
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != len(expected_rule_ids):
        raise EvaluationError("evaluation manifest must contain one case per rule")
    if [case.get("rule_id") for case in cases if isinstance(case, dict)] != rule_ids:
        raise EvaluationError("evaluation cases must follow rule_ids without duplicates")

    positive_total = 0
    safe_total = 0
    normalized_cases: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise EvaluationError(f"evaluation cases[{index}] must be an object")
        rule_id = str(case["rule_id"])
        fixture_value = case.get("fixture")
        if not isinstance(fixture_value, str) or not fixture_value:
            raise EvaluationError(f"evaluation case {rule_id} has no fixture")
        fixture = (manifest_path.parent / fixture_value).resolve()
        if not (fixture / "foundry.toml").is_file() or not (fixture / "src").is_dir():
            raise EvaluationError(f"evaluation fixture is incomplete: {fixture}")
        if "expectations" in case:
            expectation_value = case["expectations"]
            if not isinstance(expectation_value, str):
                raise EvaluationError(f"evaluation case {rule_id} expectations is invalid")
            labels = _load_json(
                (manifest_path.parent / expectation_value).resolve(),
                f"{rule_id} expectations",
            )
            if labels.get("rule_id") != rule_id:
                raise EvaluationError(f"evaluation expectations do not match {rule_id}")
        else:
            labels = case
        expected = labels.get("expected_findings")
        safe = labels.get("expected_clean_entries", labels.get("expected_clean"))
        if not isinstance(expected, list) or any(
            not isinstance(label, dict) for label in expected
        ):
            raise EvaluationError(f"evaluation {rule_id} positive labels are invalid")
        if not isinstance(safe, list) or any(
            not isinstance(label, str) or not label for label in safe
        ):
            raise EvaluationError(f"evaluation {rule_id} safe labels are invalid")
        if len(safe) != len(set(safe)):
            raise EvaluationError(f"evaluation {rule_id} safe labels are duplicated")
        serialized_expected = [json.dumps(label, sort_keys=True) for label in expected]
        if len(serialized_expected) != len(set(serialized_expected)):
            raise EvaluationError(f"evaluation {rule_id} positive labels are duplicated")
        if case.get("positive_labels") != len(expected):
            raise EvaluationError(f"evaluation {rule_id} positive label count changed")
        if case.get("safe_labels") != len(safe):
            raise EvaluationError(f"evaluation {rule_id} safe label count changed")
        positive_total += len(expected)
        safe_total += len(safe)
        normalized_cases.append(
            {
                "rule_id": rule_id,
                "fixture": fixture,
                "expected_findings": expected,
                "expected_clean_entries": safe,
            }
        )
    if payload.get("expected_positive_labels") != positive_total:
        raise EvaluationError("evaluation expected_positive_labels total changed")
    if payload.get("expected_safe_labels") != safe_total:
        raise EvaluationError("evaluation expected_safe_labels total changed")
    return {
        **payload,
        "minimum_precision": minimum_precision,
        "minimum_recall": minimum_recall,
        "manifest_path": manifest_path,
        "cases": normalized_cases,
    }


def evaluate_labelled_corpus(
    manifest_path: Path | str,
    *,
    offline: bool = True,
    compiler: ForgeCompiler | None = None,
) -> dict[str, object]:
    manifest = load_evaluation_manifest(manifest_path)
    scanner = Scanner()
    project_cache: dict[Path, tuple[list[Finding], ProjectIndex, tuple[str, ...]]] = {}
    rule_results: list[dict[str, object]] = []
    for case in manifest["cases"]:
        fixture = case["fixture"]
        if fixture not in project_cache:
            project_cache[fixture] = _scan_project(
                fixture,
                scanner,
                compiler=compiler,
                offline=offline,
            )
        findings, project, versions = project_cache[fixture]
        if not versions or any(
            not version.startswith(str(manifest["solc_version"]))
            for version in versions
        ):
            raise EvaluationError(
                f"fixture {fixture} did not compile with solc {manifest['solc_version']}"
            )
        available = _available_labels(project)
        safe = list(case["expected_clean_entries"])
        missing_safe = sorted(set(safe) - available)
        if missing_safe:
            raise EvaluationError(
                f"{case['rule_id']} safe labels do not exist: "
                + ", ".join(missing_safe)
            )
        rule_findings = [
            finding for finding in findings if finding.rule_id == case["rule_id"]
        ]
        rule_results.append(
            score_labelled_findings(
                str(case["rule_id"]),
                list(case["expected_findings"]),
                safe,
                rule_findings,
                minimum_precision=float(manifest["minimum_precision"]),
                minimum_recall=float(manifest["minimum_recall"]),
                path_root=fixture,
            )
        )
    true_positives = sum(int(result["true_positives"]) for result in rule_results)
    false_positives = sum(int(result["false_positives"]) for result in rule_results)
    false_negatives = sum(int(result["false_negatives"]) for result in rule_results)
    micro_precision = _metric(true_positives, false_positives)
    micro_recall = _metric(true_positives, false_negatives)
    macro_precision = sum(float(result["precision"]) for result in rule_results) / len(
        rule_results
    )
    macro_recall = sum(float(result["recall"]) for result in rule_results) / len(
        rule_results
    )
    failed_rules = [
        str(result["rule_id"])
        for result in rule_results
        if result["status"] != "passed"
    ]
    return {
        "schema_version": "1.0",
        "evaluation_version": "1.0",
        "corpus_version": manifest["corpus_version"],
        "solc_version": manifest["solc_version"],
        "thresholds": {
            "minimum_precision": manifest["minimum_precision"],
            "minimum_recall": manifest["minimum_recall"],
        },
        "labels": {
            "positive": manifest["expected_positive_labels"],
            "safe": manifest["expected_safe_labels"],
        },
        "aggregate": {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "micro_precision": round(micro_precision, 6),
            "micro_recall": round(micro_recall, 6),
            "macro_precision": round(macro_precision, 6),
            "macro_recall": round(macro_recall, 6),
        },
        "rules": rule_results,
        "status": "failed" if failed_rules else "passed",
        "failed_rules": failed_rules,
    }


def score_labelled_findings(
    rule_id: str,
    expected_findings: list[dict[str, object]],
    safe_labels: list[str],
    actual_findings: Iterable[Finding],
    *,
    minimum_precision: float = 0.8,
    minimum_recall: float = 0.8,
    path_root: Path | None = None,
) -> dict[str, object]:
    actual = list(actual_findings)
    unmatched = list(range(len(actual)))
    missed: list[dict[str, object]] = []
    matched = 0
    for expected in expected_findings:
        match = next(
            (
                index
                for index in unmatched
                if _finding_matches(actual[index], expected)
            ),
            None,
        )
        if match is None:
            missed.append(expected)
        else:
            unmatched.remove(match)
            matched += 1
    extras = [actual[index] for index in unmatched]
    safe_violations = sorted(
        {
            scope
            for finding in actual
            if (scope := _finding_scope(finding)) in set(safe_labels)
        }
    )
    precision = _metric(matched, len(extras))
    recall = _metric(matched, len(missed))
    status = (
        "passed"
        if precision >= minimum_precision
        and recall >= minimum_recall
        and not safe_violations
        else "failed"
    )
    return {
        "rule_id": rule_id,
        "positive_labels": len(expected_findings),
        "safe_labels": len(safe_labels),
        "actual_findings": len(actual),
        "true_positives": matched,
        "false_positives": len(extras),
        "false_negatives": len(missed),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "status": status,
        "false_positive_findings": [
            _finding_identity(finding, path_root) for finding in extras
        ],
        "false_negative_labels": missed,
        "safe_label_violations": safe_violations,
    }


def evaluation_exit_status(payload: dict[str, object]) -> int:
    return 1 if payload.get("status") == "failed" else 0


def _scan_project(
    fixture: Path,
    scanner: Scanner,
    *,
    compiler: ForgeCompiler | None,
    offline: bool,
) -> tuple[list[Finding], ProjectIndex, tuple[str, ...]]:
    try:
        files = discover_sources([fixture / "src"])
        compilation = (compiler or ForgeCompiler()).compile(
            files,
            project_root=fixture,
            offline=offline,
        )
        project = ProjectIndex(compilation)
        findings: list[Finding] = []
        for path in files:
            indexed = project.source_for_path(path)
            if indexed is None:
                raise EvaluationError(f"compiler produced no source model for {path}")
            findings.extend(scanner.scan_source(indexed.source))
    except (CompilerError, ProjectIndexError, ScanError) as exc:
        raise EvaluationError(str(exc)) from exc
    return findings, project, compilation.compiler_versions


def _actual_value(finding: Finding, field: str) -> object:
    if field == "path":
        return None
    if field == "trace_kinds":
        trace = finding.metadata.get("trace")
        return (
            [event.get("kind") for event in trace if isinstance(event, dict)]
            if isinstance(trace, list)
            else None
        )
    if field == "entry_function" and finding.rule_id == "SOL011":
        return _proxy_entry(finding.metadata)
    if hasattr(finding, field):
        return getattr(finding, field)
    return finding.metadata.get(field)


def _finding_matches(finding: Finding, expected: dict[str, object]) -> bool:
    for field, value in expected.items():
        if field == "path":
            actual_path = finding.path.as_posix()
            if not actual_path.endswith(str(value).replace("\\", "/")):
                return False
        elif _actual_value(finding, field) != value:
            return False
    return True


def _proxy_entry(metadata: dict[str, object]) -> object:
    if metadata.get("initializer"):
        return metadata["initializer"]
    if metadata.get("issue_kind") == "proxy-storage-collision":
        trace = metadata.get("trace")
        if isinstance(trace, list) and len(trace) > 1 and isinstance(trace[1], dict):
            return trace[1].get("owner")
    return None


def _finding_scope(finding: Finding) -> str:
    if finding.rule_id == "SOL011":
        return str(_proxy_entry(finding.metadata) or finding.metadata.get("contract"))
    for field in ("entry_function", "function"):
        value = finding.metadata.get(field)
        if isinstance(value, str):
            return value
    return ""


def _finding_identity(
    finding: Finding, path_root: Path | None
) -> dict[str, object]:
    path = finding.path
    if path_root is not None:
        try:
            path = path.resolve().relative_to(path_root.resolve())
        except ValueError:
            pass
    return {
        "fingerprint": replace(finding, path=path).fingerprint,
        "path": path.as_posix(),
        "line": finding.line,
        "rule_id": finding.rule_id,
        "scope": _finding_scope(finding),
    }


def _available_labels(project: ProjectIndex) -> set[str]:
    labels = {
        str(contract.get("name"))
        for contract in project.contracts_by_id.values()
        if contract.get("name")
    }
    for function in project.functions_by_id.values():
        contract = project.enclosing_node(function, "ContractDefinition")
        if contract is not None and contract.get("name") and function.get("name"):
            labels.add(f"{contract['name']}.{function['name']}")
    return labels


def _metric(true_positives: int, errors: int) -> float:
    denominator = true_positives + errors
    return true_positives / denominator if denominator else 0.0


def _ratio(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvaluationError(f"evaluation {label} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0 or result > 1:
        raise EvaluationError(f"evaluation {label} must be between 0 and 1")
    return result


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"could not read {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvaluationError(f"{label} root must be an object")
    return payload
