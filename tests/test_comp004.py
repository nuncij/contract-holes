import contextlib
import io
from importlib.resources import files
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes.bounty_profile import (
    BountyProfileError,
    initialize_bounty_workspace,
    load_bounty_profile,
)
from contract_holes.bounty_scope import (
    ScopedForgeCompiler,
    identify_source,
    scan_bounty_workspace,
    validate_profile_source,
)
from contract_holes.cli import main
from contract_holes.compatibility import parse_version
from contract_holes.compiler import CompilationResult, CompiledSource, CompilerError


REVISION = "a" * 40


def initialize(root: Path | str, **changes):
    source = root / "target"
    source.mkdir(exist_ok=True)
    (source / "Vault.sol").write_text(
        "// SPDX-License-Identifier: MIT\n"
        "pragma solidity ^0.8.20;\n"
        "contract ScopedVault {}\n",
        encoding="utf-8",
    )
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


def directory_profile(root: Path | str, *, compiler_version: str | None):
    target = root / "target"
    identity = identify_source(target, ("src",))
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
        scope_paths=("src",),
        impacts=["Unauthorized privileged operation"],
        restrictions=["No live-network testing"],
        compiler_enabled=True,
        compiler_version=compiler_version,
    )


def create_source(root: Path, relative: str = "src/Vault.sol") -> Path:
    path = root / "target" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// SPDX-License-Identifier: MIT\n"
        "pragma solidity ^0.8.20;\n"
        "contract ScopedVault {\n"
        "    function ownerOnly() external view returns (bool) {\n"
        "        return tx.origin == msg.sender;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    return path


def staged_result(staged, *, compiler_versions=("0.8.30+commit.a2be1a0c",)):
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
        compiler_versions=tuple(compiler_versions),
        diagnostics=(),
    )


