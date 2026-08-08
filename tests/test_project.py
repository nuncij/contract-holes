from pathlib import Path
import tempfile
import unittest

from contract_holes.compiler import CompilationResult, CompiledSource
from contract_holes.project import NodeKey, ProjectIndex


def src_for(text: str, fragment: str, source_id: int) -> str:
    start = text.index(fragment)
    byte_start = len(text[:start].encode("utf-8"))
    byte_length = len(fragment.encode("utf-8"))
    return f"{byte_start}:{byte_length}:{source_id}"


class ProjectIndexTests(unittest.TestCase):
    def test_indexes_imported_remapped_source_and_resolves_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dependency_path = root / "lib" / "example" / "src" / "Dep.sol"
            main_path = root / "src" / "Main.sol"
            dependency_text = "// ž\ncontract Dep { uint256 value; }"
            main_text = (
                'import {Dep} from "example/Dep.sol";\n'
                "contract Main is Dep { function get() external view returns (uint256) { "
                "return value; } }"
            )

            dependency_contract = {
                "nodeType": "ContractDefinition",
                "id": 100,
                "name": "Dep",
                "contractKind": "contract",
                "src": src_for(dependency_text, "contract Dep { uint256 value; }", 1),
                "nodes": [
                    {
                        "nodeType": "VariableDeclaration",
                        "id": 101,
                        "name": "value",
                        "stateVariable": True,
                        "src": src_for(dependency_text, "uint256 value", 1),
                    }
                ],
            }
            dependency_ast = {
                "nodeType": "SourceUnit",
                "id": 1_000,
                "src": f"0:{len(dependency_text.encode('utf-8'))}:1",
                "nodes": [dependency_contract],
            }

            inherited_reference = {
                "nodeType": "IdentifierPath",
                "id": 201,
                "name": "Dep",
                "referencedDeclaration": 100,
                "src": src_for(main_text, "Dep", 0),
            }
            value_reference = {
                "nodeType": "Identifier",
                "id": 204,
                "name": "value",
                "referencedDeclaration": 101,
                "src": src_for(main_text, "value", 0),
            }
            function_text = (
                "function get() external view returns (uint256) { return value; }"
            )
            function_node = {
                "nodeType": "FunctionDefinition",
                "id": 203,
                "name": "get",
                "kind": "function",
                "src": src_for(main_text, function_text, 0),
                "body": {
                    "nodeType": "Block",
                    "id": 205,
                    "src": src_for(main_text, "{ return value; }", 0),
                    "statements": [value_reference],
                },
            }
            main_contract_text = (
                "contract Main is Dep { function get() external view returns (uint256) { "
                "return value; } }"
            )
            main_contract = {
                "nodeType": "ContractDefinition",
                "id": 200,
                "name": "Main",
                "contractKind": "contract",
                "src": src_for(main_text, main_contract_text, 0),
                "baseContracts": [
                    {
                        "nodeType": "InheritanceSpecifier",
                        "id": 202,
                        "src": src_for(main_text, "Dep", 0),
                        "baseName": inherited_reference,
                    }
                ],
                "nodes": [function_node],
            }
            main_ast = {
                "nodeType": "SourceUnit",
                "id": 2_000,
                "src": f"0:{len(main_text.encode('utf-8'))}:0",
                "nodes": [
                    {
                        "nodeType": "ImportDirective",
                        "id": 199,
                        "absolutePath": "lib/example/src/Dep.sol",
                        "src": src_for(
                            main_text, 'import {Dep} from "example/Dep.sol";', 0
                        ),
                    },
                    main_contract,
                ],
            }
            compilation = CompilationResult(
                sources=(
                    CompiledSource(
                        path=main_path.resolve(),
                        source_id=0,
                        compilation_id="build-a",
                        ast=main_ast,
                        content=main_text,
                    ),
                    CompiledSource(
                        path=dependency_path.resolve(),
                        source_id=1,
                        compilation_id="build-a",
                        ast=dependency_ast,
                        content=dependency_text,
                    ),
                ),
                compiler_versions=("0.8.25",),
                diagnostics=(),
            )

            index = ProjectIndex(compilation)

            self.assertEqual(index.source_for_id("build-a", 1).path, dependency_path)
            self.assertEqual(index.source_for_path(dependency_path).source_id, 1)
            self.assertIs(index.resolve_reference(inherited_reference), dependency_contract)
            self.assertIs(index.resolve_reference(value_reference), dependency_contract["nodes"][0])
            self.assertIn(NodeKey("build-a", 100), index.contracts_by_id)
            self.assertIn(NodeKey("build-a", 203), index.functions_by_id)
            self.assertIn(NodeKey("build-a", 101), index.declarations_by_id)
            self.assertIs(index.source_for_path(main_path).source.project_index, index)

            span = index.source_span(dependency_contract)
            self.assertIsNotNone(span)
            assert span is not None
            self.assertEqual(span.path, dependency_path.resolve())
            self.assertEqual((span.line, span.column), (2, 1))
            self.assertEqual(
                dependency_text[span.start : span.end],
                "contract Dep { uint256 value; }",
            )

    def test_node_ids_are_namespaced_by_compilation(self) -> None:
        first_node = {
            "nodeType": "ContractDefinition",
            "id": 10,
            "name": "First",
            "src": "0:17:0",
            "nodes": [],
        }
        second_node = {
            "nodeType": "ContractDefinition",
            "id": 10,
            "name": "Second",
            "src": "0:18:0",
            "nodes": [],
        }
        compilation = CompilationResult(
            sources=(
                CompiledSource(
                    Path("First.sol").resolve(),
                    0,
                    "build-a",
                    {"nodeType": "SourceUnit", "id": 1, "src": "0:17:0", "nodes": [first_node]},
                    "contract First {}",
                ),
                CompiledSource(
                    Path("Second.sol").resolve(),
                    0,
                    "build-b",
                    {"nodeType": "SourceUnit", "id": 1, "src": "0:18:0", "nodes": [second_node]},
                    "contract Second {}",
                ),
            ),
            compiler_versions=("0.8.20", "0.8.25"),
            diagnostics=(),
        )

        index = ProjectIndex(compilation)

        self.assertIs(index.nodes_by_id[NodeKey("build-a", 10)], first_node)
        self.assertIs(index.nodes_by_id[NodeKey("build-b", 10)], second_node)


if __name__ == "__main__":
    unittest.main()
