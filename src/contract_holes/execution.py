from __future__ import annotations

from typing import TYPE_CHECKING

from .project import Node, NodeKey

if TYPE_CHECKING:
    from .project import ProjectIndex


def execution_order(project: "ProjectIndex", function: Node) -> dict[NodeKey, int]:
    """Return a conservative runtime order for relevant expression nodes."""

    result: dict[NodeKey, int] = {}
    ordinal = 0

    def record(node: Node) -> None:
        nonlocal ordinal
        key = project.key_for_node(node)
        if key is not None and key not in result:
            result[key] = ordinal
            ordinal += 1

    def visit(node: Node) -> None:
        node_type = node.get("nodeType")
        if node_type in {"Block", "UncheckedBlock"}:
            visit_list(node.get("statements"))
        elif node_type == "ExpressionStatement":
            visit_field(node, "expression")
        elif node_type == "VariableDeclarationStatement":
            visit_field(node, "initialValue")
        elif node_type == "Assignment":
            visit_field(node, "rightHandSide")
            visit_field(node, "leftHandSide")
        elif node_type == "UnaryOperation":
            visit_field(node, "subExpression")
        elif node_type == "FunctionCall":
            visit_field(node, "expression")
            visit_list(node.get("arguments"))
        elif node_type == "FunctionCallOptions":
            visit_field(node, "expression")
            visit_list(node.get("options"))
        elif node_type in {"IndexAccess", "IndexRangeAccess"}:
            for field in (
                "baseExpression",
                "indexExpression",
                "startExpression",
                "endExpression",
            ):
                visit_field(node, field)
        elif node_type in {"BinaryOperation", "Conditional"}:
            for field in (
                "leftExpression",
                "condition",
                "trueExpression",
                "falseExpression",
                "rightExpression",
            ):
                visit_field(node, field)
        elif node_type == "TupleExpression":
            visit_list(node.get("components"))
        elif node_type == "IfStatement":
            for field in ("condition", "trueBody", "falseBody"):
                visit_field(node, field)
        elif node_type in {"WhileStatement", "DoWhileStatement"}:
            visit_field(node, "condition")
            visit_field(node, "body")
        elif node_type == "ForStatement":
            for field in (
                "initializationExpression",
                "condition",
                "body",
                "loopExpression",
            ):
                visit_field(node, field)
        elif node_type in {"Return", "EmitStatement", "RevertStatement"}:
            for field in ("expression", "eventCall", "errorCall"):
                visit_field(node, field)
        elif node_type == "TryStatement":
            visit_field(node, "externalCall")
            visit_list(node.get("clauses"))
        else:
            children: list[Node] = []
            for value in node.values():
                if isinstance(value, dict) and "nodeType" in value:
                    children.append(value)
                elif isinstance(value, list):
                    children.extend(
                        child
                        for child in value
                        if isinstance(child, dict) and "nodeType" in child
                    )
            children.sort(
                key=lambda child: (
                    project.source_span(child).byte_start
                    if project.source_span(child) is not None
                    else -1
                )
            )
            for child in children:
                visit(child)
        record(node)

    def visit_field(node: Node, field: str) -> None:
        child = node.get(field)
        if isinstance(child, dict):
            visit(child)

    def visit_list(value: object) -> None:
        if not isinstance(value, list):
            return
        for child in value:
            if isinstance(child, dict):
                visit(child)

    visit_list(function.get("modifiers"))
    body = function.get("body")
    if isinstance(body, dict):
        visit(body)
    return result
