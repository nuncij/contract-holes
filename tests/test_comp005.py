from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes.bounty_profile import initialize_bounty_workspace
from contract_holes.bounty_scope import (
    BountyScopeError,
    ScopedForgeCompiler,
    identify_source,
    scan_bounty_workspace,
    validate_profile_source,
)
from contract_holes.compiler import CompilationResult, CompiledSource


REPORTABLE_IMPORTING_DEPENDENCY = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "example-lib/src/Dependency.sol";
contract Vault is Dependency {}
"""

DEPENDENCY_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
abstract contract Dependency {}
"""


def create_target(root: Path, relative: str, text: str) -> None:
    path = root / "target" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_profile(
    root: Path,
    *,
    scope: tuple[str, ...] = ("src/Vault.sol",),
    compiler_dependencies: tuple[str, ...] = (),
    compiler_version: str | None = None,
):
    target = root / "target"
    identity = identify_source(
        target,
        scope,
        compiler_dependency_paths=compiler_dependencies,
    )
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
        compiler_enabled=True,
        compiler_dependency_paths=compiler_dependencies,
        compiler_version=compiler_version,
    )


class CapturingDelegate:
    def __init__(self):
        self.remappings = ""
        self.foundry = ""
        self.offline = None
        self.root = None

    def compile(self, files, *, project_root=None, offline=False):
        self.root = project_root
        self.offline = offline
        remappings_path = project_root / "remappings.txt"
        self.remappings = (
            remappings_path.read_text(encoding="utf-8")
            if remappings_path.exists()
            else ""
        )
        self.foundry = (project_root / "foundry.toml").read_text(encoding="utf-8")
        sources = []
        for path in sorted(project_root.rglob("*.sol")):
            sources.append(
                CompiledSource(
                    path=path,
                    source_id=len(sources),
                    compilation_id="safe-build",
                    ast={
                        "nodeType": "SourceUnit",
                        "src": f"0:1:{len(sources)}",
                    },
                    content=path.read_text(encoding="utf-8"),
                )
            )
        return CompilationResult(
            sources=tuple(sources),
            compiler_versions=("0.8.25",),
            diagnostics=(),
        )


