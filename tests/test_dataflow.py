import json
from pathlib import Path
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.project import ProjectIndex
from contract_holes.scanner import Scanner


def identifier(node_id: int, name: str, reference: int) -> dict:
    return {
        "nodeType": "Identifier",
        "id": node_id,
        "name": name,
        "referencedDeclaration": reference,
        "src": f"{node_id}:1:0",
    }


def literal(node_id: int) -> dict:
    return {
        "nodeType": "Literal",
        "id": node_id,
        "kind": "number",
        "value": "0",
        "src": f"{node_id}:1:0",
    }


def declaration(node_id: int, name: str, *, state: bool = False) -> dict:
    return {
        "nodeType": "VariableDeclaration",
        "id": node_id,
        "name": name,
        "stateVariable": state,
        "visibility": "internal",
        "src": f"{node_id}:1:0",
    }


def expression_statement(node_id: int, expression: dict) -> dict:
    return {
        "nodeType": "ExpressionStatement",
        "id": node_id,
        "expression": expression,
        "src": f"{node_id}:1:0",
    }


def require_call(node_id: int, condition: dict) -> dict:
    return {
        "nodeType": "FunctionCall",
        "id": node_id,
        "kind": "functionCall",
        "expression": identifier(node_id + 1_000, "require", -18),
        "arguments": [condition],
        "src": f"{node_id}:1:0",
    }


class DataFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        owner = declaration(2, "owner", state=True)
        stored = declaration(3, "stored", state=True)
        allowed = declaration(4, "allowed", state=True)
        target_parameter = declaration(10, "target")
        amount_parameter = declaration(11, "amount")
        flag_parameter = declaration(12, "flag")
        alias = declaration(20, "aliasAmount")
        selected = declaration(21, "selected")
        success = declaration(22, "success")

        alias_statement = {
            "nodeType": "VariableDeclarationStatement",
            "id": 100,
            "declarations": [alias],
            "initialValue": identifier(101, "amount", 11),
            "src": "100:1:0",
        }
        selected_statement = {
            "nodeType": "VariableDeclarationStatement",
            "id": 102,
            "declarations": [selected],
            "initialValue": literal(103),
            "src": "102:1:0",
        }
        branch_assignment = {
            "nodeType": "Assignment",
            "id": 106,
            "operator": "=",
            "leftHandSide": identifier(107, "selected", 21),
            "rightHandSide": identifier(108, "amount", 11),
            "src": "106:1:0",
        }
        branch = {
            "nodeType": "IfStatement",
            "id": 104,
            "condition": identifier(105, "flag", 12),
            "trueBody": expression_statement(109, branch_assignment),
            "falseBody": None,
            "src": "104:1:0",
        }

        sender = {
            "nodeType": "MemberAccess",
            "id": 113,
            "memberName": "sender",
            "expression": identifier(114, "msg", -15),
            "src": "113:1:0",
        }
        owner_check = {
            "nodeType": "BinaryOperation",
            "id": 112,
            "operator": "==",
            "leftExpression": sender,
            "rightExpression": identifier(115, "owner", 2),
            "src": "112:1:0",
        }
        owner_require = expression_statement(110, require_call(111, owner_check))

        allowed_sender = {
            "nodeType": "MemberAccess",
            "id": 120,
            "memberName": "sender",
            "expression": identifier(121, "msg", -15),
            "src": "120:1:0",
        }
        allowed_check = {
            "nodeType": "IndexAccess",
            "id": 119,
            "baseExpression": identifier(122, "allowed", 4),
            "indexExpression": allowed_sender,
            "src": "119:1:0",
        }
        allowed_require = expression_statement(117, require_call(118, allowed_check))

        state_assignment = {
            "nodeType": "Assignment",
            "id": 124,
            "operator": "=",
            "leftHandSide": identifier(125, "stored", 3),
            "rightHandSide": identifier(126, "aliasAmount", 20),
            "src": "124:1:0",
        }

        ignored_call = {
            "nodeType": "FunctionCall",
            "id": 130,
            "kind": "functionCall",
            "expression": {
                "nodeType": "FunctionCallOptions",
                "id": 131,
                "names": ["value"],
                "options": [identifier(132, "selected", 21)],
                "expression": {
                    "nodeType": "MemberAccess",
                    "id": 133,
                    "memberName": "call",
                    "expression": identifier(134, "target", 10),
                    "src": "133:1:0",
                },
                "src": "131:1:0",
            },
            "arguments": [literal(135)],
            "src": "130:1:0",
        }
        assigned_call = {
            "nodeType": "FunctionCall",
            "id": 140,
            "kind": "functionCall",
            "expression": {
                "nodeType": "MemberAccess",
                "id": 141,
                "memberName": "call",
                "expression": identifier(142, "target", 10),
                "src": "141:1:0",
            },
            "arguments": [literal(143)],
            "src": "140:1:0",
        }
        success_statement = {
            "nodeType": "VariableDeclarationStatement",
            "id": 144,
            "declarations": [success],
            "initialValue": assigned_call,
            "src": "144:1:0",
        }
        assembly = {
            "nodeType": "InlineAssembly",
            "id": 150,
            "src": "150:1:0",
        }
        body = {
            "nodeType": "Block",
            "id": 90,
            "statements": [
                alias_statement,
                selected_statement,
                branch,
                owner_require,
                allowed_require,
                expression_statement(123, state_assignment),
                expression_statement(129, ignored_call),
                success_statement,
                assembly,
            ],
            "src": "90:100:0",
        }
        process = {
            "nodeType": "FunctionDefinition",
            "id": 30,
            "name": "process",
            "kind": "function",
            "visibility": "external",
            "parameters": {
                "nodeType": "ParameterList",
                "id": 31,
                "parameters": [target_parameter, amount_parameter, flag_parameter],
                "src": "31:1:0",
            },
            "modifiers": [],
            "body": body,
            "src": "30:170:0",
        }
        contract = {
            "nodeType": "ContractDefinition",
            "id": 1_000,
            "name": "Flow",
            "contractKind": "contract",
            "linearizedBaseContracts": [1_000],
            "baseContracts": [],
            "nodes": [owner, stored, allowed, process],
            "src": "0:300:0",
        }
        ast = {
            "nodeType": "SourceUnit",
            "id": 2_000,
            "src": "0:300:0",
            "nodes": [contract],
        }
        compilation = CompilationResult(
            sources=(
                CompiledSource(
                    Path("/virtual/Flow.sol"),
                    0,
                    "build-a",
                    ast,
                    " " * 300,
                ),
            ),
            compiler_versions=("0.8.25",),
            diagnostics=(),
        )
        self.index = ProjectIndex(compilation)
        self.flow = self.index.data_flow
        self.process = process
        self.alias = alias
        self.selected = selected
        self.success = success
        self.stored = stored

    def test_tracks_inputs_aliases_branch_merge_and_state_write(self) -> None:
        facts = self.flow.facts_for(function=self.process)
        external_inputs = [
            fact
            for fact in facts
            if fact.kind == "input" and fact.metadata.get("externally_controlled") is True
        ]
        self.assertEqual(
            {fact.metadata["name"] for fact in external_inputs},
            {"target", "amount", "flag", "msg.sender"},
        )

        alias_fact = next(
            fact
            for fact in facts
            if fact.kind == "alias"
            and fact.declaration == self.index.key_for_node(self.alias)
        )
        self.assertTrue(alias_fact.value.user_controlled)
        self.assertIn(self.index.key_for_node(self.alias), {
            fact.declaration for fact in facts if fact.kind == "write"
        })

        state_write = next(
            fact
            for fact in facts
            if fact.kind == "write"
            and fact.declaration == self.index.key_for_node(self.stored)
        )
        self.assertEqual(state_write.metadata["scope"], "state")
        self.assertTrue(state_write.value.user_controlled)

        transfer = next(fact for fact in facts if fact.kind == "value-transfer")
        self.assertTrue(transfer.value.user_controlled)
        self.assertFalse(transfer.value.unknown)

    def test_external_interactions_auth_and_unknowns_are_explicit(self) -> None:
        facts = self.flow.facts_for(function=self.process)
        interactions = [fact for fact in facts if fact.kind == "external-interaction"]
        self.assertEqual(len(interactions), 2)
        self.assertEqual(
            {fact.metadata["result_ignored"] for fact in interactions},
            {True, False},
        )

        success_alias = next(
            fact
            for fact in facts
            if fact.kind == "alias"
            and fact.declaration == self.index.key_for_node(self.success)
        )
        self.assertIn("external-return", success_alias.value.taints)
        self.assertTrue(success_alias.value.unknown)

        authorization = [fact for fact in facts if fact.kind == "authorization"]
        mechanisms = {
            mechanism
            for fact in authorization
            for mechanism in fact.metadata["mechanisms"]
        }
        self.assertIn("msg.sender", mechanisms)
        self.assertIn("mapping:allowed:msg.sender", mechanisms)

        unknowns = [fact for fact in facts if fact.kind == "unknown-expression"]
        self.assertIn("InlineAssembly", {fact.metadata.get("node_type") for fact in unknowns})

    def test_fact_queries_and_serialization_are_stable(self) -> None:
        interactions = self.flow.facts_for(
            kind="external-interaction", path=Path("/virtual/Flow.sol")
        )
        self.assertEqual(len(interactions), 2)
        first = self.flow.to_dict()
        second = self.flow.to_dict()
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["schema_version"], "1.0")

    def test_unchecked_call_rule_consumes_data_flow_facts(self) -> None:
        source = self.index.source_for_path(Path("/virtual/Flow.sol")).source

        findings = [
            finding
            for finding in Scanner().scan_source(source)
            if finding.rule_id == "SOL002"
        ]

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].metadata["evidence"], "compiler-data-flow")
        self.assertEqual(findings[0].metadata["call_kind"], "call")
        self.assertEqual(findings[0].metadata["target"], "target")


if __name__ == "__main__":
    unittest.main()
