"""Regression tests for the PILOT-007 completion repair.

The independent trial exposed two generic scanner defects that were repaired
before the operational scan was accepted. These tests lock in the repaired
behavior through the public compiler-backed seam:

1. Signature-domain feature propagation must terminate on functions whose
   local variables are assigned the result of a call that passes that same
   variable as an argument. The previous implementation reset the visited set
   per call argument, so such chains recursed without bound.
2. Custom error constructors, event emissions, and struct constructors are not
   external interactions. A real external call must still be detected.

Detector behavior must remain unchanged by this repair; these tests only add
regression coverage.
"""

from pathlib import Path
import shutil
import unittest

from contract_holes.compiler import ForgeCompiler
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner


FIXTURE_ROOT = Path("tests/fixtures/repair_007").resolve()


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for repair tests")
class Repair007Tests(unittest.TestCase):
    def test_signature_domain_propagation_terminates_on_recursive_args(self) -> None:
        compilation = ForgeCompiler().compile(
            [FIXTURE_ROOT / "src" / "Quote.sol"],
            project_root=FIXTURE_ROOT,
            offline=True,
        )
        index = ProjectIndex(compilation)
        self.assertTrue(index.signature.issues is not None)
        # Deterministic: a second identical build gives the same result.
        again = ProjectIndex(
            ForgeCompiler().compile(
                [FIXTURE_ROOT / "src" / "Quote.sol"],
                project_root=FIXTURE_ROOT,
                offline=True,
            )
        )
        self.assertEqual(
            len(index.signature.issues),
            len(again.signature.issues),
        )

    def test_error_event_struct_members_are_not_external_interactions(self) -> None:
        compilation = ForgeCompiler().compile(
            [FIXTURE_ROOT / "src" / "CallKinds.sol"],
            project_root=FIXTURE_ROOT,
            offline=True,
        )
        index = ProjectIndex(compilation)
        source = index.source_for_path(FIXTURE_ROOT / "src" / "CallKinds.sol")
        self.assertIsNotNone(source)

        no_interaction_function = next(
            key
            for key, node in index.functions_by_id.items()
            if node.get("name") == "usesErrorAndEvent"
        )
        self.assertEqual(
            index.data_flow.facts_for(
                function=no_interaction_function, kind="external-interaction"
            ),
            (),
        )

        real_external_function = next(
            key
            for key, node in index.functions_by_id.items()
            if node.get("name") == "realExternal"
        )
        interactions = index.data_flow.facts_for(
            function=real_external_function, kind="external-interaction"
        )
        self.assertEqual(len(interactions), 1)

        findings = [f for f in Scanner().scan_source(source.source)]
        sol005 = [f for f in findings if f.rule_id == "SOL005"]
        sol008 = [f for f in findings if f.rule_id == "SOL008"]
        self.assertEqual(len(sol005), 1)
        self.assertEqual(
            sol005[0].metadata.get("entry_function"),
            "CallKinds.realExternal",
        )
        self.assertEqual(sol008, [])


if __name__ == "__main__":
    unittest.main()
