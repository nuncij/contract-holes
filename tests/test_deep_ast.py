"""Regression tests for iterative deep-AST traversal.

Real-world contracts (for example large vault and lending protocols) can
produce deeply nested compiler ASTs. The previous recursive AST walkers hit
Python's recursion limit and crashed analysis. These tests exercise the shared
walkers with a synthetic AST deep enough to exceed the default recursion limit,
and confirm a deep Solidity source compiles and analyzes through the scanner.
"""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes import authorization, callgraph, dataflow, market, proxy
from contract_holes import reentrancy, rules, signature
from contract_holes.compiler import ForgeCompiler
from contract_holes.project import ProjectIndex
from contract_holes.scanner import discover_sources


def _deep_node(depth: int) -> dict:
    node: dict = {"nodeType": "Literal", "src": "0:1:0"}
    for _ in range(depth):
        node = {
            "nodeType": "BinaryOperation",
            "src": "0:1:0",
            "leftExpression": node,
            "rightExpression": {"nodeType": "Literal", "src": "0:1:0"},
        }
    return {"nodeType": "ExpressionStatement", "src": "0:1:0", "expression": node}


class DeepAstTraversalTests(unittest.TestCase):
    def test_module_walkers_traverse_deep_ast_iteratively(self) -> None:
        deep = _deep_node(5000)
        walkers = [
            authorization._walk_ast,
            callgraph._walk_ast,
            dataflow._walk_ast,
            market._walk_ast,
            proxy._walk_ast,
            reentrancy._walk_ast,
            signature._walk_ast,
        ]
        for walker in walkers:
            collected = list(walker(deep))
            self.assertGreater(len(collected), 5000)
            self.assertEqual(collected[0]["nodeType"], "ExpressionStatement")

    def test_rules_walker_traverses_deep_ast_with_parents(self) -> None:
        deep = _deep_node(5000)
        collected = list(rules._walk_ast(deep))
        self.assertGreater(len(collected), 5000)
        first, parent = collected[0]
        self.assertEqual(first["nodeType"], "ExpressionStatement")
        self.assertIsNone(parent)
        child, child_parent = collected[-1]
        self.assertEqual(child["nodeType"], "Literal")
        self.assertEqual(child_parent["nodeType"], "BinaryOperation")

    def test_deep_solidity_source_compiles_and_indexes(self) -> None:
        if shutil.which("forge") is None:
            self.skipTest("Foundry is required for compiler-backed scans")
        depth = 20
        expression = "uint256(1)"
        for _ in range(depth):
            expression = f"keccak256(abi.encode({expression}))"
        source_text = (
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.20;\n"
            "contract DeepNest {\n"
            "    function f() external pure returns (bytes32) {\n"
            f"        return {expression};\n"
            "    }\n"
            "}\n"
        )
        root = Path(tempfile.mkdtemp(prefix="holes-deep-ast-regression-"))
        (root / "DeepNest.sol").write_text(source_text, encoding="utf-8")
        try:
            files = discover_sources([root])
            compilation = ForgeCompiler().compile(files, project_root=root, offline=True)
            index = ProjectIndex(compilation)
            self.assertEqual(len(index.sources), 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
