from pathlib import Path
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner


def node_src(offset: int, length: int = 1) -> str:
    return f"{offset}:{length}:0"


def identifier(node_id: int, offset: int, name: str, reference: int) -> dict:
    return {
        "nodeType": "Identifier",
        "id": node_id,
        "name": name,
        "referencedDeclaration": reference,
        "src": node_src(offset),
    }


def literal(node_id: int, offset: int, value: str = "0") -> dict:
    return {
        "nodeType": "Literal",
        "id": node_id,
        "kind": "number",
        "value": value,
        "src": node_src(offset),
    }


def statement(node_id: int, offset: int, expression: dict) -> dict:
    return {
        "nodeType": "ExpressionStatement",
        "id": node_id,
        "expression": expression,
        "src": node_src(offset),
    }


def function_call(node_id: int, offset: int, name: str, reference: int) -> dict:
    return {
        "nodeType": "FunctionCall",
        "id": node_id,
        "kind": "functionCall",
        "expression": identifier(node_id + 1, offset, name, reference),
        "arguments": [],
        "src": node_src(offset),
    }


def assignment(
    node_id: int, offset: int, name: str, reference: int, value: str = "0"
) -> dict:
    return {
        "nodeType": "Assignment",
        "id": node_id,
        "operator": "=",
        "leftHandSide": identifier(node_id + 1, offset, name, reference),
        "rightHandSide": literal(node_id + 2, offset, value),
        "src": node_src(offset),
    }


def block(node_id: int, offset: int, statements: list[dict]) -> dict:
    return {
        "nodeType": "Block",
        "id": node_id,
        "statements": statements,
        "src": node_src(offset, 80),
    }


def function(
    node_id: int,
    offset: int,
    name: str,
    statements: list[dict],
    *,
    visibility: str = "internal",
    modifiers: list[dict] | None = None,
) -> dict:
    return {
        "nodeType": "FunctionDefinition",
        "id": node_id,
        "name": name,
        "kind": "function",
        "visibility": visibility,
        "parameters": {
            "nodeType": "ParameterList",
            "id": node_id + 1,
            "parameters": [],
            "src": node_src(offset),
        },
        "modifiers": modifiers or [],
        "body": block(node_id + 2, offset, statements),
        "src": node_src(offset, 80),
    }


class ReentrancyAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        balances = {
            "nodeType": "VariableDeclaration",
            "id": 10,
            "name": "balances",
            "stateVariable": True,
            "visibility": "internal",
            "src": node_src(10),
        }
        base = {
            "nodeType": "ContractDefinition",
            "id": 100,
            "name": "BaseVault",
            "contractKind": "contract",
            "linearizedBaseContracts": [100],
            "baseContracts": [],
            "nodes": [balances],
            "src": node_src(0, 90),
        }

        guard_state = {
            "nodeType": "VariableDeclaration",
            "id": 20,
            "name": "_status",
            "stateVariable": True,
            "visibility": "private",
            "src": node_src(90),
        }
        modifier = {
            "nodeType": "ModifierDefinition",
            "id": 30,
            "name": "nonReentrant",
            "body": block(
                31,
                91,
                [
                    {
                        "nodeType": "PlaceholderStatement",
                        "id": 32,
                        "src": node_src(92),
                    }
                ],
            ),
            "src": node_src(91, 10),
        }

        low_level_call = {
            "nodeType": "FunctionCall",
            "id": 1000,
            "kind": "functionCall",
            "expression": {
                "nodeType": "MemberAccess",
                "id": 1001,
                "memberName": "call",
                "expression": {
                    "nodeType": "MemberAccess",
                    "id": 1002,
                    "memberName": "sender",
                    "expression": identifier(1003, 111, "msg", -15),
                    "src": node_src(111),
                },
                "src": node_src(112),
            },
            "arguments": [literal(1004, 113)],
            "src": node_src(110, 5),
        }
        send = function(
            200,
            100,
            "_send",
            [statement(1005, 110, low_level_call)],
        )
        update = function(
            210,
            200,
            "_update",
            [statement(1010, 210, assignment(1011, 210, "balances", 10))],
        )

        vulnerable = function(
            220,
            300,
            "vulnerable",
            [
                statement(1020, 310, function_call(1021, 310, "_send", 200)),
                statement(1030, 320, function_call(1031, 320, "_update", 210)),
            ],
            visibility="external",
        )
        safe = function(
            230,
            400,
            "safe",
            [
                statement(1040, 410, function_call(1041, 410, "_update", 210)),
                statement(1050, 420, function_call(1051, 420, "_send", 200)),
            ],
            visibility="external",
        )
        modifier_invocation = {
            "nodeType": "ModifierInvocation",
            "id": 1060,
            "modifierName": {
                "nodeType": "IdentifierPath",
                "id": 1061,
                "name": "nonReentrant",
                "referencedDeclaration": 30,
                "src": node_src(501),
            },
            "src": node_src(501),
        }
        guarded = function(
            240,
            500,
            "guarded",
            [
                statement(1070, 510, function_call(1071, 510, "_send", 200)),
                statement(1080, 520, function_call(1081, 520, "_update", 210)),
            ],
            visibility="external",
            modifiers=[modifier_invocation],
        )
        manual = function(
            250,
            600,
            "manualGuard",
            [
                statement(1090, 610, assignment(1091, 610, "_status", 20, "1")),
                statement(1100, 620, function_call(1101, 620, "_send", 200)),
                statement(1110, 630, function_call(1111, 630, "_update", 210)),
                statement(1120, 640, assignment(1121, 640, "_status", 20, "0")),
            ],
            visibility="external",
        )
        rhs_call = {
            "nodeType": "FunctionCall",
            "id": 1300,
            "kind": "functionCall",
            "expression": {
                "nodeType": "MemberAccess",
                "id": 1301,
                "memberName": "call",
                "expression": identifier(1302, 711, "target", -1),
                "src": node_src(711),
            },
            "arguments": [],
            "src": node_src(710, 5),
        }
        send_and_return = function(
            260,
            700,
            "_sendAndReturn",
            [statement(1303, 710, rhs_call)],
        )
        nested_call = function_call(1310, 820, "_sendAndReturn", 260)
        assignment_order = function(
            270,
            800,
            "assignmentOrder",
            [
                statement(
                    1320,
                    810,
                    {
                        "nodeType": "Assignment",
                        "id": 1321,
                        "operator": "=",
                        "leftHandSide": identifier(1322, 810, "balances", 10),
                        "rightHandSide": nested_call,
                        "src": node_src(810, 15),
                    },
                )
            ],
            visibility="external",
        )
        derived = {
            "nodeType": "ContractDefinition",
            "id": 300,
            "name": "Vault",
            "contractKind": "contract",
            "linearizedBaseContracts": [300, 100],
            "baseContracts": [
                {
                    "nodeType": "InheritanceSpecifier",
                    "id": 1200,
                    "baseName": {
                        "nodeType": "IdentifierPath",
                        "id": 1201,
                        "name": "BaseVault",
                        "referencedDeclaration": 100,
                        "src": node_src(95),
                    },
                    "src": node_src(95),
                }
            ],
            "nodes": [
                guard_state,
                modifier,
                send,
                update,
                vulnerable,
                safe,
                guarded,
                manual,
                send_and_return,
                assignment_order,
            ],
            "src": node_src(90, 850),
        }
        ast = {
            "nodeType": "SourceUnit",
            "id": 1,
            "nodes": [base, derived],
            "src": node_src(0, 1000),
        }
        self.path = Path("/virtual/Reentrancy.sol")
        compilation = CompilationResult(
            sources=(
                CompiledSource(self.path, 0, "build-a", ast, " " * 1000),
            ),
            compiler_versions=("0.8.25",),
            diagnostics=(),
        )
        self.index = ProjectIndex(compilation)
        self.vulnerable = vulnerable

    def test_unfolds_helpers_and_resolves_inherited_state(self) -> None:
        issues = self.index.reentrancy.issues
        self.assertEqual(len(issues), 2)
        issue = next(
            issue
            for issue in issues
            if self.index.reentrancy.function_name(issue.entry) == "Vault.vulnerable"
        )
        self.assertEqual(
            self.index.reentrancy.function_name(issue.interaction.function),
            "Vault._send",
        )
        self.assertEqual(
            self.index.reentrancy.function_name(issue.state_write.function),
            "Vault._update",
        )
        self.assertEqual(
            self.index.reentrancy.state_variable_name(issue.state_write), "balances"
        )
        self.assertEqual(
            [event.kind for event in issue.trace],
            ["call", "interaction", "call", "write"],
        )

    def test_runtime_order_places_rhs_helper_before_assignment_write(self) -> None:
        issue = next(
            issue
            for issue in self.index.reentrancy.issues
            if self.index.reentrancy.function_name(issue.entry)
            == "Vault.assignmentOrder"
        )
        self.assertEqual(
            [event.kind for event in issue.trace], ["call", "interaction", "write"]
        )

    def test_guards_and_effect_before_interaction_are_not_reported(self) -> None:
        entry_names = {
            self.index.reentrancy.function_name(issue.entry)
            for issue in self.index.reentrancy.issues
        }
        self.assertNotIn("Vault.safe", entry_names)
        self.assertNotIn("Vault.guarded", entry_names)
        self.assertNotIn("Vault.manualGuard", entry_names)

    def test_rule_emits_compiler_trace_metadata(self) -> None:
        source = self.index.source_for_path(self.path).source
        findings = [
            finding
            for finding in Scanner().scan_source(source)
            if finding.rule_id == "SOL005"
        ]
        self.assertEqual(len(findings), 2)
        finding = next(
            finding
            for finding in findings
            if finding.metadata["entry_function"] == "Vault.vulnerable"
        )
        self.assertEqual(finding.metadata["evidence"], "compiler-interprocedural-data-flow")
        self.assertEqual(finding.metadata["entry_function"], "Vault.vulnerable")
        self.assertEqual(finding.metadata["state_variable"], "balances")
        self.assertEqual(
            [event["kind"] for event in finding.metadata["trace"]],
            ["call", "interaction", "call", "write"],
        )


if __name__ == "__main__":
    unittest.main()
