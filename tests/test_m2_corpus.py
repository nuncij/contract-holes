import json
from pathlib import Path
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.inspector import InspectionError, InspectionFilters, ProjectInspector
from contract_holes.project import Node, ProjectIndex
from contract_holes.scanner import Scanner, discover_sources


CORPUS_ROOT = Path("tests/fixtures/m2_corpus").resolve()
MANIFEST_PATH = CORPUS_ROOT / "expectations.json"
TRACE_FIELDS = (
    "kind",
    "function",
    "path",
    "call_kind",
    "callee",
    "state_variable",
)


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def relative_path(path: Path | str) -> str:
    return Path(path).resolve().relative_to(CORPUS_ROOT).as_posix()


class M2CorpusManifestTests(unittest.TestCase):
    def test_manifest_is_versioned_and_pairs_positive_with_safe_cases(self) -> None:
        manifest = load_manifest()

        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["corpus_version"], "m2-1")
        self.assertEqual(manifest["solc_version"], "0.8.25")
        vulnerable_entries = {
            item["entry_function"] for item in manifest["expected_findings"]
        }
        safe_entries = set(manifest["expected_clean_entries"])
        self.assertEqual(
            {entry.replace("Vulnerable", "Safe") for entry in vulnerable_entries},
            safe_entries,
        )
        for item in manifest["expected_findings"]:
            self.assertTrue((CORPUS_ROOT / item["path"]).is_file())
            self.assertTrue(
                (CORPUS_ROOT / item["path"].replace("Vulnerable", "Safe")).is_file()
            )
            for event in item["trace"]:
                self.assertTrue((CORPUS_ROOT / event["path"]).is_file())


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for the M2 corpus")
class M2CorpusCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest()
        cls.files = discover_sources([CORPUS_ROOT / "src"])
        cls.compilation = ForgeCompiler().compile(
            cls.files,
            project_root=CORPUS_ROOT,
            offline=True,
        )
        cls.index = ProjectIndex(cls.compilation)
        scanner = Scanner()
        cls.findings = [
            finding
            for path in cls.files
            for finding in scanner.scan_source(cls.index.source_for_path(path).source)
        ]

    def test_expected_rule_ids_and_evidence_paths(self) -> None:
        actual = sorted(
            (self._finding_projection(finding) for finding in self.findings),
            key=lambda item: (item["path"], item["rule_id"], item["entry_function"]),
        )
        expected = sorted(
            self.manifest["expected_findings"],
            key=lambda item: (item["path"], item["rule_id"], item["entry_function"]),
        )

        self.assertEqual(actual, expected)
        self.assertEqual({item["rule_id"] for item in actual}, {"SOL005"})
        self.assertTrue(
            all(
                version.startswith(self.manifest["solc_version"])
                for version in self.compilation.compiler_versions
            )
        )
        actual_entries = {item["entry_function"] for item in actual}
        self.assertTrue(
            actual_entries.isdisjoint(self.manifest["expected_clean_entries"])
        )
        for entry in self.manifest["expected_clean_entries"]:
            contract_name, function_name = entry.split(".", 1)
            self._function(contract_name, function_name)

    def test_project_contains_every_m2_primitive(self) -> None:
        imported = self._function("ImportedVulnerable", "withdraw")
        library_edges = {
            edge.kind: edge for edge in self.index.call_graph.edges_from(imported)
        }
        self.assertEqual(
            self.index.reentrancy.function_name(library_edges["library"].callee),
            "PaymentLibrary.pay",
        )
        imported_source = self.index.source_for_path(
            CORPUS_ROOT / "src/imports/ImportedVulnerable.sol"
        )
        self.assertEqual(
            sum(
                node.get("nodeType") == "ImportDirective"
                for node in imported_source.ast.get("nodes", [])
                if isinstance(node, dict)
            ),
            2,
        )

        override = self._function("OverrideVulnerable", "withdraw")
        overridden = self.index.inheritance.overridden_function_nodes(override)
        self.assertEqual(
            [self.index.reentrancy.function_name(node) for node in overridden],
            ["OverrideBase.withdraw"],
        )
        self.assertIn(
            "super", {edge.kind for edge in self.index.call_graph.edges_from(override)}
        )

        diamond = self._contract("DiamondVulnerable")
        semantics = self.index.inheritance.for_contract(diamond)
        self.assertIsNotNone(semantics)
        linearized = [
            str(self.index.node_for_key(key).get("name"))
            for key in semantics.linearized_contracts
        ]
        self.assertEqual(len(linearized), len(set(linearized)))
        self.assertEqual(
            set(linearized),
            {
                "DiamondVulnerable",
                "DiamondAccounting",
                "DiamondPayments",
                "DiamondRoot",
            },
        )
        visible_state = self.index.inheritance.state_variable_nodes(
            diamond, visible_only=True
        )
        self.assertEqual(
            [node.get("name") for node in visible_state].count("balances"), 1
        )

        recursive = self._function("RecursivePayments", "_recursivePay")
        recursive_key = self.index.key_for_node(recursive)
        self.assertTrue(
            any(
                edge.caller == recursive_key and edge.callee == recursive_key
                for edge in self.index.call_graph.edges_from(recursive)
            )
        )

        guarded = self._function("ModifierSafe", "withdraw")
        guarded_key = self.index.key_for_node(guarded)
        self.assertIn(
            "modifier", {edge.kind for edge in self.index.call_graph.edges_from(guarded)}
        )
        self.assertIn(guarded_key, self.index.reentrancy.guarded_functions)

    def test_inspection_filters_are_deterministic_and_source_free(self) -> None:
        filters = InspectionFilters.create(
            files=["src/overrides/OverrideVulnerable.sol"],
            contracts=["OverrideVulnerable"],
            functions=["withdraw"],
        )
        inspector = ProjectInspector(
            self.index,
            root=CORPUS_ROOT,
            compiler_versions=self.compilation.compiler_versions,
            filters=filters,
        )

        first = inspector.to_dict()
        second = inspector.to_dict()
        self.assertEqual(first, second)
        self.assertEqual(
            first["summary"],
            {
                "sources": 1,
                "contracts": 1,
                "functions": 1,
                "modifiers": 0,
                "call_edges": 2,
                "facts": 10,
                "guarded_functions": 0,
                "reentrancy_issues": 1,
                "target_taint_issues": 0,
                "authorization_issues": 0,
                "signature_issues": 0,
                "proxy_issues": 0,
            },
        )
        self.assertEqual(
            {edge["kind"] for edge in first["call_graph"]["edges"]},
            {"internal", "super"},
        )
        self.assertEqual(
            first["reentrancy"]["issues"][0]["entry_function"],
            "OverrideVulnerable.withdraw",
        )
        rendered = json.dumps(first, sort_keys=True)
        self.assertNotIn("SPDX-License-Identifier", rendered)
        self.assertNotIn("recipient.call{value: amount}", rendered)

        missing_filters = (
            InspectionFilters.create(files=["Missing.sol"]),
            InspectionFilters.create(contracts=["MissingContract"]),
            InspectionFilters.create(functions=["missingFunction"]),
        )
        for missing in missing_filters:
            with self.subTest(filters=missing):
                with self.assertRaisesRegex(
                    InspectionError, "matched no compiler nodes"
                ):
                    ProjectInspector(
                        self.index,
                        root=CORPUS_ROOT,
                        filters=missing,
                    )

    def _finding_projection(self, finding) -> dict[str, object]:
        metadata = finding.metadata
        return {
            "rule_id": finding.rule_id,
            "path": relative_path(finding.path),
            "evidence": metadata.get("evidence"),
            "entry_function": metadata.get("entry_function"),
            "state_variable": metadata.get("state_variable"),
            "trace": [
                {
                    field: (
                        relative_path(event[field])
                        if field == "path"
                        else event[field]
                    )
                    for field in TRACE_FIELDS
                    if event.get(field) is not None
                }
                for event in metadata.get("trace", [])
            ],
        }

    def _contract(self, name: str) -> Node:
        matches = [
            contract
            for contract in self.index.contracts_by_id.values()
            if contract.get("name") == name
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def _function(self, contract_name: str, function_name: str) -> Node:
        matches: list[Node] = []
        for function in self.index.functions_by_id.values():
            contract = self.index.enclosing_node(function, "ContractDefinition")
            if (
                contract is not None
                and contract.get("name") == contract_name
                and function.get("name") == function_name
            ):
                matches.append(function)
        self.assertEqual(len(matches), 1)
        return matches[0]


if __name__ == "__main__":
    unittest.main()
