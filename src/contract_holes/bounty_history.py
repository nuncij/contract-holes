from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from . import __version__
from .bounty_io import payload_sha256
from .models import Finding, Severity
from .rules import DEFAULT_RULES
from .scanner import ScanError, Scanner


class BountyHistoryError(RuntimeError):
    pass


HISTORY_SCHEMA_VERSION = "1.0"
HISTORY_EVALUATION_VERSION = "1.0"
MODEL_STATUSES = frozenset({"supported", "out-of-model"})
SPLITS = frozenset({"calibration", "holdout"})
REQUIRED_EVIDENCE_FIELDS = (
    "path",
    "line",
    "column",
    "excerpt",
    "recommendation",
    "confidence",
)


def load_bounty_history_manifest(path: Path | str) -> dict[str, object]:
    manifest_path = Path(path).resolve()
    payload = _load_json(manifest_path, "historical corpus manifest")
    if payload.get("schema_version") != HISTORY_SCHEMA_VERSION:
        raise BountyHistoryError("historical manifest schema_version must be 1.0")
    if payload.get("evaluation_version") != HISTORY_EVALUATION_VERSION:
        raise BountyHistoryError("historical manifest evaluation_version must be 1.0")
    for field in ("corpus_version", "solc_version"):
        _nonempty_text(payload.get(field), f"historical manifest {field}")
    _date(payload.get("labels_frozen_on"), "labels_frozen_on")
    thresholds = _thresholds(payload.get("thresholds"))
    methodology = payload.get("methodology")
    if not isinstance(methodology, dict):
        raise BountyHistoryError("historical manifest methodology must be an object")
    for field in ("fixture_policy", "label_policy", "claim"):
        _nonempty_text(methodology.get(field), f"methodology {field}")

    compiler_config = _relative_regular_file(
        manifest_path,
        payload.get("compiler_config"),
        "compiler_config",
    )
    _verify_file_sha256(
        compiler_config,
        payload.get("compiler_config_sha256"),
        "compiler config",
    )
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 10:
        raise BountyHistoryError("historical manifest requires at least ten cases")
    rule_ids = {rule.info.rule_id for rule in DEFAULT_RULES}
    normalized: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for index, raw_case in enumerate(cases):
        if not isinstance(raw_case, dict):
            raise BountyHistoryError(f"historical cases[{index}] must be an object")
        case_id = _nonempty_text(raw_case.get("case_id"), f"cases[{index}].case_id")
        if case_id in seen_ids:
            raise BountyHistoryError(f"duplicate historical case ID: {case_id}")
        seen_ids.add(case_id)
        split = raw_case.get("split")
        if split not in SPLITS:
            raise BountyHistoryError(f"historical case {case_id} has invalid split")
        project = _nonempty_text(raw_case.get("project"), f"{case_id} project")
        _nonempty_text(raw_case.get("title"), f"{case_id} title")
        incident_on = _date(raw_case.get("incident_on"), f"{case_id} incident_on")
        disclosed_on = _date(
            raw_case.get("disclosed_on"), f"{case_id} disclosed_on"
        )
        if disclosed_on < incident_on:
            raise BountyHistoryError(
                f"historical case {case_id} disclosure predates the incident/report"
            )
        _nonempty_text(raw_case.get("root_cause"), f"{case_id} root_cause")
        _nonempty_text(raw_case.get("support_limit"), f"{case_id} support_limit")
        model_status = raw_case.get("model_status")
        if model_status not in MODEL_STATUSES:
            raise BountyHistoryError(
                f"historical case {case_id} model_status must be supported or out-of-model"
            )
        labels = _expected_findings(
            raw_case.get("expected_findings"), case_id, rule_ids
        )
        if model_status == "supported" and not labels:
            raise BountyHistoryError(
                f"supported historical case {case_id} needs expected findings"
            )
        if model_status == "out-of-model" and labels:
            raise BountyHistoryError(
                f"out-of-model historical case {case_id} cannot expect findings"
            )
        fixture = _relative_regular_file(
            manifest_path,
            raw_case.get("fixture"),
            f"{case_id} fixture",
            suffix=".sol",
        )
        _verify_file_sha256(
            fixture,
            raw_case.get("fixture_sha256"),
            f"{case_id} fixture",
        )
        source = _reference(raw_case.get("source"), f"{case_id} source")
        immutable_id = str(source["immutable_id"])
        if immutable_id in seen_sources:
            raise BountyHistoryError(
                f"historical cases must have distinct immutable sources: {immutable_id}"
            )
        seen_sources.add(immutable_id)
        disclosure = _disclosure(
            raw_case.get("disclosure"), f"{case_id} disclosure"
        )
        provenance = raw_case.get("provenance")
        if not isinstance(provenance, dict):
            raise BountyHistoryError(f"{case_id} provenance must be an object")
        if (
            provenance.get("fixture_kind") != "locally-authored-reduction"
            or provenance.get("fixture_license") != "MIT"
            or provenance.get("upstream_code_copied") is not False
        ):
            raise BountyHistoryError(
                f"{case_id} provenance must identify an MIT local reduction with no copied upstream code"
            )
        normalized.append(
            {
                **raw_case,
                "project": project,
                "expected_findings": labels,
                "fixture_path": fixture,
                "source": source,
                "disclosure": disclosure,
            }
        )

    projects = {str(case["project"]) for case in normalized}
    if len(projects) < 5:
        raise BountyHistoryError(
            "historical manifest requires at least five independent projects"
        )
    splits = {str(case["split"]) for case in normalized}
    if splits != SPLITS:
        raise BountyHistoryError(
            "historical manifest requires distinct calibration and holdout cases"
        )
    supported_projects = {
        str(case["project"])
        for case in normalized
        if case["model_status"] == "supported"
    }
    if len(supported_projects) < 3:
        raise BountyHistoryError(
            "historical manifest requires three independent supported projects"
        )
    labels_sha256 = payload_sha256(
        [
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "project": case["project"],
                "root_cause": case["root_cause"],
                "model_status": case["model_status"],
                "support_limit": case["support_limit"],
                "expected_findings": case["expected_findings"],
                "fixture_sha256": case["fixture_sha256"],
                "source_immutable_id": case["source"]["immutable_id"],
            }
            for case in normalized
        ]
    )
    return {
        **payload,
        "manifest_path": manifest_path,
        "compiler_config_path": compiler_config,
        "thresholds": thresholds,
        "cases": normalized,
        "labels_sha256": labels_sha256,
    }


