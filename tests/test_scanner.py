import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.models import Finding, RuleInfo, Severity
from contract_holes.project import ProjectIndex
from contract_holes.rules import Rule
from contract_holes.reporters import json_report, sarif_report
from contract_holes.scanner import ScanError, Scanner, discover_sources


class ScannerTests(unittest.TestCase):
    def test_severity_filter(self) -> None:
        findings, count = Scanner().scan_paths(
            [Path("tests/fixtures/VulnerableVault.sol")],
            minimum_severity=Severity.HIGH,
        )
        self.assertEqual(count, 1)
        self.assertTrue(findings)
        self.assertTrue(all(finding.severity >= Severity.HIGH for finding in findings))
        self.assertNotIn("SOL002", {finding.rule_id for finding in findings})

    def test_json_and_sarif_are_valid(self) -> None:
        scanner = Scanner()
        findings, count = scanner.scan_paths([Path("tests/fixtures/VulnerableVault.sol")])

        json_payload = json.loads(json_report(findings, count))
        sarif_payload = json.loads(sarif_report(findings, [rule.info for rule in scanner.rules]))

        self.assertEqual(json_payload["finding_count"], 7)
        self.assertEqual(sarif_payload["version"], "2.1.0")
        self.assertEqual(len(sarif_payload["runs"][0]["results"]), 7)

    def test_dependency_directories_are_excluded_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "lib").mkdir()
            (root / "src" / "Main.sol").write_text("contract Main {}", encoding="utf-8")
            (root / "lib" / "Dependency.sol").write_text("contract Dependency {}", encoding="utf-8")

            default = discover_sources([root])
            included = discover_sources([root], include_dependencies=True)

            self.assertEqual([item.name for item in default], ["Main.sol"])
            self.assertEqual({item.name for item in included}, {"Main.sol", "Dependency.sol"})

    def test_custom_globs_exclude_relative_paths_and_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated").mkdir()
            (root / "src").mkdir()
            (root / "generated" / "Generated.sol").write_text(
                "contract Generated {}", encoding="utf-8"
            )
            (root / "src" / "Ignored.skip.sol").write_text(
                "contract Ignored {}", encoding="utf-8"
            )
            kept = root / "src" / "Kept.sol"
            kept.write_text("contract Kept {}", encoding="utf-8")

            files = discover_sources(
                [root],
                exclude_patterns=("generated/**", "*.skip.sol"),
            )

            self.assertEqual(files, [kept])

    def test_invalid_path_is_an_actionable_error(self) -> None:
        with self.assertRaisesRegex(ScanError, "path does not exist"):
            discover_sources(["definitely-missing.sol"])

    def test_compiler_mode_shares_project_index_with_rules(self) -> None:
        class CaptureRule(Rule):
            info = RuleInfo(
                "TEST001",
                Severity.INFO,
                "capture",
                "capture",
                "none",
            )

            def __init__(self) -> None:
                self.index = None

            def scan(self, source):
                self.index = source.project_index
                return ()

        class FakeCompiler:
            def __init__(self, result) -> None:
                self.result = result

            def compile(self, files, *, offline=False):
                return self.result

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Indexed.sol"
            text = "contract Indexed {}"
            path.write_text(text, encoding="utf-8")
            ast = {
                "nodeType": "SourceUnit",
                "id": 1,
                "src": f"0:{len(text)}:0",
                "nodes": [],
            }
            compilation = CompilationResult(
                sources=(CompiledSource(path.resolve(), 0, "build-a", ast, text),),
                compiler_versions=("0.8.25",),
                diagnostics=(),
            )
            capture = CaptureRule()
            scanner = Scanner(rules=(capture,), compiler=FakeCompiler(compilation))

            findings, count = scanner.scan_paths([path], compile_sources=True)

            self.assertEqual((findings, count), ([], 1))
            self.assertIsInstance(capture.index, ProjectIndex)
            self.assertIsNotNone(capture.index.source_for_path(path))

    def test_compiler_mode_does_not_silently_fall_back_without_ast(self) -> None:
        class EmptyCompiler:
            def compile(self, files, *, offline=False):
                return CompilationResult((), (), ())

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Missing.sol"
            path.write_text("contract Missing {}", encoding="utf-8")
            scanner = Scanner(compiler=EmptyCompiler())

            with self.assertRaisesRegex(ScanError, "produced no AST"):
                scanner.scan_paths([path], compile_sources=True)

    def test_scan_paths_coalesces_findings_with_the_same_fingerprint(self) -> None:
        class DuplicateRule(Rule):
            info = RuleInfo(
                "SOL999",
                Severity.HIGH,
                "duplicate fixture",
                "duplicate fixture",
                "none",
            )

            def scan(self, source):
                finding = Finding(
                    rule_id=self.info.rule_id,
                    severity=self.info.severity,
                    title=self.info.title,
                    message="first trace",
                    path=source.path,
                    line=1,
                    column=1,
                    excerpt="contract SafeVault",
                    recommendation=self.info.recommendation,
                    metadata={"trace": ["first"]},
                )
                return (
                    finding,
                    replace(
                        finding,
                        message="alternative trace",
                        metadata={"trace": ["alternative"]},
                    ),
                )

        findings, count = Scanner(rules=(DuplicateRule(),)).scan_paths(
            [Path("tests/fixtures/SafeVault.sol")]
        )

        self.assertEqual(count, 1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].message, "first trace")
        json_report(findings, count)


if __name__ == "__main__":
    unittest.main()
