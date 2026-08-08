import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.compiler import CompilerError, ForgeCompiler


class CompilerTests(unittest.TestCase):
    def test_loads_ast_from_forge_build_info(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Example.sol"
            source.write_text("contract Example {}", encoding="utf-8")

            def fake_run(command, **kwargs):
                build_info = Path(command[command.index("--build-info-path") + 1])
                build_info.mkdir(parents=True)
                payload = {
                    "solcLongVersion": "0.8.25+commit.fake",
                    "output": {
                        "sources": {
                            "Example.sol": {
                                "ast": {"nodeType": "SourceUnit", "nodes": []}
                            }
                        },
                        "errors": [
                            {
                                "severity": "warning",
                                "errorCode": "9302",
                                "message": "Return value not used.",
                            }
                        ],
                    },
                }
                (build_info / "build.json").write_text(json.dumps(payload), encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            with (
                patch("contract_holes.compiler.shutil.which", return_value="/usr/bin/forge"),
                patch("contract_holes.compiler.subprocess.run", side_effect=fake_run) as run,
            ):
                result = ForgeCompiler().compile([source], project_root=root, offline=True)

            self.assertIn(source.resolve(), result.asts)
            self.assertEqual(result.compiler_versions, ("0.8.25+commit.fake",))
            self.assertEqual(result.diagnostics[0].error_code, "9302")
            command = run.call_args.args[0]
            self.assertIn("--offline", command)
            self.assertEqual(run.call_args.kwargs["cwd"], root)

    def test_missing_forge_is_actionable(self) -> None:
        with patch("contract_holes.compiler.shutil.which", return_value=None):
            with self.assertRaisesRegex(CompilerError, "forge.*not found"):
                ForgeCompiler().compile([Path("Example.sol")])

    def test_compiler_failure_is_reported(self) -> None:
        process = subprocess.CompletedProcess(["forge"], 1, "", "ParserError: broken source")
        with (
            patch("contract_holes.compiler.shutil.which", return_value="/usr/bin/forge"),
            patch("contract_holes.compiler.subprocess.run", return_value=process),
        ):
            with self.assertRaisesRegex(CompilerError, "ParserError: broken source"):
                ForgeCompiler().compile([Path("Example.sol")], project_root=Path.cwd())


if __name__ == "__main__":
    unittest.main()