def evaluate_bounty_history(
    manifest_path: Path | str,
    *,
    offline: bool = True,
    scanner: Scanner | None = None,
) -> dict[str, object]:
    manifest = load_bounty_history_manifest(manifest_path)
    corpus_root = Path(manifest["manifest_path"]).parent
    fixtures = [Path(case["fixture_path"]) for case in manifest["cases"]]
    try:
        findings, files_scanned = (scanner or Scanner()).scan_paths(
            fixtures,
            minimum_severity=Severity.INFO,
            compile_sources=True,
            compiler_offline=offline,
        )
    except ScanError as exc:
        raise BountyHistoryError(str(exc)) from exc
    by_fixture: dict[Path, list[Finding]] = {fixture.resolve(): [] for fixture in fixtures}
    for finding in findings:
        resolved = finding.path.resolve()
        if resolved not in by_fixture:
            raise BountyHistoryError(
                f"scanner returned a finding outside the historical corpus: {finding.path}"
            )
        by_fixture[resolved].append(finding)

    case_results: list[dict[str, object]] = []
    total_expected = 0
    total_matched = 0
    total_candidates = 0
    total_rejected = 0
    complete_evidence = 0
    compiler_evidence = 0
    supported_cases_with_evidence = 0
    for case in manifest["cases"]:
        actual = by_fixture[Path(case["fixture_path"]).resolve()]
        expected = list(case["expected_findings"])
        matched_indices, missed = _match_findings(expected, actual)
        unexpected = [
            finding for index, finding in enumerate(actual) if index not in matched_indices
        ]
        total_expected += len(expected)
        total_matched += len(matched_indices)
        total_candidates += len(actual)
        total_rejected += len(unexpected)
        complete_evidence += sum(_evidence_complete(finding) for finding in actual)
        compiler_evidence += sum(
            str(finding.metadata.get("evidence", "")).startswith("compiler-")
            for finding in actual
        )
        supported = case["model_status"] == "supported"
        if supported and expected and not missed:
            supported_cases_with_evidence += 1
        case_results.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "project": case["project"],
                "model_status": case["model_status"],
                "support_limit": case["support_limit"],
                "expected_candidates": len(expected),
                "matched_candidates": len(matched_indices),
                "investigation_count": len(actual),
                "rejected_candidates": len(unexpected),
                "missed_labels": missed,
                "candidates": [
                    _finding_record(finding, corpus_root) for finding in actual
                ],
                "status": (
                    "evidence-produced"
                    if supported and expected and not missed
                    else "missed"
                    if supported
                    else "out-of-model-recorded"
                ),
            }
        )

    precision = _ratio(total_matched, total_candidates)
    recall = _ratio(total_matched, total_expected)
    completeness = _ratio(complete_evidence, total_candidates)
    thresholds = manifest["thresholds"]
    gate_checks = {
        "candidate_precision": precision
        >= thresholds["minimum_candidate_precision"],
        "supported_class_recall": recall
        >= thresholds["minimum_supported_recall"],
        "evidence_completeness": completeness
        >= thresholds["minimum_evidence_completeness"],
        "independent_supported_cases": supported_cases_with_evidence
        >= thresholds["minimum_supported_cases_with_evidence"],
    }
    passed = all(gate_checks.values())
    result: dict[str, object] = {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "evaluation_version": HISTORY_EVALUATION_VERSION,
        "corpus_version": manifest["corpus_version"],
        "scanner_version": __version__,
        "solc_version": manifest["solc_version"],
        "labels_frozen_on": manifest["labels_frozen_on"],
        "labels_sha256": manifest["labels_sha256"],
        "execution_policy": {
            "offline": offline,
            "network_writes": False,
            "funded_credentials": False,
        },
        "corpus": {
            "cases": len(case_results),
            "projects": len({str(case["project"]) for case in manifest["cases"]}),
            "files_scanned": files_scanned,
            "supported_cases": sum(
                case["model_status"] == "supported" for case in manifest["cases"]
            ),
            "out_of_model_cases": [
                case["case_id"]
                for case in manifest["cases"]
                if case["model_status"] == "out-of-model"
            ],
            "splits": {
                split: sum(case["split"] == split for case in manifest["cases"])
                for split in sorted(SPLITS)
            },
        },
        "thresholds": thresholds,
        "metrics": {
            "candidate_precision": precision,
            "supported_class_recall": recall,
            "investigation_count": total_candidates,
            "rejected_candidates": total_rejected,
            "evidence_completeness": completeness,
            "compiler_evidence_rate": _ratio(compiler_evidence, total_candidates),
            "supported_cases_with_evidence": supported_cases_with_evidence,
        },
        "split_metrics": {
            split: _split_metrics(case_results, split) for split in sorted(SPLITS)
        },
        "gate_checks": gate_checks,
        "product_claim": {
            "decision": "go" if passed else "no-go",
            "statement": (
                "Contract Holes produced useful investigation evidence for at least "
                "three independent historical supported cases. Human validation is still required."
                if passed
                else "The historical evidence gate failed; no M7 usefulness claim may be made."
            ),
            "does_not_mean": [
                "the historical vulnerabilities were automatically confirmed",
                "the scanner is complete or equivalent to an audit",
                "a finding is exploitable, in scope, unique, or eligible for payout",
            ],
        },
        "cases": case_results,
        "limitations": [
            "Fixtures are locally authored reductions, not the complete historical deployments.",
            "A matched rule is useful investigation evidence, not proof of the disclosed impact.",
            "Out-of-model labels are preserved even when generic candidates require rejection.",
            "Remote references are provenance metadata and are not fetched during evaluation.",
        ],
        "status": "passed" if passed else "failed",
    }
    result["result_sha256"] = payload_sha256(result)
    return result


