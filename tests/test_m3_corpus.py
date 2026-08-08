from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


CORPUS_ROOT = Path("tests/fixtures/m3_corpus").resolve()
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_labels(expectations: dict[str, object]) -> list[str]:
    values = expectations.get(
        "expected_clean_entries", expectations.get("expected_clean", [])
    )
    return [str(value) for value in values]


class M3CorpusManifestTests(unittest.TestCase):
    def test_manifest_versions_every_m3_positive_and_safe_label(self) -> None:
        manifest = load_json(MANIFEST_PATH)
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["corpus_version"], "m3-1")
        self.assertEqual(manifest["solc_version"], "0.8.25")

        cases = manifest["cases"]
        self.assertEqual(
            [case["rule_id"] for case in cases],
            manifest["rule_ids"],
        )
        self.assertEqual(
            manifest["rule_ids"],
            ["SOL008", "SOL009", "SOL010", "SOL011", "SOL012", "SOL013"],
        )

        positive_total = 0
        safe_total = 0
        for case in cases:
            with self.subTest(rule_id=case["rule_id"]):
                fixture = (CORPUS_ROOT / case["fixture"]).resolve()
                expectation_path = (CORPUS_ROOT / case["expectations"]).resolve()
                expectations = load_json(expectation_path)
                self.assertTrue((fixture / "foundry.toml").is_file())
                self.assertTrue((fixture / "src").is_dir())
                self.assertEqual(expectations["schema_version"], "1.0")
                self.assertEqual(expectations["rule_id"], case["rule_id"])
                self.assertEqual(
                    len(expectations["expected_findings"]),
                    case["positive_labels"],
                )
                self.assertEqual(len(safe_labels(expectations)), case["safe_labels"])
                positive_total += case["positive_labels"]
                safe_total += case["safe_labels"]

        self.assertEqual(positive_total, manifest["expected_positive_labels"])
        self.assertEqual(safe_total, manifest["expected_safe_labels"])


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for the M3 corpus")
class M3CorpusCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(MANIFEST_PATH)
        cls.results: dict[str, dict[str, object]] = {}
        scanner = Scanner()
        for case in cls.manifest["cases"]:
            rule_id = str(case["rule_id"])
            fixture = (CORPUS_ROOT / str(case["fixture"])).resolve()
            expectations = load_json(
                (CORPUS_ROOT / str(case["expectations"])).resolve()
            )
            files = discover_sources([fixture / "src"])
            compilation = ForgeCompiler().compile(
                files,
                project_root=fixture,
                offline=True,
            )
            index = ProjectIndex(compilation)
            findings = [
                finding
                for path in files
                for finding in scanner.scan_source(index.source_for_path(path).source)
                if finding.rule_id == rule_id
            ]
            cls.results[rule_id] = {
                "compilation": compilation,
                "index": index,
                "findings": findings,
                "expectations": expectations,
            }

    def test_every_label_matches_expected_evidence(self) -> None:
        for rule_id, result in self.results.items():
            with self.subTest(rule_id=rule_id):
                expectations = result["expectations"]
                expected = expectations["expected_findings"]
                fields = set().union(*(item.keys() for item in expected))
                actual = [
                    self._project_finding(finding, fields)
                    for finding in result["findings"]
                ]
                self.assertEqual(self._sorted(actual), self._sorted(expected))
                self.assertTrue(
                    all(
                        finding.metadata.get("evidence") == expectations["evidence"]
                        for finding in result["findings"]
                    )
                )
                versions = result["compilation"].compiler_versions
                self.assertTrue(
                    all(
                        version.startswith(self.manifest["solc_version"])
                        for version in versions
                    )
                )

    def test_safe_labels_exist_and_have_no_findings(self) -> None:
        for rule_id, result in self.results.items():
            with self.subTest(rule_id=rule_id):
                expected_safe = set(safe_labels(result["expectations"]))
                index = result["index"]
                available = {
                    str(contract.get("name"))
                    for contract in index.contracts_by_id.values()
                }
                for function in index.functions_by_id.values():
                    contract = index.enclosing_node(function, "ContractDefinition")
                    if contract is not None and function.get("name"):
                        available.add(
                            f"{contract.get('name')}.{function.get('name')}"
                        )
                self.assertTrue(expected_safe <= available)
                finding_labels = {
                    self._finding_label(finding) for finding in result["findings"]
                }
                self.assertTrue(expected_safe.isdisjoint(finding_labels))

    @staticmethod
    def _project_finding(finding, fields: set[str]) -> dict[str, object]:
        metadata = finding.metadata
        result: dict[str, object] = {}
        for field in fields:
            if field == "trace_kinds":
                result[field] = [event["kind"] for event in metadata["trace"]]
            elif field == "entry_function" and finding.rule_id == "SOL011":
                result[field] = M3CorpusCompilerTests._proxy_entry(metadata)
            else:
                result[field] = metadata.get(field)
        return result

    @staticmethod
    def _proxy_entry(metadata: dict[str, object]) -> object:
        if metadata.get("initializer"):
            return metadata["initializer"]
        if metadata.get("issue_kind") == "proxy-storage-collision":
            return metadata["trace"][1]["owner"]
        return None

    @staticmethod
    def _finding_label(finding) -> str:
        metadata = finding.metadata
        if finding.rule_id != "SOL011":
            return str(metadata.get("entry_function"))
        return str(
            M3CorpusCompilerTests._proxy_entry(metadata)
            or metadata.get("contract")
        )

    @staticmethod
    def _sorted(values: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(values, key=lambda item: json.dumps(item, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