class Comp004CliTests(unittest.TestCase):
    def test_init_with_compiler_version_emits_profile_schema_1_2_and_reloads(self) -> None:
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
                        "--compiler-version",
                        "0.8.30",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(payload["profile"]["schema_version"], "1.2")
            self.assertEqual(
                payload["profile"]["compiler"]["version"], "0.8.30"
            )
            self.assertEqual(
                payload["profile"]["compiler"]["enabled"], True
            )
            self.assertEqual(len(payload["profile"]["profile_sha256"]), 64)

            loaded = load_bounty_profile(workspace)
            self.assertEqual(loaded.compiler_version, "0.8.30")
            self.assertEqual(loaded.digest, payload["profile"]["profile_sha256"])
            self.assertEqual(loaded.normalized_payload(), payload["profile"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["bounty", "validate", str(workspace)])
            validation = json.loads(output.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(
                validation["profile"]["profile_sha256"],
                payload["profile"]["profile_sha256"],
            )
            self.assertEqual(
                validation["profile"]["compiler"]["version"], "0.8.30"
            )

    def test_pinned_profile_reloads_from_toml_and_keeps_byte_exact_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = initialize(Path(temporary), compiler_version="0.8.30")
            text = profile.path.read_text(encoding="utf-8")
            self.assertIn('version = "0.8.30"', text)
            loaded = load_bounty_profile(profile.path)
            self.assertEqual(loaded.compiler_version, "0.8.30")
            self.assertEqual(loaded.digest, profile.digest)


class Comp004ProfileTests(unittest.TestCase):
    def test_compiler_version_is_rejected_with_source_only_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "target"
            source.mkdir()
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                with self.assertRaises(SystemExit):
                    main(
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
                            "--authorized",
                            "--authorization-note",
                            "not a compiler profile",
                            "--source",
                            str(source),
                            "--revision",
                            REVISION,
                            "--scope",
                            "contracts",
                            "--impact",
                            "Loss of funds",
                            "--source-only",
                            "--compiler-version",
                            "0.8.30",
                        ]
                    )
            self.assertIn("--source-only", errors.getvalue())
            self.assertFalse((root / "review").exists())

    def test_compiler_version_requires_compiler_enabled_in_direct_api(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                BountyProfileError, "compiler.enabled"
            ):
                initialize(
                    Path(temporary),
                    workspace=Path(temporary) / "source-only",
                    compiler_enabled=False,
                    compiler_version="0.8.30",
                )

    def test_compiler_version_rejects_inexact_or_unsupported_releases(self) -> None:
        for invalid in (
            "0.8",
            "0.8.30+commit.a2be1a0c",
            "v0.8.30",
            "0.8.030",
            "0.8.30.1",
            " 0.8.30",
            "0.8.19",
            "0.8.37",
            "main",
            "",
        ):
            with self.subTest(version=invalid):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaisesRegex(
                        BountyProfileError, "compiler.version"
                    ):
                        initialize(
                            Path(temporary),
                            workspace=Path(temporary) / "review",
                            compiler_version=invalid,
                        )

    def test_pinned_profile_rejects_unknown_compiler_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = initialize(root, compiler_version="0.8.30")
            content = profile.path.read_text(encoding="utf-8")
            profile.path.write_text(
                content.replace(
                    'version = "0.8.30"',
                    'version = "0.8.30"\noptimizer = true',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                BountyProfileError, r"unknown \[compiler\] setting"
            ):
                load_bounty_profile(profile.path)

    def test_legacy_unpinned_digest_literals_are_byte_for_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            one_point_zero = initialize(root)
            self.assertEqual(
                one_point_zero.normalized_payload()["schema_version"],
                "1.0",
            )
            self.assertEqual(
                one_point_zero.digest,
                "8b85c738abe54d897d683e2b2452bc1670548ec4a71de780f4aa448c2e696360",
            )

            with tempfile.TemporaryDirectory() as temporary_two:
                root_two = Path(temporary_two)
                source = root_two / "target"
                source.mkdir()
                (source / "Vault.sol").write_text(
                    "pragma solidity ^0.8.20; contract Vault {}\n",
                    encoding="utf-8",
                )
                one_point_one = initialize_bounty_workspace(
                    root_two / "review",
                    program_name="Example Protocol",
                    platform="Example Bounty",
                    rules_url="https://example.test/rules",
                    reviewed_on="2026-08-09",
                    authorization_acknowledged=True,
                    authorization_note="Local compiler analysis is in scope",
                    source_root=source,
                    source_revision=REVISION,
                    source_content_sha256=None,
                    scope_paths=["contracts/Vault.sol"],
                    impacts=["Loss of funds"],
                    compiler_enabled=True,
                    compiler_dependency_paths=["lib/Dependency.sol"],
                )
                self.assertEqual(
                    one_point_one.normalized_payload()["schema_version"],
                    "1.1",
                )
                self.assertEqual(
                    one_point_one.digest,
                    "7375840d5cbf1980d57bfdd9e14ec2178e631cf5cbc565dfd166ed18eeb5ba39",
                )


class Comp004CompilerTests(unittest.TestCase):
    def test_pinned_compiler_writes_solc_version_in_foundry_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = create_source(root)
            profile = directory_profile(root, compiler_version="0.8.30")
            identity = validate_profile_source(profile)

            class Delegate:
                def compile(self, files, *, project_root=None, offline=False):
                    self.foundry = (project_root / "foundry.toml").read_text(
                        encoding="utf-8"
                    )
                    staged = files[0]
                    return staged_result(staged)

            delegate = Delegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            result = compiler.compile([original], offline=True)

            self.assertIn('solc_version = "0.8.30"', delegate.foundry)
            self.assertNotIn("auto_detect_solc", delegate.foundry)
            self.assertNotIn("optimizer", delegate.foundry)
            self.assertNotIn("evm_version", delegate.foundry)
            self.assertIn("ffi = false", delegate.foundry)
            self.assertEqual(result.sources[0].path, original.resolve())

    def test_unpinned_compiler_keeps_auto_detect_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = create_source(root)
            profile = directory_profile(root, compiler_version=None)
            identity = validate_profile_source(profile)

            class Delegate:
                def compile(self, files, *, project_root=None, offline=False):
                    self.foundry = (project_root / "foundry.toml").read_text(
                        encoding="utf-8"
                    )
                    staged = files[0]
                    return staged_result(staged)

            delegate = Delegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            compiler.compile([original], offline=True)

            self.assertIn("auto_detect_solc = true", delegate.foundry)
            self.assertNotIn("solc_version", delegate.foundry)

    def test_pinned_compiler_fails_closed_unless_exactly_one_release_matches(self) -> None:
        cases = (
            ("0.8.28+commit.80e0e2d2",),
            (),
            ("0.8.25+commit.80e0e2d2", "0.8.30+commit.a2be1a0c"),
            ("0.8.30+commit.a2be1a0c", "0.8.30+commit.b3cf2b1d"),
        )
        for observed in cases:
            with self.subTest(observed=observed):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    original = create_source(root)
                    profile = directory_profile(root, compiler_version="0.8.30")
                    identity = validate_profile_source(profile)

                    class Delegate:
                        def compile(self, files, **kwargs):
                            return staged_result(
                                files[0], compiler_versions=observed
                            )

                    compiler = ScopedForgeCompiler(
                        profile, identity, delegate=Delegate()
                    )
                    with self.assertRaisesRegex(CompilerError, "0.8.30"):
                        compiler.compile([original], offline=True)

    def test_pinned_compiler_accepts_exactly_one_matching_observed_release(self) -> None:
        for observed in (("0.8.30+commit.a2be1a0c",), ("0.8.30",)):
            with self.subTest(observed=observed):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    original = create_source(root)
                    profile = directory_profile(root, compiler_version="0.8.30")
                    identity = validate_profile_source(profile)

                    class Delegate:
                        def compile(self, files, **kwargs):
                            return staged_result(
                                files[0], compiler_versions=observed
                            )

                    compiler = ScopedForgeCompiler(
                        profile, identity, delegate=Delegate()
                    )
                    result = compiler.compile([original], offline=True)
                    self.assertEqual(compiler.compiler_versions, tuple(observed))
                    self.assertEqual(result.sources[0].path, original.resolve())


class Comp004ManifestTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("forge"), "Foundry is required")
    def test_pinned_scan_emits_source_manifest_1_2_and_observed_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_source(root)
            profile = directory_profile(root, compiler_version="0.8.25")
            result = scan_bounty_workspace(profile.workspace)

            self.assertEqual(result.source_manifest["schema_version"], "1.2")
            self.assertEqual(
                result.source_manifest["compiler"]["version"], "0.8.25"
            )
            self.assertFalse(
                result.source_manifest["compiler"]["target_configuration_loaded"]
            )
            self.assertNotIn(
                "dependency_paths", result.source_manifest["compiler"]
            )

            self.assertEqual(result.scan_record["schema_version"], "1.0")
            self.assertEqual(
                result.scan_record["compiler"]["enabled"], True
            )
            versions = result.scan_record["compiler"]["versions"]
            self.assertEqual(len(versions), 1)
            self.assertEqual(parse_version(versions[0]), (0, 8, 25))
            self.assertEqual(
                result.scan_record["profile_sha256"], profile.digest
            )

    def test_profile_and_source_manifest_1_2_schemas_are_packaged(self) -> None:
        schema_directory = files("contract_holes").joinpath("schemas")
        profile_schema = json.loads(
            schema_directory.joinpath(
                "bounty-profile-1.2.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            profile_schema["properties"]["schema_version"]["const"], "1.2"
        )
        self.assertIn(
            "version",
            profile_schema["properties"]["compiler"]["required"],
        )
        self.assertEqual(
            profile_schema["properties"]["compiler"]["properties"]["enabled"][
                "const"
            ],
            True,
        )

        manifest_schema = json.loads(
            schema_directory.joinpath(
                "bounty-source-manifest-1.2.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            manifest_schema["properties"]["schema_version"]["const"], "1.2"
        )
        self.assertIn(
            "version",
            manifest_schema["properties"]["compiler"]["required"],
        )
        self.assertNotIn(
            "compiler_dependency_paths",
            manifest_schema["required"],
        )
        self.assertEqual(
            set(manifest_schema["dependentRequired"]),
            {
                "compiler_dependency_paths",
                "compiler_dependency_files",
                "compiler_dependency_set_sha256",
            },
        )


if __name__ == "__main__":
    unittest.main()