def bounty_history_exit_status(result: dict[str, object]) -> int:
    return 0 if result.get("status") == "passed" else 1


def _expected_findings(
    value: object, case_id: str, rule_ids: set[str]
) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise BountyHistoryError(f"{case_id} expected_findings must be an array")
    normalized: list[dict[str, object]] = []
    for index, label in enumerate(value):
        if not isinstance(label, dict) or set(label) - {"rule_id", "metadata"}:
            raise BountyHistoryError(
                f"{case_id} expected_findings[{index}] has invalid fields"
            )
        rule_id = label.get("rule_id")
        if rule_id not in rule_ids:
            raise BountyHistoryError(
                f"{case_id} expected_findings[{index}] has unknown rule_id"
            )
        metadata = label.get("metadata", {})
        if not isinstance(metadata, dict) or any(
            not isinstance(key, str) or not isinstance(item, (str, int, bool))
            for key, item in metadata.items()
        ):
            raise BountyHistoryError(
                f"{case_id} expected_findings[{index}] metadata is invalid"
            )
        normalized.append({"rule_id": rule_id, **({"metadata": metadata} if metadata else {})})
    if len({json.dumps(item, sort_keys=True) for item in normalized}) != len(normalized):
        raise BountyHistoryError(f"{case_id} expected_findings contains duplicates")
    return normalized


