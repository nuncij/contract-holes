from copy import deepcopy
from importlib.resources import files
import json
from pathlib import Path
import unittest

from contract_holes.models import Finding, RuleInfo, Severity
from contract_holes.reporters import json_report, sarif_report
from contract_holes.scanner import Scanner
from contract_holes.schema import (
    FINDING_REQUIRED_FIELDS,
    REPORT_REQUIRED_FIELDS,
    SARIF_LEVELS,
    SARIF_SECURITY_SEVERITY,
    SchemaValidationError,
    validate_report_payload,
    validate_sarif_payload,
)


class OutputSchemaTests(unittest.TestCase):
    def test_packaged_json_schemas_match_frozen_required_fields(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        report_schema = json.loads(
            schema_directory.joinpath("report-1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        sarif_schema = json.loads(
            schema_directory.joinpath("sarif-2.1.0-profile.schema.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(set(report_schema["required"]), REPORT_REQUIRED_FIELDS)
        self.assertEqual(
            set(report_schema["$defs"]["finding"]["required"]),
            FINDING_REQUIRED_FIELDS,
        )
        self.assertEqual(report_schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(sarif_schema["properties"]["version"]["const"], "2.1.0")

    def test_json_report_exact_v1_shape_and_additive_consumer_compatibility(self) -> None:
        findings, count = Scanner().scan_paths(
            [Path("tests/fixtures/VulnerableVault.sol")]
        )
        payload = json.loads(json_report(findings, count))

        self.assertEqual(set(payload), REPORT_REQUIRED_FIELDS)
        self.assertTrue(payload["findings"])
        self.assertEqual(set(payload["findings"][0]), FINDING_REQUIRED_FIELDS)
        validate_report_payload(payload)

        future_minor = deepcopy(payload)
        future_minor["optional_summary"] = {"producer": "future"}
        future_minor["findings"][0]["optional_evidence"] = []
        validate_report_payload(future_minor)

    def test_json_validator_rejects_count_boolean_and_changed_fingerprint(self) -> None:
        findings, count = Scanner().scan_paths([Path("tests/fixtures/SafeVault.sol")])
        payload = json.loads(json_report(findings, count))
        payload["finding_count"] = False
        with self.assertRaisesRegex(SchemaValidationError, "finding_count"):
            validate_report_payload(payload)

        findings, count = Scanner().scan_paths(
            [Path("tests/fixtures/VulnerableVault.sol")]
        )
        payload = json.loads(json_report(findings, count))
        payload["findings"][0]["fingerprint"] = "0" * 16
        with self.assertRaisesRegex(SchemaValidationError, "fingerprint v1"):
            validate_report_payload(payload)

    def test_sarif_profile_maps_severity_and_protects_canonical_properties(self) -> None:
        findings: list[Finding] = []
        infos: list[RuleInfo] = []
        for index, severity in enumerate(Severity, 1):
            rule_id = f"SOL9{index:02d}"
            findings.append(
                Finding(
                    rule_id=rule_id,
                    severity=severity,
                    title=f"Finding {index}",
                    message="deterministic evidence",
                    path=Path(f"Contract{index}.sol"),
                    line=index,
                    column=1,
                    excerpt=f"evidence{index}();",
                    recommendation="review",
                    confidence="high",
                    metadata={"severity": "critical", "confidence": "low"},
                )
            )
            infos.append(
                RuleInfo(
                    rule_id,
                    severity,
                    f"Finding {index}",
                    "description",
                    "review",
                    "high",
                )
            )

        payload = json.loads(sarif_report(findings, infos))
        validate_sarif_payload(payload)
        rules = payload["runs"][0]["tool"]["driver"]["rules"]
        results = payload["runs"][0]["results"]

        for finding, rule, result in zip(findings, rules, results):
            self.assertEqual(result["level"], SARIF_LEVELS[finding.severity])
            self.assertEqual(
                rule["properties"]["security-severity"],
                SARIF_SECURITY_SEVERITY[finding.severity],
            )
            self.assertEqual(result["properties"]["severity"], str(finding.severity))
            self.assertEqual(result["properties"]["confidence"], "high")
            self.assertEqual(
                result["partialFingerprints"]["primaryLocationLineHash"],
                finding.fingerprint,
            )

        invalid = deepcopy(payload)
        invalid["runs"][0]["results"][0]["ruleId"] = "SOL999"
        with self.assertRaisesRegex(SchemaValidationError, "not declared"):
            validate_sarif_payload(invalid)


if __name__ == "__main__":
    unittest.main()
