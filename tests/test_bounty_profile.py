import contextlib
import io
from importlib.resources import files
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.bounty_profile import (
    BountyProfileError,
    initialize_bounty_workspace,
    load_bounty_profile,
)
from contract_holes.cli import bounty_parser, main


REVISION = "a" * 40


def initialize(root: Path, **changes: object):
    source = root / "target"
    source.mkdir(exist_ok=True)
    arguments = {
        "workspace": root / "private-review",
        "program_name": "Example Protocol",
        "platform": "Example Bounty",
        "rules_url": "https://example.test/security/rules",
        "reviewed_on": "2026-08-09",
        "authorization_acknowledged": True,
        "authorization_note": "Public program permits local source analysis",
        "source_root": source,
        "source_revision": REVISION,
        "source_content_sha256": None,
        "scope_paths": ["src", "contracts/Vault.sol"],
        "impacts": ["Unauthorized withdrawal of user funds"],
        "restrictions": ["No live-network transactions"],
        "compiler_enabled": True,
    }
    arguments.update(changes)
    return initialize_bounty_workspace(**arguments)


class BountyProfileTests(unittest.TestCase):
    def test_initializes_private_normalized_profile_and_reloads_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = initialize(root)
            loaded = load_bounty_profile(profile.workspace)

            self.assertEqual(loaded, profile)
            self.assertEqual(loaded.source_root, (root / "target").resolve())
            self.assertEqual(loaded.source_revision, REVISION)
            self.assertEqual(loaded.scope_paths, ("src", "contracts/Vault.sol"))
            self.assertEqual(len(loaded.digest), 64)
            normalized = loaded.normalized_payload()
            self.assertEqual(normalized["schema_version"], "1.0")
            self.assertNotIn("dependency_paths", normalized["compiler"])
            self.assertEqual(normalized["profile_sha256"], loaded.digest)
            self.assertNotIn(str(root.resolve()), json.dumps(normalized))
            self.assertEqual(
                (profile.workspace / ".gitignore").read_text(encoding="utf-8"),
                "# Bounty workspaces are private by default.\n*\n!.gitignore\n",
            )
            if os.name == "posix":
                self.assertEqual(
                    stat.S_IMODE(profile.workspace.stat().st_mode),
                    0o700,
                )
                self.assertEqual(stat.S_IMODE(profile.path.stat().st_mode), 0o600)

    def test_refuses_overwrite_workspace_inside_target_and_missing_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = initialize(root)
            with self.assertRaisesRegex(BountyProfileError, "already exists"):
                initialize(root)

            nested_source = root / "nested-target"
            nested_source.mkdir()
            with self.assertRaisesRegex(BountyProfileError, "outside"):
                initialize(
                    root,
                    workspace=nested_source / "review",
                    source_root=nested_source,
                )

            with self.assertRaisesRegex(BountyProfileError, "acknowledged"):
                initialize(
                    root,
                    workspace=root / "unauthorized",
                    authorization_acknowledged=False,
                )
            self.assertFalse((root / "unauthorized").exists())
            self.assertTrue(profile.path.is_file())

    def test_rejects_ambiguous_identity_scope_escape_and_unknown_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(BountyProfileError, "source.revision"):
                initialize(root, source_revision="main")
            with self.assertRaisesRegex(BountyProfileError, "relative and contained"):
                initialize(root, scope_paths=["../outside.sol"])

            profile = initialize(root)
            content = profile.path.read_text(encoding="utf-8")
            profile.path.write_text(
                content.replace("[compiler]", "unexpected = true\n\n[compiler]"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BountyProfileError, "unknown .* setting"):
                load_bounty_profile(profile.path)

    def test_rejects_invalid_compiler_dependency_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(BountyProfileError, "relative and contained"):
                initialize(
                    root,
                    workspace=root / "traversal",
                    compiler_dependency_paths=["../outside.sol"],
                )
            with self.assertRaisesRegex(BountyProfileError, "duplicate scope.paths"):
                initialize(
                    root,
                    workspace=root / "overlap",
                    compiler_dependency_paths=["src"],
                )
            with self.assertRaisesRegex(BountyProfileError, "require compiler.enabled"):
                initialize(
                    root,
                    workspace=root / "source-only",
                    compiler_enabled=False,
                    compiler_dependency_paths=["lib/Dependency.sol"],
                )

    def test_python_310_subset_parser_loads_generated_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = initialize(Path(temporary))
            with patch("contract_holes.bounty_profile.tomllib", None):
                loaded = load_bounty_profile(profile.path)
            self.assertEqual(loaded.digest, profile.digest)

    @unittest.skipUnless(os.name == "posix", "POSIX permission policy")
    def test_rejects_workspace_or_profile_readable_by_other_users(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = initialize(root)
            profile.path.chmod(0o644)
            with self.assertRaisesRegex(BountyProfileError, "profile permissions"):
                load_bounty_profile(profile.path)
            profile.path.chmod(0o600)
            profile.workspace.chmod(0o755)
            with self.assertRaisesRegex(BountyProfileError, "workspace permissions"):
                load_bounty_profile(profile.path)

    def test_normalized_schema_is_packaged(self) -> None:
        schema = json.loads(
            files("contract_holes")
            .joinpath("schemas/bounty-profile-1.0.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertFalse(schema["additionalProperties"])

        dependency_schema = json.loads(
            files("contract_holes")
            .joinpath("schemas/bounty-profile-1.1.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            dependency_schema["properties"]["schema_version"]["const"],
            "1.1",
        )
        self.assertIn(
            "dependency_paths",
            dependency_schema["properties"]["compiler"]["properties"],
        )


class BountyProfileCliTests(unittest.TestCase):
    def test_init_records_compiler_only_dependency_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "target"
            source.mkdir()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "init",
                        str(root / "review"),
                        "--program",
                        "Example Protocol",
                        "--platform",
                        "Example Bounty",
                        "--rules-url",
                        "https://example.test/rules",
                        "--reviewed-on",
                        "2026-08-10",
                        "--authorized",
                        "--authorization-note",
                        "Local compiler analysis is in scope",
                        "--source",
                        str(source),
                        "--revision",
                        REVISION,
                        "--scope",
                        "contracts/Vault.sol",
                        "--compiler-dependency",
                        "lib/Dependency.sol",
                        "--impact",
                        "Loss of funds",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["profile"]["schema_version"], "1.1")
            self.assertEqual(
                payload["profile"]["compiler"]["dependency_paths"],
                ["lib/Dependency.sol"],
            )
            loaded = load_bounty_profile(root / "review")
            self.assertEqual(
                loaded.compiler_dependency_paths,
                ("lib/Dependency.sol",),
            )

    def test_init_and_validate_emit_versioned_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "target"
            source.mkdir()
            workspace = root / "review"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    [
                        "bounty",
                        "init",
                        str(workspace),
                        "--program",
                        "Example Protocol",
                        "--platform",
                        "Example Bounty",
                        "--rules-url",
                        "https://example.test/rules",
                        "--reviewed-on",
                        "2026-08-09",
                        "--authorized",
                        "--authorization-note",
                        "Local review is in scope",
                        "--source",
                        str(source),
                        "--revision",
                        REVISION,
                        "--scope",
                        "contracts",
                        "--impact",
                        "Loss of funds",
                        "--restriction",
                        "No live testing",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["command"], "bounty.init")
            self.assertEqual(payload["status"], "created")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["bounty", "validate", str(workspace)])
            validation = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(validation["command"], "bounty.validate")
            self.assertEqual(
                validation["profile"]["profile_sha256"],
                payload["profile"]["profile_sha256"],
            )

    def test_init_requires_authorization_and_has_no_submission_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "target"
            source.mkdir()
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                status = main(
                    [
                        "bounty",
                        "init",
                        str(root / "review"),
                        "--program",
                        "Example",
                        "--platform",
                        "Example",
                        "--rules-url",
                        "https://example.test/rules",
                        "--reviewed-on",
                        "2026-08-09",
                        "--authorization-note",
                        "not enough without the flag",
                        "--source",
                        str(source),
                        "--revision",
                        REVISION,
                        "--scope",
                        ".",
                        "--impact",
                        "Loss of funds",
                    ]
                )
            self.assertEqual(status, 2)
            self.assertIn("authorization_acknowledged", errors.getvalue())
            self.assertNotIn("submit", bounty_parser()._subparsers._group_actions[0].choices)


if __name__ == "__main__":
    unittest.main()
