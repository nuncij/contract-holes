import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.ai_triage import (
    AITriageError,
    explain_report,
    prepare_evidence_bundle,
    request_ai_annotations,
)
from contract_holes.cli import main
from contract_holes.models import Finding, Severity


class FakeResponse:
    def __init__(self, payload: object):
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _maximum: int) -> bytes:
        return self.body


def finding(
    path: str,
    line: int,
    rule_id: str,
    *,
    scope: str = "Vault.withdraw",
) -> dict[str, object]:
    return Finding(
        rule_id=rule_id,
        severity=Severity.HIGH,
        title=f"{rule_id} title",
        message=f"{rule_id} deterministic message",
        path=Path(path),
        line=line,
        column=5,
        excerpt=f"evidence_{rule_id}()",
        recommendation=f"Review {rule_id}",
        confidence="high",
        metadata={
            "entry_function": scope,
            "evidence": "compiler-data-flow",
            "trace": [{"kind": "entry", "line": line}],
        },
    ).to_dict()


def write_report(path: Path, findings: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "files_scanned": 1,
                "finding_count": len(findings),
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def response_payload(annotation: dict[str, object], *, status: str = "completed"):
    return {
        "id": "resp_test",
        "status": status,
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps({"groups": [annotation]}),
                    }
                ],
            }
        ],
    }


