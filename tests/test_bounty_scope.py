import contextlib
import io
from importlib.resources import files
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from contract_holes.bounty_io import (
    BountyWorkspaceError,
    redact_sensitive_text,
    write_private_json_new_or_identical,
    payload_sha256,
)
from contract_holes.bounty_profile import initialize_bounty_workspace
from contract_holes.bounty_scope import (
    BountyScopeError,
    ScopedForgeCompiler,
    identify_source,
    scan_bounty_workspace,
    validate_profile_source,
)
from contract_holes.cli import main
from contract_holes.compiler import CompilationResult, CompiledSource, CompilerError
from contract_holes.process_environment import sanitized_subprocess_environment


VULNERABLE_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract ScopedVault {
    function ownerOnly() external view returns (bool) {
        return tx.origin == msg.sender;
    }
}
"""


def directory_profile(
    root: Path,
    *,
    scope: tuple[str, ...] = ("src",),
    compiler_enabled: bool = False,
):
    target = root / "target"
    identity = identify_source(target, scope)
    return initialize_bounty_workspace(
        root / "review",
        program_name="Example Protocol",
        platform="Example Bounty",
        rules_url="https://example.test/rules",
        reviewed_on="2026-08-09",
        authorization_acknowledged=True,
        authorization_note="Repository-owned local test target",
        source_root=target,
        source_revision=None,
        source_content_sha256=identity.source_set_sha256,
        scope_paths=scope,
        impacts=["Unauthorized privileged operation"],
        restrictions=["No live-network testing"],
        compiler_enabled=compiler_enabled,
    )


def create_source(root: Path, relative: str = "src/Vault.sol") -> Path:
    path = root / "target" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(VULNERABLE_SOURCE, encoding="utf-8")
    return path


class BountyScopeTests(unittest.TestCase):
    def test_directory_scan_writes_reproducible_relative_private_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            profile = directory_profile(root)

            first = scan_bounty_workspace(profile.workspace)
            second = scan_bounty_workspace(profile.workspace)

            self.assertEqual(first.scan_record, second.scan_record)
            self.assertEqual(first.source_manifest, second.source_manifest)
            self.assertEqual(first.scan_record["command"], "bounty.scan")
            self.assertEqual(first.scan_record["status"], "completed")
            self.assertEqual(first.scan_record["report"]["finding_count"], 1)
            self.assertEqual(
                first.scan_record["report"]["findings"][0]["path"],
                "src/Vault.sol",
            )
            rendered = json.dumps(first.scan_record)
            self.assertNotIn(str(root.resolve()), rendered)
            self.assertTrue((profile.workspace / "source-manifest.json").is_file())
            self.assertTrue((profile.workspace / "scan.json").is_file())
            manifest_material = dict(first.source_manifest)
            manifest_digest = manifest_material.pop("manifest_sha256")
            self.assertEqual(manifest_digest, payload_sha256(manifest_material))
            scan_material = dict(first.scan_record)
            scan_digest = scan_material.pop("scan_sha256")
            self.assertEqual(scan_digest, payload_sha256(scan_material))

    def test_directory_identity_fails_after_source_or_remapping_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = create_source(root)
            (root / "target" / "remappings.txt").write_text(
                "example/=src/\n", encoding="utf-8"
            )
            profile = directory_profile(root)
            validate_profile_source(profile)

            source.write_text(VULNERABLE_SOURCE + "\n", encoding="utf-8")
            with self.assertRaisesRegex(BountyScopeError, "content_sha256"):
                validate_profile_source(profile)

            source.write_text(VULNERABLE_SOURCE, encoding="utf-8")
            (root / "target" / "remappings.txt").write_text(
                "example/=contracts/\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(BountyScopeError, "content_sha256"):
                validate_profile_source(profile)

    def test_scope_excludes_unapproved_source_and_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root, "src/Approved.sol")
            create_source(root, "outside/Unapproved.sol")
            profile = directory_profile(root, scope=("src/Approved.sol",))
            result = scan_bounty_workspace(profile.workspace)
            self.assertEqual(result.scan_record["report"]["files_scanned"], 1)
            self.assertEqual(
                {entry["path"] for entry in result.source_manifest["files"]},
                {"src/Approved.sol"},
            )

            if hasattr(os, "symlink"):
                link = root / "target" / "linked.sol"
                link.symlink_to(root / "target" / "outside" / "Unapproved.sol")
                with self.assertRaisesRegex(BountyScopeError, "symlink"):
                    identify_source(root / "target", ["linked.sol"])

    def test_rejects_remapping_that_escapes_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            (root / "target" / "remappings.txt").write_text(
                "evil/=../outside/\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(BountyScopeError, "remapping escapes"):
                identify_source(root / "target", ["src"])

    def test_git_profile_requires_exact_clean_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            source = create_source(root)
            subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True, capture_output=True)
            subprocess.run(["git", "add", "src/Vault.sol"], cwd=target, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.test",
                    "commit",
                    "--no-gpg-sign",
                    "-m",
                    "fixture",
                ],
                cwd=target,
                check=True,
                capture_output=True,
            )
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            profile = initialize_bounty_workspace(
                root / "review",
                program_name="Git Program",
                platform="Example",
                rules_url="https://example.test/rules",
                reviewed_on="2026-08-09",
                authorization_acknowledged=True,
                authorization_note="Local fixture",
                source_root=target,
                source_revision=revision,
                source_content_sha256=None,
                scope_paths=["src"],
                impacts=["Unauthorized operation"],
                compiler_enabled=False,
            )
            identity = validate_profile_source(profile)
            self.assertEqual(identity.files[0].path, source.resolve())

            source.write_text(VULNERABLE_SOURCE + "// changed\n", encoding="utf-8")
            with self.assertRaisesRegex(BountyScopeError, "not clean"):
                validate_profile_source(profile)

    def test_scoped_compiler_stages_only_approved_files_and_maps_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = create_source(root)
            (root / "target" / "foundry.toml").write_text(
                '[profile.default]\nffi = true\nsolc = "./malicious"\n',
                encoding="utf-8",
            )
            profile = directory_profile(root, compiler_enabled=True)
            identity = validate_profile_source(profile)

            class Delegate:
                def compile(self, files, *, project_root=None, offline=False):
                    self.root = project_root
                    self.offline = offline
                    self.foundry = (project_root / "foundry.toml").read_text(
                        encoding="utf-8"
                    )
                    staged = files[0]
                    return CompilationResult(
                        sources=(
                            CompiledSource(
                                path=staged,
                                source_id=0,
                                compilation_id="safe-build",
                                ast={"nodeType": "SourceUnit", "src": "0:1:0"},
                                content=staged.read_text(encoding="utf-8"),
                            ),
                        ),
                        compiler_versions=("0.8.25",),
                        diagnostics=(),
                    )

            delegate = Delegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            result = compiler.compile([original], offline=True)
            self.assertEqual(result.sources[0].path, original.resolve())
            self.assertTrue(delegate.offline)
            self.assertIn("ffi = false", delegate.foundry)
            self.assertNotIn("malicious", delegate.foundry)
            self.assertEqual(compiler.compiler_versions, ("0.8.25",))

            with self.assertRaisesRegex(CompilerError, "out-of-scope"):
                compiler.compile([root / "target" / "outside.sol"], offline=True)

    def test_scoped_compiler_rejects_traversal_and_absolute_imports(self) -> None:
        for imported in ("../outside.sol", "/tmp/outside.sol", "https://evil.test/X.sol"):
            with self.subTest(imported=imported), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = create_source(root)
                source.write_text(
                    f'pragma solidity ^0.8.20; import "{imported}"; contract X {{}}\n',
                    encoding="utf-8",
                )
                profile = directory_profile(root, compiler_enabled=True)
                identity = validate_profile_source(profile)

                class UnusedDelegate:
                    def compile(self, files, **kwargs):
                        raise AssertionError("unsafe imports must fail before Foundry")

                compiler = ScopedForgeCompiler(
                    profile, identity, delegate=UnusedDelegate()
                )
                with self.assertRaisesRegex(CompilerError, "unsafe import path"):
                    compiler.compile([source], offline=True)

    def test_private_records_refuse_tampering_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = root / "record.json"
            self.assertTrue(write_private_json_new_or_identical(record, {"a": 1}))
            self.assertFalse(write_private_json_new_or_identical(record, {"a": 1}))
            with self.assertRaisesRegex(BountyWorkspaceError, "overwrite changed"):
                write_private_json_new_or_identical(record, {"a": 2})

            if hasattr(os, "symlink"):
                target = root / "target.json"
                target.write_text("{}\n", encoding="utf-8")
                linked = root / "linked.json"
                linked.symlink_to(target)
                with self.assertRaisesRegex(BountyWorkspaceError, "symlink"):
                    write_private_json_new_or_identical(linked, {})

    def test_bounty_environment_and_shareable_text_remove_sensitive_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FOUNDRY_PROFILE": "host-profile",
                "ETH_RPC_URL": "https://secret-rpc.test/key",
                "AWS_REGION": "eu-west-1",
                "PATH": os.environ.get("PATH", ""),
            },
            clear=True,
        ):
            environment = sanitized_subprocess_environment(
                remove_prefixes=("FOUNDRY_", "ETH_", "AWS_")
            )
        self.assertNotIn("FOUNDRY_PROFILE", environment)
        self.assertNotIn("ETH_RPC_URL", environment)
        self.assertNotIn("AWS_REGION", environment)

        private = Path("/private/workspace").resolve()
        redacted = redact_sensitive_text(
            f"password=hunter2 https://alice:secret@example.test {private}/report.json",
            private_paths=(private,),
        )
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("alice:secret", redacted)
        self.assertNotIn(str(private), redacted)
        self.assertIn("<redacted>", redacted)

    def test_source_and_scan_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        source_schema = json.loads(
            schema_directory.joinpath(
                "bounty-source-manifest-1.0.schema.json"
            ).read_text(encoding="utf-8")
        )
        scan_schema = json.loads(
            schema_directory.joinpath("bounty-scan-1.0.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(source_schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(scan_schema["properties"]["command"]["const"], "bounty.scan")


class BountyScopeCliTests(unittest.TestCase):
    def test_identify_then_source_only_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(
                    ["bounty", "identify", str(root / "target"), "--scope", "src"]
                )
            identity = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(identity["command"], "bounty.identify")
            digest = identity["source"]["source_set_sha256"]

            workspace = root / "review"
            with contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "bounty",
                        "init",
                        str(workspace),
                        "--program",
                        "Example",
                        "--platform",
                        "Example",
                        "--rules-url",
                        "https://example.test/rules",
                        "--reviewed-on",
                        "2026-08-09",
                        "--authorized",
                        "--authorization-note",
                        "Local fixture",
                        "--source",
                        str(root / "target"),
                        "--content-sha256",
                        digest,
                        "--scope",
                        "src",
                        "--impact",
                        "Unauthorized operation",
                        "--source-only",
                    ]
                )
            self.assertEqual(status, 0)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["bounty", "scan", str(workspace)])
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["report"]["finding_count"], 1)


if __name__ == "__main__":
    unittest.main()