def _reference(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise BountyHistoryError(f"{label} must be an object")
    required = {"kind", "url", "immutable_id", "redistribution"}
    if set(value) != required:
        raise BountyHistoryError(f"{label} fields must be {', '.join(sorted(required))}")
    for field in required:
        _nonempty_text(value.get(field), f"{label} {field}")
    _https_url(value["url"], f"{label} url")
    return dict(value)


def _disclosure(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {
        "publisher",
        "url",
        "retrieved_on",
    }:
        raise BountyHistoryError(
            f"{label} requires publisher, url, and retrieved_on"
        )
    _nonempty_text(value.get("publisher"), f"{label} publisher")
    _https_url(value.get("url"), f"{label} url")
    _date(value.get("retrieved_on"), f"{label} retrieved_on")
    return dict(value)


def _thresholds(value: object) -> dict[str, float | int]:
    if not isinstance(value, dict):
        raise BountyHistoryError("historical thresholds must be an object")
    expected = {
        "minimum_candidate_precision",
        "minimum_supported_recall",
        "minimum_evidence_completeness",
        "minimum_supported_cases_with_evidence",
    }
    if set(value) != expected:
        raise BountyHistoryError("historical threshold fields are invalid")
    result: dict[str, float | int] = {}
    for name in expected - {"minimum_supported_cases_with_evidence"}:
        item = value[name]
        if not isinstance(item, (int, float)) or isinstance(item, bool) or not 0 <= item <= 1:
            raise BountyHistoryError(f"historical threshold {name} must be in [0, 1]")
        result[name] = float(item)
    count = value["minimum_supported_cases_with_evidence"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 3:
        raise BountyHistoryError(
            "minimum_supported_cases_with_evidence must be an integer of at least 3"
        )
    result["minimum_supported_cases_with_evidence"] = count
    return result


def _match_findings(
    expected: list[dict[str, object]], actual: list[Finding]
) -> tuple[set[int], list[dict[str, object]]]:
    matched: set[int] = set()
    missed: list[dict[str, object]] = []
    for label in expected:
        index = next(
            (
                candidate
                for candidate, finding in enumerate(actual)
                if candidate not in matched and _finding_matches(label, finding)
            ),
            None,
        )
        if index is None:
            missed.append(label)
        else:
            matched.add(index)
    return matched, missed


def _finding_matches(label: dict[str, object], finding: Finding) -> bool:
    if finding.rule_id != label.get("rule_id"):
        return False
    metadata = label.get("metadata", {})
    return isinstance(metadata, dict) and all(
        finding.metadata.get(key) == value for key, value in metadata.items()
    )


def _finding_record(finding: Finding, root: Path) -> dict[str, object]:
    try:
        relative = finding.path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise BountyHistoryError(
            f"historical finding path escapes the corpus: {finding.path}"
        ) from exc
    stable_fingerprint = hashlib.sha256(
        "\0".join(
            (finding.rule_id, relative, str(finding.line), finding.excerpt.strip())
        ).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "rule_id": finding.rule_id,
        "path": relative,
        "line": finding.line,
        "column": finding.column,
        "severity": str(finding.severity),
        "confidence": finding.confidence,
        "evidence": finding.metadata.get("evidence", "source-pattern"),
        "issue_kind": finding.metadata.get("issue_kind"),
        "fingerprint": stable_fingerprint,
    }


def _evidence_complete(finding: Finding) -> bool:
    record = finding.to_dict()
    return all(record.get(field) not in (None, "") for field in REQUIRED_EVIDENCE_FIELDS)


def _split_metrics(
    cases: Iterable[dict[str, object]], split: str
) -> dict[str, object]:
    selected = [case for case in cases if case["split"] == split]
    expected = sum(int(case["expected_candidates"]) for case in selected)
    matched = sum(int(case["matched_candidates"]) for case in selected)
    candidates = sum(int(case["investigation_count"]) for case in selected)
    rejected = sum(int(case["rejected_candidates"]) for case in selected)
    return {
        "cases": len(selected),
        "candidate_precision": _ratio(matched, candidates),
        "supported_class_recall": _ratio(matched, expected),
        "investigation_count": candidates,
        "rejected_candidates": rejected,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 1.0


def _load_json(path: Path, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise BountyHistoryError(f"{label} is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BountyHistoryError(f"could not read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BountyHistoryError(f"{label} root must be an object")
    return payload


def _relative_regular_file(
    manifest_path: Path,
    value: object,
    label: str,
    *,
    suffix: str | None = None,
) -> Path:
    text = _nonempty_text(value, label)
    raw = Path(text)
    if raw.is_absolute() or ".." in raw.parts:
        raise BountyHistoryError(f"{label} must be a normalized relative path")
    path = (manifest_path.parent / raw).resolve()
    try:
        path.relative_to(manifest_path.parent)
    except ValueError as exc:
        raise BountyHistoryError(f"{label} escapes the corpus directory") from exc
    if path.is_symlink() or not path.is_file() or (suffix and path.suffix != suffix):
        raise BountyHistoryError(f"{label} is not an expected regular file: {path}")
    return path


def _verify_file_sha256(path: Path, expected: object, label: str) -> None:
    digest = _digest(expected, f"{label} SHA-256")
    try:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BountyHistoryError(f"could not hash {label}: {exc}") from exc
    if actual != digest:
        raise BountyHistoryError(f"{label} SHA-256 changed")


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise BountyHistoryError(f"{label} is invalid")
    return value


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyHistoryError(f"{label} must be a non-empty string")
    return value


def _date(value: object, label: str) -> date:
    text = _nonempty_text(value, label)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise BountyHistoryError(f"{label} must be YYYY-MM-DD") from exc


def _https_url(value: object, label: str) -> str:
    text = _nonempty_text(value, label)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise BountyHistoryError(f"{label} must be a credential-free HTTPS URL")
    return text
