from __future__ import annotations

import hashlib
import re

from .models import Severity


REPORT_SCHEMA_VERSION = "1.0"
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{16}\Z")
RULE_ID_PATTERN = re.compile(r"SOL[0-9]{3}\Z")
CONFIDENCE_VALUES = frozenset({"low", "medium", "high"})
SARIF_LEVELS = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}
SARIF_SECURITY_SEVERITY = {
    Severity.CRITICAL: "9.0",
    Severity.HIGH: "8.0",
    Severity.MEDIUM: "5.0",
    Severity.LOW: "3.0",
    Severity.INFO: "1.0",
}
REPORT_REQUIRED_FIELDS = frozenset(
    {"schema_version", "files_scanned", "finding_count", "findings"}
)
FINDING_REQUIRED_FIELDS = frozenset(
    {
        "rule_id",
        "severity",
        "title",
        "message",
        "path",
        "line",
        "column",
        "excerpt",
        "recommendation",
        "confidence",
        "end_line",
        "metadata",
        "fingerprint",
    }
)


class SchemaValidationError(ValueError):
    pass


def validate_report_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise SchemaValidationError("report root must be an object")
    missing = REPORT_REQUIRED_FIELDS - set(payload)
    if missing:
        raise SchemaValidationError(
            "report is missing required fields: " + ", ".join(sorted(missing))
        )
    if payload.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise SchemaValidationError(
            f"report schema_version must be {REPORT_SCHEMA_VERSION}"
        )
    files_scanned = payload.get("files_scanned")
    if not _nonnegative_integer(files_scanned):
        raise SchemaValidationError("files_scanned must be a non-negative integer")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise SchemaValidationError("findings must be an array")
    finding_count = payload.get("finding_count")
    if not _nonnegative_integer(finding_count) or finding_count != len(findings):
        raise SchemaValidationError("finding_count must equal the findings length")
    fingerprints: set[str] = set()
    for index, finding in enumerate(findings):
        _validate_finding(finding, index)
        fingerprint = str(finding["fingerprint"])
        if fingerprint in fingerprints:
            raise SchemaValidationError(f"duplicate finding fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)
    if "baseline" in payload:
        _validate_baseline_summary(payload["baseline"])


def validate_sarif_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise SchemaValidationError("SARIF root must be an object")
    if payload.get("$schema") != SARIF_SCHEMA_URI:
        raise SchemaValidationError("SARIF $schema URI is unsupported")
    if payload.get("version") != SARIF_VERSION:
        raise SchemaValidationError(f"SARIF version must be {SARIF_VERSION}")
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) != 1 or not isinstance(runs[0], dict):
        raise SchemaValidationError("SARIF must contain exactly one run")
    run = runs[0]
    tool = run.get("tool")
    driver = tool.get("driver") if isinstance(tool, dict) else None
    if not isinstance(driver, dict) or driver.get("name") != "contract-holes":
        raise SchemaValidationError("SARIF driver must be contract-holes")
    rules = driver.get("rules")
    if not isinstance(rules, list):
        raise SchemaValidationError("SARIF driver rules must be an array")
    declared: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not RULE_ID_PATTERN.fullmatch(
            str(rule.get("id", ""))
        ):
            raise SchemaValidationError(f"SARIF rules[{index}] has an invalid ID")
        rule_id = str(rule["id"])
        if rule_id in declared:
            raise SchemaValidationError(f"duplicate SARIF rule ID: {rule_id}")
        declared.add(rule_id)
        properties = rule.get("properties")
        if not isinstance(properties, dict):
            raise SchemaValidationError(
                f"SARIF rule {rule_id} properties must be an object"
            )
        score = properties.get("security-severity")
        if score not in set(SARIF_SECURITY_SEVERITY.values()):
            raise SchemaValidationError(
                f"SARIF rule {rule_id} has invalid security-severity"
            )
        if properties.get("confidence") not in CONFIDENCE_VALUES:
            raise SchemaValidationError(f"SARIF rule {rule_id} has invalid confidence")
    results = run.get("results")
    if not isinstance(results, list):
        raise SchemaValidationError("SARIF results must be an array")
    fingerprints: set[str] = set()
    for index, result in enumerate(results):
        fingerprint = _validate_sarif_result(result, index, declared)
        if fingerprint in fingerprints:
            raise SchemaValidationError(f"duplicate SARIF fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)


def _validate_finding(finding: object, index: int) -> None:
    if not isinstance(finding, dict):
        raise SchemaValidationError(f"findings[{index}] must be an object")
    missing = FINDING_REQUIRED_FIELDS - set(finding)
    if missing:
        raise SchemaValidationError(
            f"findings[{index}] is missing: " + ", ".join(sorted(missing))
        )
    string_fields = (
        "rule_id",
        "severity",
        "title",
        "message",
        "path",
        "excerpt",
        "recommendation",
        "confidence",
        "fingerprint",
    )
    for name in string_fields:
        if not isinstance(finding.get(name), str):
            raise SchemaValidationError(f"findings[{index}].{name} must be a string")
    rule_id = str(finding["rule_id"])
    if not RULE_ID_PATTERN.fullmatch(rule_id):
        raise SchemaValidationError(f"findings[{index}].rule_id is invalid")
    try:
        Severity.parse(str(finding["severity"]))
    except ValueError as exc:
        raise SchemaValidationError(f"findings[{index}].severity is invalid") from exc
    if finding["confidence"] not in CONFIDENCE_VALUES:
        raise SchemaValidationError(f"findings[{index}].confidence is invalid")
    for name in ("line", "column"):
        if not _positive_integer(finding.get(name)):
            raise SchemaValidationError(
                f"findings[{index}].{name} must be a positive integer"
            )
    end_line = finding.get("end_line")
    if end_line is not None and (
        not _positive_integer(end_line) or end_line < finding["line"]
    ):
        raise SchemaValidationError(
            f"findings[{index}].end_line must be null or at least line"
        )
    if not isinstance(finding.get("metadata"), dict):
        raise SchemaValidationError(f"findings[{index}].metadata must be an object")
    fingerprint = str(finding["fingerprint"])
    if not FINGERPRINT_PATTERN.fullmatch(fingerprint):
        raise SchemaValidationError(f"findings[{index}].fingerprint is invalid")
    material = (
        f"{rule_id}\0{finding['path']}\0{finding['line']}\0"
        f"{str(finding['excerpt']).strip()}"
    )
    expected = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    if fingerprint != expected:
        raise SchemaValidationError(
            f"findings[{index}].fingerprint does not match fingerprint v1"
        )


def _validate_baseline_summary(value: object) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        raise SchemaValidationError("baseline must contain a string path")
    for name in ("new", "existing", "resolved"):
        if not _nonnegative_integer(value.get(name)):
            raise SchemaValidationError(
                f"baseline.{name} must be a non-negative integer"
            )


def _validate_sarif_result(
    result: object, index: int, declared: set[str]
) -> str:
    if not isinstance(result, dict):
        raise SchemaValidationError(f"SARIF results[{index}] must be an object")
    rule_id = result.get("ruleId")
    if not isinstance(rule_id, str) or rule_id not in declared:
        raise SchemaValidationError(f"SARIF results[{index}] rule is not declared")
    message = result.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("text"), str):
        raise SchemaValidationError(f"SARIF results[{index}] message is invalid")
    properties = result.get("properties")
    if not isinstance(properties, dict):
        raise SchemaValidationError(f"SARIF results[{index}] properties are invalid")
    try:
        severity = Severity.parse(str(properties.get("severity")))
    except ValueError as exc:
        raise SchemaValidationError(
            f"SARIF results[{index}] severity is invalid"
        ) from exc
    if result.get("level") != SARIF_LEVELS[severity]:
        raise SchemaValidationError(
            f"SARIF results[{index}] level does not match severity"
        )
    if properties.get("confidence") not in CONFIDENCE_VALUES:
        raise SchemaValidationError(f"SARIF results[{index}] confidence is invalid")
    locations = result.get("locations")
    if not isinstance(locations, list) or len(locations) != 1:
        raise SchemaValidationError(
            f"SARIF results[{index}] must have exactly one location"
        )
    location = locations[0]
    physical = location.get("physicalLocation") if isinstance(location, dict) else None
    artifact = physical.get("artifactLocation") if isinstance(physical, dict) else None
    region = physical.get("region") if isinstance(physical, dict) else None
    if not isinstance(artifact, dict) or not isinstance(artifact.get("uri"), str):
        raise SchemaValidationError(f"SARIF results[{index}] artifact URI is invalid")
    if not isinstance(region, dict):
        raise SchemaValidationError(f"SARIF results[{index}] region is invalid")
    for name in ("startLine", "startColumn"):
        if not _positive_integer(region.get(name)):
            raise SchemaValidationError(
                f"SARIF results[{index}] {name} must be a positive integer"
            )
    if "endLine" in region and (
        not _positive_integer(region["endLine"])
        or region["endLine"] < region["startLine"]
    ):
        raise SchemaValidationError(f"SARIF results[{index}] endLine is invalid")
    partial = result.get("partialFingerprints")
    fingerprint = (
        partial.get("primaryLocationLineHash") if isinstance(partial, dict) else None
    )
    if not isinstance(fingerprint, str) or not FINGERPRINT_PATTERN.fullmatch(
        fingerprint
    ):
        raise SchemaValidationError(f"SARIF results[{index}] fingerprint is invalid")
    return fingerprint


def _positive_integer(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _nonnegative_integer(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0
