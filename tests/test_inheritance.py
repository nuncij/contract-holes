from pathlib import Path
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.project import NodeKey, ProjectIndex


def base_specifier(specifier_id: int, name_id: int, name: str, reference: int) -> dict:
    return {
        "nodeType": "InheritanceSpecifier",
        "id": specifier_id,
        "src": "0:0:0",
        "baseName": {
            "nodeType": "IdentifierPath",
            "id": name_id,
            "name": name,
            "referencedDeclaration": reference,
            "src": "0:0:0",
        },
    }


def state_variable(node_id: int, name: str, visibility: str = "internal") -> dict:
    return {
        "nodeType": "VariableDeclaration",
        "id": node_id,
        "name": name,
        "stateVariable": True,
        "visibility": visibility,
        "src": "0:0:0",
    }


def parameter(node_id: int, name: str = "value") -> dict:
    return {
        "nodeType": "VariableDeclaration",
        "id": node_id,
        "name": name,
        "stateVariable": False,
        "typeDescriptions": {
            "typeIdentifier": "t_uint256",
            "typeString": "uint256",
        },
        "src": "0:0:0",
    }


def function(
    node_id: int,
    parameter_id: int,
    *,
    base_functions: list[int] | None = None,
    modifiers: list[dict] | None = None,
    body: dict | None = None,
) -> dict:
    return {
        "nodeType": "FunctionDefinition",
        "id": node_id,
        "name": "work",
        "kind": "function",
        "visibility": "internal",
        "baseFunctions": base_functions or [],
        "parameters": {
            "nodeType": "ParameterList",
            "id": parameter_id + 1,
            "parameters": [parameter(parameter_id)],
            "src": "0:0:0",
        },
        "modifiers": modifiers or [],
        "body": body,
        "src": "0:0:0",
    }


def project(contracts: list[dict], text: str = "contract Placeholder {}") -> ProjectIndex:
    ast = {
        "nodeType": "SourceUnit",
        "id": 1,
        "src": f"0:{len(text)}:0",
        "nodes": contracts,
    }
    compilation = CompilationResult(
        sources=(
            CompiledSource(
                path=Path("Inheritance.sol").resolve(),
                source_id=0,
                compilation_id="build-a",
                ast=ast,
                content=text,
            ),
        ),
        compiler_versions=("0.8.25",),
        diagnostics=(),
    )
    return ProjectIndex(compilation)


