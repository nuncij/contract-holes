"""Regression tests for the PILOT-007 completion repair.

The independent trial exposed two generic scanner defects that were repaired
before the operational scan was accepted. These tests lock in the repaired
behavior through the public compiler-backed seam and assert stable public
evidence, not internal state:

1. Signature-domain feature propagation must terminate on functions whose
   local variables are assigned the result of a call that passes that same
   variable as an argument. The previous implementation reset the visited set
   per call argument, so such chains recursed without bound. `Quote.sol` has
   no recovery site, so the expected result is a completed analysis with no
   signature issues and no recovery facts.
2. Custom error constructors, event emissions, and struct constructors are not
   external interactions, while a real external call still is. The retained
   `SOL005` finding on the real call is asserted with its stable public path,
   line, kind, entry function, evidence, and target-provenance fields.

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
CALL_KINDS = FIXTURE_ROOT / "src" / "CallKinds.sol"
QUOTE = FIXTURE_ROOT / "src" / "Quote.sol"


@unittest.skipUnless(shutil.which("forge"), "Foundry is required for repair tests")
class Repair007Tests(unittest.TestCase):
    def test_signature_domain_propagation_terminates_with_expected_result(self) -> None:
        compilation = ForgeCompiler().compile(
            [QUOTE], project_root=FIXTURE_ROOT, offline=True
        )
        index = ProjectIndex(compilation)
        # The recursive-argument chain terminates: the fixture has no recovery
        # site, so the expected semantic result is a completed analysis with
        # zero signature issues and zero recovery facts.
        self.assertEqual(index.signature.issues, ())
        self.assertEqual(
            index.data_flow.facts_for(kind="signature-recovery"),
            (),
        )

    def test_error_event_struct_members_are_not_external_interactions(self) -> None:
        compilation = ForgeCompiler().compile(
            [CALL_KINDS], project_root=FIXTURE_ROOT, offline=True
        )
        index = ProjectIndex(compilation)
        source = index.source_for_path(CALL_KINDS)
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
        self.assertEqual(interactions[0].metadata.get("edge_kind"), "external")
        self.assertEqual(interactions[0].metadata.get("target"), "ping")
        self.assertEqual(interactions[0].span.line, 31)

        findings = [f for f in Scanner().scan_source(source.source)]
        sol005 = [f for f in findings if f.rule_id == "SOL005"]
        sol008 = [f for f in findings if f.rule_id == "SOL008"]
        self.assertEqual(sol008, [])
        self.assertEqual(len(sol005), 1)
        finding = sol005[0]
        self.assertEqual(finding.path, CALL_KINDS)
        self.assertEqual(finding.line, 31)
        self.assertEqual(finding.column, 18)
        self.assertEqual(finding.metadata["evidence"], "compiler-interprocedural-data-flow")
        self.assertEqual(finding.metadata["entry_function"], "CallKinds.realExternal")
        self.assertEqual(finding.metadata["state_variable"], "stored")
        self.assertEqual(finding.metadata["interaction_function"], "CallKinds.realExternal")
        self.assertEqual(finding.metadata["interaction_line"], 31)
        self.assertEqual(finding.metadata["mutation_line"], 31)
        self.assertEqual(
            [event["kind"] for event in finding.metadata["trace"]],
            ["interaction", "write"],
        )
        self.assertEqual(
            finding.metadata["target_provenance"],
            {
                "declarations": ["counter"],
                "kind": "immutable-state",
                "user_controlled": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