class AITriageTests(unittest.TestCase):
    def test_prepare_groups_by_path_and_scope_with_deterministic_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            findings = [
                finding("contracts/Vault.sol", 20, "SOL008"),
                finding("contracts/Vault.sol", 10, "SOL005"),
                finding("contracts/Token.sol", 7, "SOL012", scope="Token.deposit"),
            ]
            write_report(report, findings)
            expected_digest = hashlib.sha256(report.read_bytes()).hexdigest()

            first = prepare_evidence_bundle(report)
            second = prepare_evidence_bundle(report)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "1.0")
        self.assertEqual(first["group_count"], 2)
        self.assertEqual(first["finding_count"], 3)
        self.assertEqual(first["source_report_sha256"], expected_digest)
        vault = next(
            group
            for group in first["groups"]
            if group["correlation"]["path"] == "contracts/Vault.sol"
        )
        self.assertEqual(
            [item["rule_id"] for item in vault["findings"]],
            ["SOL005", "SOL008"],
        )
        self.assertTrue(
            all(":metadata" in item["evidence_id"] for item in vault["evidence"][3::4])
        )

    def test_rejects_modified_fingerprint_and_duplicate_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            item = finding("Vault.sol", 10, "SOL005")
            item["fingerprint"] = "0" * 16
            write_report(report, [item])
            with self.assertRaisesRegex(AITriageError, "fingerprint does not match"):
                prepare_evidence_bundle(report)

            valid = finding("Vault.sol", 10, "SOL005")
            write_report(report, [valid, valid])
            with self.assertRaisesRegex(AITriageError, "duplicate"):
                prepare_evidence_bundle(report)

    def test_responses_request_uses_strict_schema_and_validates_annotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            write_report(report, [finding("Vault.sol", 10, "SOL005")])
            bundle = prepare_evidence_bundle(report)
        group = bundle["groups"][0]
        evidence_id = group["evidence"][0]["evidence_id"]
        annotation = {
            "group_id": group["group_id"],
            "summary": "The scanner records an interaction-before-effect signal.",
            "evidence_refs": [evidence_id],
            "review_questions": ["Does a guard dominate this interaction?"],
        }
        requests = []

        def opener(request, *, timeout):
            requests.append((request, timeout))
            return FakeResponse(response_payload(annotation))

        response_id, annotations = request_ai_annotations(
            bundle,
            "secret-key",
            model="gpt-test",
            timeout_seconds=12.5,
            opener=opener,
        )

        request, timeout = requests[0]
        request_body = json.loads(request.data)
        self.assertEqual(response_id, "resp_test")
        self.assertEqual(annotations, [annotation])
        self.assertEqual(timeout, 12.5)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-key")
        self.assertFalse(request_body["store"])
        self.assertTrue(request_body["text"]["format"]["strict"])
        self.assertEqual(request_body["text"]["format"]["type"], "json_schema")
        self.assertIn(group["group_id"], json.dumps(request_body))

    def test_rejects_unknown_evidence_missing_groups_refusal_and_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            write_report(report, [finding("Vault.sol", 10, "SOL005")])
            bundle = prepare_evidence_bundle(report)
        group_id = bundle["groups"][0]["group_id"]
        bad = {
            "group_id": group_id,
            "summary": "Unsupported",
            "evidence_refs": ["invented:evidence"],
            "review_questions": [],
        }
        with self.assertRaisesRegex(AITriageError, "evidence refs"):
            request_ai_annotations(
                bundle,
                "key",
                model="gpt-test",
                timeout_seconds=1,
                opener=lambda *_args, **_kwargs: FakeResponse(response_payload(bad)),
            )

        missing = response_payload(bad)
        missing["output"][0]["content"][0]["text"] = json.dumps({"groups": []})
        with self.assertRaisesRegex(AITriageError, "omitted groups"):
            request_ai_annotations(
                bundle,
                "key",
                model="gpt-test",
                timeout_seconds=1,
                opener=lambda *_args, **_kwargs: FakeResponse(missing),
            )

        refusal = {
            "id": "resp_refusal",
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}
            ],
        }
        with self.assertRaisesRegex(AITriageError, "refused"):
            request_ai_annotations(
                bundle,
                "key",
                model="gpt-test",
                timeout_seconds=1,
                opener=lambda *_args, **_kwargs: FakeResponse(refusal),
            )

        incomplete = {"id": "resp_partial", "status": "incomplete", "output": []}
        with self.assertRaisesRegex(AITriageError, "not completed"):
            request_ai_annotations(
                bundle,
                "key",
                model="gpt-test",
                timeout_seconds=1,
                opener=lambda *_args, **_kwargs: FakeResponse(incomplete),
            )

    def test_explain_envelope_retains_authoritative_group_and_marks_ai_untrusted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            write_report(report, [finding("Vault.sol", 10, "SOL005")])
            bundle = prepare_evidence_bundle(report)
            group = bundle["groups"][0]
            annotation = {
                "group_id": group["group_id"],
                "summary": "Review the cited ordering signal.",
                "evidence_refs": [group["evidence"][0]["evidence_id"]],
                "review_questions": [],
            }
            payload = explain_report(
                report,
                "key",
                model="gpt-test",
                opener=lambda *_args, **_kwargs: FakeResponse(
                    response_payload(annotation)
                ),
            )

        self.assertEqual(payload["response_id"], "resp_test")
        self.assertEqual(payload["groups"][0]["findings"], group["findings"])
        self.assertEqual(
            payload["groups"][0]["ai_annotation"]["status"],
            "untrusted-model-explanation",
        )

    def test_cli_prepare_is_offline_and_online_uses_named_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            write_report(report, [finding("Vault.sol", 10, "SOL005")])
            output = io.StringIO()
            with (
                patch.dict(os.environ, {}, clear=True),
                contextlib.redirect_stdout(output),
            ):
                status = main(["explain", str(report), "--prepare"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["group_count"], 1)

            output = io.StringIO()
            expected = {"schema_version": "1.0", "groups": []}
            with (
                patch.dict(os.environ, {"TEST_OPENAI_KEY": "key"}, clear=True),
                patch("contract_holes.cli.explain_report", return_value=expected) as explain,
                contextlib.redirect_stdout(output),
            ):
                status = main(
                    [
                        "explain",
                        str(report),
                        "--api-key-env",
                        "TEST_OPENAI_KEY",
                        "--model",
                        "gpt-test",
                        "--timeout",
                        "9",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue()), expected)
            explain.assert_called_once_with(
                str(report), "key", model="gpt-test", timeout_seconds=9.0
            )


if __name__ == "__main__":
    unittest.main()