class Comp005RemappingTests(unittest.TestCase):
    def test_uncovered_direct_library_import_derives_mapping_and_compiles(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            create_target(root, "lib/example-lib/src/Dependency.sol", DEPENDENCY_SOURCE)
            profile = make_profile(
                root,
                compiler_dependencies=("lib/example-lib/src/Dependency.sol",),
            )
            identity = validate_profile_source(profile)
            reportable = root / "target" / "src/Vault.sol"

            delegate = CapturingDelegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            result = compiler.compile([reportable], offline=True)

            self.assertIn("example-lib/=lib/example-lib/", delegate.remappings)
            self.assertEqual(
                {source.path for source in result.sources},
                {
                    reportable.resolve(),
                    (root / "target/lib/example-lib/src/Dependency.sol").resolve(),
                },
            )
            self.assertIn("libs = []", delegate.foundry)

    def test_explicit_validated_remapping_is_authoritative_and_not_duplicated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            create_target(root, "lib/example-lib/src/Dependency.sol", DEPENDENCY_SOURCE)
            create_target(
                root,
                "remappings.txt",
                "example-lib/=lib/example-lib/\n",
            )
            profile = make_profile(
                root,
                compiler_dependencies=("lib/example-lib/src/Dependency.sol",),
            )
            identity = validate_profile_source(profile)
            reportable = root / "target" / "src/Vault.sol"

            delegate = CapturingDelegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            compiler.compile([reportable], offline=True)

            self.assertEqual(
                delegate.remappings,
                "example-lib/=lib/example-lib/\n",
            )
            self.assertEqual(
                [
                    line
                    for line in delegate.remappings.splitlines()
                    if line == "example-lib/=lib/example-lib/"
                ],
                ["example-lib/=lib/example-lib/"],
            )

    def test_explicit_remapping_for_other_lib_stays_before_derived_in_order(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            create_target(root, "lib/example-lib/src/Dependency.sol", DEPENDENCY_SOURCE)
            create_target(root, "lib/alpha/src/A.sol", DEPENDENCY_SOURCE)
            create_target(
                root,
                "remappings.txt",
                "alpha/=lib/alpha/src/\n",
            )
            reportable_text = REPORTABLE_IMPORTING_DEPENDENCY.replace(
                'import "example-lib/src/Dependency.sol";\n',
                'import "alpha/A.sol";\nimport "example-lib/src/Dependency.sol";\n',
            )
            create_target(root, "src/Vault.sol", reportable_text)
            profile = make_profile(
                root,
                compiler_dependencies=(
                    "lib/example-lib/src/Dependency.sol",
                    "lib/alpha/src/A.sol",
                ),
            )
            identity = validate_profile_source(profile)
            reportable = root / "target" / "src/Vault.sol"

            delegate = CapturingDelegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            compiler.compile([reportable], offline=True)

            lines = delegate.remappings.splitlines()
            self.assertEqual(lines[0], "alpha/=lib/alpha/src/")
            self.assertIn("example-lib/=lib/example-lib/", lines)
            self.assertNotIn("alpha/=lib/alpha/", lines)

    def test_undeclared_direct_library_import_derives_no_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            profile = make_profile(root)
            identity = validate_profile_source(profile)
            reportable = root / "target" / "src/Vault.sol"

            delegate = CapturingDelegate()
            compiler = ScopedForgeCompiler(profile, identity, delegate=delegate)
            compiler.compile([reportable], offline=True)

            self.assertEqual(delegate.remappings, "")

    def test_multiple_derived_mappings_are_lexically_ordered_and_deterministic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(
                root,
                "src/Vault.sol",
                """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "zeta-lib/src/Z.sol";
import "alpha-lib/src/A.sol";
contract Vault is ZetaDep, AlphaDep {}
""",
            )
            create_target(
                root,
                "lib/alpha-lib/src/A.sol",
                "pragma solidity ^0.8.20; abstract contract AlphaDep {}\n",
            )
            create_target(
                root,
                "lib/zeta-lib/src/Z.sol",
                "pragma solidity ^0.8.20; abstract contract ZetaDep {}\n",
            )
            profile = make_profile(
                root,
                compiler_dependencies=(
                    "lib/alpha-lib/src/A.sol",
                    "lib/zeta-lib/src/Z.sol",
                ),
            )
            identity = validate_profile_source(profile)
            reportable = root / "target" / "src/Vault.sol"

            first = CapturingDelegate()
            ScopedForgeCompiler(profile, identity, delegate=first).compile(
                [reportable], offline=True
            )
            second = CapturingDelegate()
            ScopedForgeCompiler(profile, identity, delegate=second).compile(
                [reportable], offline=True
            )

            expected = "alpha-lib/=lib/alpha-lib/\nzeta-lib/=lib/zeta-lib/\n"
            self.assertEqual(first.remappings, expected)
            self.assertEqual(first.remappings, second.remappings)


class Comp005IdentityTests(unittest.TestCase):
    def test_self_contained_fixture_keeps_exact_legacy_identities(self) -> None:
        source = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract ScopedVault {
    function ownerOnly() external view returns (bool) {
        return tx.origin == msg.sender;
    }
}
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", source)
            profile = make_profile(root, scope=("src",))
            result = scan_bounty_workspace(profile.workspace)

            self.assertEqual(
                result.source_identity.source_set_sha256,
                "28cb5c36386273c60d8fc0179ea3899e62851992ade379020bff7a2e9075b3a8",
            )
            self.assertIsNone(result.source_identity.remappings_sha256)
            self.assertEqual(result.source_manifest["schema_version"], "1.0")
            self.assertEqual(
                result.source_manifest["compiler"]["isolation"],
                "staged-approved-sources",
            )
            self.assertEqual(
                result.source_manifest["manifest_sha256"],
                "6cf63133ab77605e157622cf6794d69bb3577dd2bc65ff3a617fb90eb9794804",
            )
            self.assertEqual(
                result.scan_record["scan_sha256"],
                "f46dd3004bb91ff1eb467efba17f818394ef71b4b0a7ee2582f94ab0a624604b",
            )

    def test_self_contained_fixture_with_compiler_dependency_keeps_identities(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(
                root,
                "src/Vault.sol",
                'pragma solidity ^0.8.20; import "lib/Dependency.sol";'
                " contract Vault is Dependency {}\n",
            )
            create_target(
                root,
                "lib/Dependency.sol",
                "pragma solidity ^0.8.20; abstract contract Dependency {}\n",
            )
            profile = make_profile(
                root,
                compiler_dependencies=("lib/Dependency.sol",),
            )
            identity = validate_profile_source(profile)
            result = scan_bounty_workspace(profile.workspace)

            self.assertEqual(result.source_manifest["schema_version"], "1.1")
            self.assertIsNone(result.source_identity.remappings_sha256)
            self.assertEqual(
                result.source_identity.source_set_sha256,
                identity.source_set_sha256,
            )


class Comp005IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("forge"), "Foundry is required")
    def test_uncovered_direct_library_import_compiles_with_real_forge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            create_target(root, "lib/example-lib/src/Dependency.sol", DEPENDENCY_SOURCE)
            profile = make_profile(
                root,
                compiler_dependencies=("lib/example-lib/src/Dependency.sol",),
                compiler_version="0.8.25",
            )
            first = scan_bounty_workspace(profile.workspace)
            second = scan_bounty_workspace(profile.workspace)

            self.assertEqual(first.scan_record, second.scan_record)
            self.assertEqual(first.source_manifest, second.source_manifest)
            self.assertEqual(first.source_manifest["schema_version"], "1.2")
            self.assertEqual(
                first.source_manifest["compiler_dependency_paths"],
                ["lib/example-lib/src/Dependency.sol"],
            )
            self.assertEqual(
                [entry["path"] for entry in first.source_manifest["files"]],
                ["src/Vault.sol"],
            )

    @unittest.skipUnless(shutil.which("forge"), "Foundry is required")
    def test_undeclared_direct_library_import_fails_closed_with_real_forge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_target(root, "src/Vault.sol", REPORTABLE_IMPORTING_DEPENDENCY)
            profile = make_profile(root, compiler_version="0.8.25")
            with self.assertRaises(BountyScopeError):
                scan_bounty_workspace(profile.workspace)


if __name__ == "__main__":
    unittest.main()
