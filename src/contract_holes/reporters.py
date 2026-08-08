from __future__ import annotations

import json
from pathlib import Path

from .models import Finding, RuleInfo, Severity
from .schema import (
    REPORT_SCHEMA_VERSION,
    SARIF_LEVELS,
    SARIF_SCHEMA_URI,
    SARIF_SECURITY_SEVERITY,
    SARIF_VERSION,
    validate_report_payload,
    validate_sarif_payload,
)


COLORS = {
    Severity.CRITICAL: "\033[1;35m",
    Severity.HIGH: "\033[1;31m",
    Severity.MEDIUM: "\033[1;33m",
    Severity.LOW: "\033[1;36m",
    Severity.INFO: "\033[1;34m",
}
RESET = "\033[0m"


def text_report(findings: list[Finding], files_scanned: int, *, color: bool = False) -> str:
    if not findings:
        noun = "file" if files_scanned == 1 else "files"
        return f"No findings in {files_scanned} Solidity {noun}."

    blocks: list[str] = []
    for finding in findings:
        label = finding.severity.name
        if color:
            label = f"{COLORS[finding.severity]}{label}{RESET}"
        blocks.append(
            "\n".join(
                [
                    f"{label} {finding.rule_id} — {finding.title}",
                    f"  {finding.path}:{finding.line}:{finding.column}",
                    f"  {finding.excerpt}",
                    f"  {finding.message}",
                    f"  Fix: {finding.recommendation}",
                    f"  Confidence: {finding.confidence}  Fingerprint: {finding.fingerprint}",
                ]
            )
        )
    counts = {severity: 0 for severity in Severity}
    for finding in findings:
        counts[finding.severity] += 1
    summary_parts = [
        f"{counts[item]} {item.name.lower()}"
        for item in reversed(Severity)
        if counts[item]
    ]
    noun = "file" if files_scanned == 1 else "files"
    blocks.append(f"Found {len(findings)} issue(s) in {files_scanned} {noun}: " + ", ".join(summary_parts))
    return "\n\n".join(blocks)


def json_report(
    findings: list[Finding],
    files_scanned: int,
    *,
    baseline: dict[str, object] | None = None,
) -> str:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "files_scanned": files_scanned,
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
        **({"baseline": baseline} if baseline is not None else {}),
    }
    validate_report_payload(payload)
    return json.dumps(payload, indent=2, sort_keys=True)


def sarif_report(findings: list[Finding], rule_infos: list[RuleInfo]) -> str:
    rules = [
        {
            "id": info.rule_id,
            "name": info.title,
            "shortDescription": {"text": info.description},
            "help": {"text": info.recommendation},
            "properties": {
                "security-severity": SARIF_SECURITY_SEVERITY[info.severity],
                "confidence": info.confidence,
            },
        }
        for info in rule_infos
    ]
    results = [
        {
            "ruleId": finding.rule_id,
            "level": SARIF_LEVELS[finding.severity],
            "message": {"text": finding.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": _uri(finding.path)},
                        "region": {
                            "startLine": finding.line,
                            "startColumn": finding.column,
                            **({"endLine": finding.end_line} if finding.end_line else {}),
                        },
                    }
                }
            ],
            "partialFingerprints": {"primaryLocationLineHash": finding.fingerprint},
            "properties": {
                **finding.metadata,
                "severity": str(finding.severity),
                "confidence": finding.confidence,
            },
        }
        for finding in findings
    ]
    payload = {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "contract-holes",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    validate_sarif_payload(payload)
    return json.dumps(payload, indent=2, sort_keys=True)


def _uri(path: Path) -> str:
    try:
        return path.resolve().as_uri()
    except ValueError:
        return str(path)
