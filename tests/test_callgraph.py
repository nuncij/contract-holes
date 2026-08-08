import json
from pathlib import Path
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.project import NodeKey, ProjectIndex


def block(node_id: int, statements: list[dict] | None = None) -> dict:
    return {
        "nodeType": "Block",
        "id": node_id,
        "statements": statements or [],
        "src": f"{node_id}:1:0",
    }


def function(
    node_id: int,
    name: str,
    *,
    visibility: str = "internal",
    body_node: dict | None = None,
    modifiers: list[dict] | None = None,
) -> dict:
    return {
        "nodeType": "FunctionDefinition",
        "id": node_id,
        "name": name,
        "kind": "function",
        "visibility": visibility,
        "parameters": {"nodeType": "ParameterList", "parameters": [], "src": "0:0:0"},
        "modifiers": modifiers or [],
        "body": body_node,
        "src": f"{node_id}:1:0",
    }


def identifier(node_id: int, name: str, reference: int, type_string: str = "") -> dict:
    return {
        "nodeType": "Identifier",
        "id": node_id,
        "name": name,
        "referencedDeclaration": reference,
        "typeDescriptions": {"typeString": type_string},
        "src": f"{node_id}:1:0",
    }


def member(
    node_id: int,
    name: str,
    owner: dict,
    reference: int | None = None,
) -> dict:
    result = {
        "nodeType": "MemberAccess",
        "id": node_id,
        "memberName": name,
        "expression": owner,
        "src": f"{node_id}:1:0",
    }
    if reference is not None:
        result["referencedDeclaration"] = reference
    return result


def call(node_id: int, expression: dict) -> dict:
    return {
        "nodeType": "FunctionCall",
        "id": node_id,
        "kind": "functionCall",
        "expression": expression,
        "arguments": [],
        "src": f"{node_id}:1:0",
    }


class CallGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        library_function = function(101, "libWork", body_node=block(102))
        library = {
            "nodeType": "ContractDefinition",
            "id": 100,
            "name": "WorkLibrary",
            "contractKind": "library",
            "linearizedBaseContracts": [100],
            "baseContracts": [],
            "nodes": [library_function],
            "src": "100:1:0",
        }
        interface_function = function(201, "ping", visibility="external")
        interface = {
            "nodeType": "ContractDefinition",
            "id": 200,
            "name": "IPing",
            "contractKind": "interface",
            "linearizedBaseContracts": [200],
            "baseContracts": [],
            "nodes": [interface_function],
            "src": "200:1:0",
        }
        base_function = function(301, "baseWork", body_node=block(302))
        base = {
            "nodeType": "ContractDefinition",
            "id": 300,
            "name": "Base",
            "contractKind": "contract",
            "linearizedBaseContracts": [300],
            "baseContracts": [],
            "nodes": [base_function],
            "src": "300:1:0",
        }

        modifier_definition = {
            "nodeType": "ModifierDefinition",
            "id": 410,
            "name": "guarded",
            "body": block(411),
            "src": "410:1:0",
        }
        modifier_invocation = {
            "nodeType": "ModifierInvocation",
            "id": 530,
            "modifierName": {
                "nodeType": "IdentifierPath",
                "id": 531,
                "name": "guarded",
                "referencedDeclaration": 410,
                "src": "531:1:0",
            },
            "src": "530:1:0",
        }
        helper_function = function(420, "helper", body_node=block(421))
        recursive_call = call(432, identifier(433, "recursive", 430))
        recursive_function = function(
            430, "recursive", body_node=block(431, [recursive_call])
        )
        public_function = function(
            440, "publicWork", visibility="external", body_node=block(441)
        )
        function_pointer = {
            "nodeType": "VariableDeclaration",
            "id": 401,
            "name": "callback",
            "stateVariable": True,
            "visibility": "internal",
            "typeDescriptions": {"typeString": "function () external"},
            "src": "401:1:0",
        }

        calls = [
            call(500, identifier(501, "helper", 420)),
            call(502, identifier(503, "baseWork", 301)),
            call(
                504,
                member(505, "baseWork", identifier(506, "super", -10), 301),
            ),
            call(
                507,
                member(508, "libWork", identifier(509, "WorkLibrary", 100), 101),
            ),
            call(
                510,
                member(511, "publicWork", identifier(512, "this", -28), 440),
            ),
            call(
                513,
                member(514, "ping", identifier(515, "remote", 900), 201),
            ),
            call(
                516,
                member(517, "call", identifier(518, "target", 901)),
            ),
            call(
                519,
                identifier(520, "callback", 401, "function () external"),
            ),
            call(
                521,
                member(522, "mystery", identifier(523, "target", 901), 999),
            ),
            call(524, identifier(525, "require", -18)),
            call(
                526,
                member(527, "encodePacked", identifier(528, "abi", -1)),
            ),
        ]
        entry_function = function(
            450,
            "entry",
            visibility="external",
            body_node=block(451, calls),
            modifiers=[modifier_invocation],
        )
        derived = {
            "nodeType": "ContractDefinition",
            "id": 400,
            "name": "Derived",
            "contractKind": "contract",
            "linearizedBaseContracts": [400, 300],
            "baseContracts": [
                {
                    "nodeType": "InheritanceSpecifier",
                    "id": 460,
                    "baseName": {
                        "nodeType": "IdentifierPath",
                        "id": 461,
                        "name": "Base",
                        "referencedDeclaration": 300,
                        "src": "461:1:0",
                    },
                    "src": "460:1:0",
                }
            ],
            "nodes": [
                function_pointer,
                modifier_definition,
                helper_function,
                recursive_function,
                public_function,
                entry_function,
            ],
            "src": "400:1:0",
        }
        ast = {
            "nodeType": "SourceUnit",
            "id": 1,
            "src": "0:1000:0",
            "nodes": [library, interface, base, derived],
        }
        compilation = CompilationResult(
            sources=(
                CompiledSource(
                    Path("/virtual/CallGraph.sol"),
                    0,
                    "build-a",
                    ast,
                    " " * 1000,
                ),
            ),
            compiler_versions=("0.8.25",),
            diagnostics=(),
        )
        self.index = ProjectIndex(compilation)
        self.graph = self.index.call_graph
        self.entry = entry_function
        self.helper = helper_function
        self.base_function = base_function
        self.library_function = library_function
        self.interface_function = interface_function
        self.public_function = public_function
        self.recursive = recursive_function
        self.modifier = modifier_definition

    def test_classifies_resolved_and_dynamic_edges(self) -> None:
        edges = self.graph.edges_from(self.entry)
        by_kind = {edge.kind: edge for edge in edges}

        self.assertIs(self.index.node_for_key(by_kind["internal"].callee), self.base_function)
        internal_callees = {
            self.index.node_for_key(edge.callee)["name"]
            for edge in edges
            if edge.kind == "internal" and edge.callee
        }
        self.assertEqual(internal_callees, {"helper", "baseWork"})
        self.assertIs(self.index.node_for_key(by_kind["super"].callee), self.base_function)
        self.assertIs(self.index.node_for_key(by_kind["library"].callee), self.library_function)
        self.assertFalse(by_kind["library"].is_sink)
        self.assertIs(
            self.index.node_for_key(by_kind["external-self"].callee),
            self.public_function,
        )
        self.assertTrue(by_kind["external-self"].is_sink)
        self.assertIs(
            self.index.node_for_key(by_kind["external"].callee),
            self.interface_function,
        )
        self.assertEqual(by_kind["external"].confidence, "declaration")
        self.assertTrue(by_kind["external"].is_sink)
        self.assertFalse(by_kind["low-level-call"].resolved)
        self.assertTrue(by_kind["low-level-call"].is_sink)
        self.assertEqual(by_kind["function-pointer"].confidence, "dynamic")
        self.assertTrue(by_kind["function-pointer"].is_sink)
        self.assertEqual(by_kind["external-dynamic"].target, "mystery")
        self.assertTrue(by_kind["external-dynamic"].reason)
        self.assertIs(self.index.node_for_key(by_kind["modifier"].callee), self.modifier)
        self.assertNotIn("encodePacked", {edge.target for edge in edges})

    def test_cycle_safe_reachability_and_sink_policy(self) -> None:
        recursive_key = self.index.key_for_node(self.recursive)
        self.assertEqual(self.graph.reachable_from(self.recursive), (recursive_key,))

        default_reachable = {
            self.index.node_for_key(key)["name"]
            for key in self.graph.reachable_from(self.entry)
        }
        self.assertEqual(
            default_reachable,
            {"entry", "guarded", "helper", "baseWork", "libWork"},
        )
        with_sinks = {
            self.index.node_for_key(key)["name"]
            for key in self.graph.reachable_from(self.entry, include_sinks=True)
        }
        self.assertIn("publicWork", with_sinks)
        self.assertIn("ping", with_sinks)

    def test_debug_serialization_is_deterministic(self) -> None:
        first = self.graph.to_dict()
        second = self.graph.to_dict()

        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )
        self.assertEqual(first["schema_version"], "1.0")
        self.assertTrue(first["nodes"])
        self.assertTrue(first["edges"])
        self.assertEqual(
            [edge["call_site"] for edge in first["edges"]],
            [edge["call_site"] for edge in second["edges"]],
        )


if __name__ == "__main__":
    unittest.main()