class InheritanceTests(unittest.TestCase):
    def test_resolves_multilevel_state_overrides_modifiers_and_super(self) -> None:
        base_modifier = {
            "nodeType": "ModifierDefinition",
            "id": 120,
            "name": "guarded",
            "src": "0:0:0",
        }
        base_function = function(110, 111)
        base = {
            "nodeType": "ContractDefinition",
            "id": 100,
            "name": "Base",
            "contractKind": "contract",
            "linearizedBaseContracts": [100],
            "baseContracts": [],
            "nodes": [
                state_variable(101, "baseValue"),
                state_variable(102, "secret", "private"),
                base_modifier,
                base_function,
            ],
            "src": "0:0:0",
        }

        middle_function = function(210, 211, base_functions=[110])
        middle = {
            "nodeType": "ContractDefinition",
            "id": 200,
            "name": "Middle",
            "contractKind": "contract",
            "linearizedBaseContracts": [200, 100],
            "baseContracts": [base_specifier(220, 221, "Base", 100)],
            "nodes": [state_variable(201, "middleValue"), middle_function],
            "src": "0:0:0",
        }

        super_member = {
            "nodeType": "MemberAccess",
            "id": 330,
            "memberName": "work",
            "referencedDeclaration": 210,
            "expression": {
                "nodeType": "Identifier",
                "id": 331,
                "name": "super",
                "referencedDeclaration": -10,
                "src": "0:0:0",
            },
            "src": "0:0:0",
        }
        modifier_name = {
            "nodeType": "IdentifierPath",
            "id": 341,
            "name": "guarded",
            "referencedDeclaration": 120,
            "src": "0:0:0",
        }
        modifier_invocation = {
            "nodeType": "ModifierInvocation",
            "id": 340,
            "modifierName": modifier_name,
            "src": "0:0:0",
        }
        derived_body = {
            "nodeType": "Block",
            "id": 332,
            "statements": [super_member],
            "src": "0:0:0",
        }
        derived_function = function(
            310,
            311,
            base_functions=[210],
            modifiers=[modifier_invocation],
            body=derived_body,
        )
        derived = {
            "nodeType": "ContractDefinition",
            "id": 300,
            "name": "Derived",
            "contractKind": "contract",
            "linearizedBaseContracts": [300, 200, 100],
            "baseContracts": [base_specifier(320, 321, "Middle", 200)],
            "nodes": [state_variable(301, "derivedValue"), derived_function],
            "src": "0:0:0",
        }

        index = project([base, middle, derived])
        resolver = index.inheritance
        semantics = resolver.for_contract(derived)

        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(
            semantics.linearized_contracts,
            (NodeKey("build-a", 300), NodeKey("build-a", 200), NodeKey("build-a", 100)),
        )
        self.assertEqual(semantics.direct_bases, (NodeKey("build-a", 200),))
        self.assertEqual(
            resolver.for_contract(middle).direct_bases,
            (NodeKey("build-a", 100),),
        )
        self.assertEqual(
            [node["name"] for node in resolver.state_variable_nodes(derived)],
            ["baseValue", "secret", "middleValue", "derivedValue"],
        )
        self.assertEqual(
            [node["name"] for node in resolver.state_variable_nodes(derived, visible_only=True)],
            ["baseValue", "middleValue", "derivedValue"],
        )
        self.assertEqual(resolver.effective_function_nodes(derived), (derived_function,))
        self.assertEqual(resolver.effective_modifier_nodes(derived), (base_modifier,))
        self.assertEqual(resolver.overridden_function_nodes(derived_function), (middle_function,))
        self.assertIs(resolver.super_target(super_member).node, middle_function)
        self.assertIs(resolver.modifier_resolutions(derived_function)[0].node, base_modifier)
        self.assertEqual(semantics.unresolved, ())

    def test_diamond_linearization_deduplicates_shared_base_symbols(self) -> None:
        base_state = state_variable(101, "sharedValue")
        base = {
            "nodeType": "ContractDefinition",
            "id": 100,
            "name": "Base",
            "linearizedBaseContracts": [100],
            "baseContracts": [],
            "nodes": [base_state],
            "src": "0:0:0",
        }
        left = {
            "nodeType": "ContractDefinition",
            "id": 200,
            "name": "Left",
            "linearizedBaseContracts": [200, 100],
            "baseContracts": [base_specifier(210, 211, "Base", 100)],
            "nodes": [],
            "src": "0:0:0",
        }
        right = {
            "nodeType": "ContractDefinition",
            "id": 300,
            "name": "Right",
            "linearizedBaseContracts": [300, 100],
            "baseContracts": [base_specifier(310, 311, "Base", 100)],
            "nodes": [],
            "src": "0:0:0",
        }
        diamond = {
            "nodeType": "ContractDefinition",
            "id": 400,
            "name": "Diamond",
            "linearizedBaseContracts": [400, 300, 200, 100, 100],
            "baseContracts": [
                base_specifier(410, 411, "Left", 200),
                base_specifier(412, 413, "Right", 300),
            ],
            "nodes": [],
            "src": "0:0:0",
        }

        index = project([base, left, right, diamond])
        semantics = index.inheritance.for_contract(diamond)

        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(
            semantics.linearized_contracts,
            (
                NodeKey("build-a", 400),
                NodeKey("build-a", 300),
                NodeKey("build-a", 200),
                NodeKey("build-a", 100),
            ),
        )
        self.assertEqual(index.inheritance.state_variable_nodes(diamond), (base_state,))

    def test_unresolved_bases_are_retained_as_labelled_unknowns(self) -> None:
        missing_name = {
            "nodeType": "IdentifierPath",
            "id": 502,
            "name": "Missing",
            "referencedDeclaration": 999,
            "src": "0:0:0",
        }
        broken = {
            "nodeType": "ContractDefinition",
            "id": 500,
            "name": "Broken",
            "linearizedBaseContracts": [500, 999],
            "baseContracts": [
                {
                    "nodeType": "InheritanceSpecifier",
                    "id": 501,
                    "baseName": missing_name,
                    "src": "0:0:0",
                }
            ],
            "nodes": [],
            "src": "0:0:0",
        }

        index = project([broken])
        semantics = index.inheritance.for_contract(broken)
        resolution = index.resolve_reference_detail(missing_name)

        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(resolution.status, "unresolved")
        self.assertEqual(resolution.reference_id, 999)
        self.assertEqual(
            {item.relation for item in semantics.unresolved},
            {"direct-base", "linearized-base"},
        )
        self.assertTrue(all(item.reference_id == 999 for item in semantics.unresolved))


if __name__ == "__main__":
    unittest.main()
