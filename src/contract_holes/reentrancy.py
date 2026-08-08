from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


INTERNAL_EDGE_KINDS = frozenset({"internal", "super", "library"})
NON_REENTRANT_MODIFIER = re.compile(
    r"(?:nonreentrant|reentrancy|mutex|lock)", re.IGNORECASE
)
GUARD_STATE_NAME = re.compile(
    r"(?:lock|reentran|mutex|status|entered)", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class TraceEvent:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    guarded: bool = False


@dataclass(frozen=True, slots=True)
class ReentrancyIssue:
    entry: NodeKey
    interaction: TraceEvent
    state_write: TraceEvent
    trace: tuple[TraceEvent, ...]


class ReentrancyAnalysis:
    """Compose call and flow facts into interaction-before-effect traces."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        self.guarded_functions = frozenset(
            key
            for key, function in project.functions_by_id.items()
            if self._has_reentrancy_guard(function)
        )
        issues: list[ReentrancyIssue] = []
        for entry, function in sorted(project.functions_by_id.items()):
            if not self._is_external_entry(function):
                continue
            trace = self.trace_from(entry)
            issues.extend(self._issues_for_trace(entry, trace))
        self.issues: tuple[ReentrancyIssue, ...] = tuple(
            sorted(issues, key=_issue_sort_key)
        )

    def trace_from(self, function: NodeKey | Node) -> tuple[TraceEvent, ...]:
        key = (
            function
            if isinstance(function, NodeKey)
            else self.project.key_for_node(function)
        )
        if key is None:
            return ()
        return tuple(self._unfold(key, frozenset(), False))

    def function_name(self, function: NodeKey | Node) -> str:
        node = (
            self.project.node_for_key(function)
            if isinstance(function, NodeKey)
            else function
        )
        if node is None:
            return "<unknown>"
        name = str(node.get("name") or node.get("kind") or "<anonymous>")
        contract = self.project.enclosing_node(node, "ContractDefinition")
        if contract is None:
            return name
        return f"{contract.get('name', '<contract>')}.{name}"

    def state_variable_name(self, event: TraceEvent) -> str:
        declaration = event.fact.declaration if event.fact is not None else None
        node = self.project.node_for_key(declaration) if declaration is not None else None
        if node is not None:
            return str(node.get("name") or "<state>")
        return "<state>"

    def event_dict(self, event: TraceEvent) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": event.kind,
            "function": self.function_name(event.function),
            "guarded": event.guarded,
            "path": str(event.span.path) if event.span is not None else None,
            "line": event.span.line if event.span is not None else None,
            "column": event.span.column if event.span is not None else None,
        }
        if event.edge is not None:
            result.update(
                {
                    "callee": (
                        self.function_name(event.edge.callee)
                        if event.edge.callee is not None
                        else None
                    ),
                    "call_kind": event.edge.kind,
                    "target": event.edge.target,
                }
            )
        if event.fact is not None:
            if event.kind == "interaction":
                result.update(
                    {
                        "call_kind": event.fact.metadata.get("edge_kind"),
                        "target": event.fact.metadata.get("target"),
                    }
                )
            elif event.kind == "write":
                result["state_variable"] = self.state_variable_name(event)
        return result

    def _unfold(
        self, function: NodeKey, stack: frozenset[NodeKey], inherited_guard: bool
    ) -> list[TraceEvent]:
        if function in stack:
            return []
        guarded = inherited_guard or function in self.guarded_functions
        local_events: list[TraceEvent] = []
        for fact in self.project.data_flow.facts_for(function=function):
            kind = self._fact_event_kind(fact)
            if kind is not None:
                local_events.append(
                    TraceEvent(kind, function, fact.span, fact=fact, guarded=guarded)
                )
        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in INTERNAL_EDGE_KINDS
            ):
                continue
            local_events.append(
                TraceEvent("call", function, edge.span, edge=edge, guarded=guarded)
            )
        function_node = self.project.node_for_key(function)
        execution_order = (
            _execution_order(self.project, function_node)
            if function_node is not None
            else {}
        )
        local_events.sort(key=lambda event: _event_sort_key(event, execution_order))

        result: list[TraceEvent] = []
        next_stack = stack | {function}
        for event in local_events:
            result.append(event)
            if event.edge is not None and event.edge.callee not in next_stack:
                result.extend(self._unfold(event.edge.callee, next_stack, guarded))
        return result

    def _issues_for_trace(
        self, entry: NodeKey, trace: tuple[TraceEvent, ...]
    ) -> list[ReentrancyIssue]:
        issues: list[ReentrancyIssue] = []
        for interaction_index, interaction in enumerate(trace):
            if interaction.kind != "interaction" or interaction.guarded:
                continue
            if self._manually_guarded(trace, interaction_index):
                continue
            for write_index in range(interaction_index + 1, len(trace)):
                write = trace[write_index]
                if write.kind != "write" or self._is_guard_write(write):
                    continue
                issues.append(
                    ReentrancyIssue(
                        entry=entry,
                        interaction=interaction,
                        state_write=write,
                        trace=trace[: write_index + 1],
                    )
                )
                break
        return issues

    def _manually_guarded(
        self, trace: tuple[TraceEvent, ...], interaction_index: int
    ) -> bool:
        before = {
            event.fact.declaration
            for event in trace[:interaction_index]
            if self._is_guard_write(event) and event.fact is not None
        }
        if not before:
            return False
        after = {
            event.fact.declaration
            for event in trace[interaction_index + 1 :]
            if self._is_guard_write(event) and event.fact is not None
        }
        return bool(before & after)

    def _is_guard_write(self, event: TraceEvent) -> bool:
        if event.kind != "write" or event.fact is None:
            return False
        declaration = event.fact.declaration
        node = self.project.node_for_key(declaration) if declaration is not None else None
        return bool(node is not None and GUARD_STATE_NAME.search(str(node.get("name", ""))))

    @staticmethod
    def _fact_event_kind(fact: FlowFact) -> str | None:
        if fact.kind == "external-interaction":
            if fact.metadata.get("edge_kind") == "low-level-staticcall":
                return None
            return "interaction"
        if fact.kind == "write" and fact.metadata.get("scope") == "state":
            return "write"
        return None

    @staticmethod
    def _is_external_entry(function: Node) -> bool:
        return bool(
            function.get("nodeType") == "FunctionDefinition"
            and function.get("visibility") in {"public", "external"}
            and function.get("kind") != "constructor"
            and isinstance(function.get("body"), dict)
        )

    def _has_reentrancy_guard(self, function: Node) -> bool:
        modifiers = function.get("modifiers", [])
        if not isinstance(modifiers, list):
            return False
        for invocation in modifiers:
            if not isinstance(invocation, dict):
                continue
            name_node = invocation.get("modifierName")
            invocation_name = (
                str(name_node.get("name") or name_node.get("namePath") or "")
                if isinstance(name_node, dict)
                else ""
            )
            if NON_REENTRANT_MODIFIER.search(invocation_name):
                return True
            resolution = (
                self.project.resolve_reference_detail(name_node)
                if isinstance(name_node, dict)
                else None
            )
            modifier = resolution.node if resolution is not None else None
            if modifier is not None and (
                NON_REENTRANT_MODIFIER.search(str(modifier.get("name", "")))
                or self._modifier_wraps_with_guard_state(modifier)
            ):
                return True
        return False

    def _modifier_wraps_with_guard_state(self, modifier: Node) -> bool:
        key = self.project.key_for_node(modifier)
        body = modifier.get("body")
        if key is None or not isinstance(body, dict):
            return False
        placeholder = next(
            (
                node
                for node in _walk_ast(body)
                if node.get("nodeType") == "PlaceholderStatement"
            ),
            None,
        )
        placeholder_span = self.project.source_span(placeholder) if placeholder else None
        if placeholder_span is None:
            return False
        before: set[NodeKey] = set()
        after: set[NodeKey] = set()
        for fact in self.project.data_flow.facts_for(function=key, kind="write"):
            if fact.metadata.get("scope") != "state" or fact.declaration is None:
                continue
            declaration = self.project.node_for_key(fact.declaration)
            if declaration is None or not GUARD_STATE_NAME.search(
                str(declaration.get("name", ""))
            ):
                continue
            if fact.span is not None and fact.span.byte_start < placeholder_span.byte_start:
                before.add(fact.declaration)
            elif fact.span is not None:
                after.add(fact.declaration)
        return bool(before & after)


def _walk_ast(node: Node):
    yield node
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            yield from _walk_ast(value)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict) and "nodeType" in child:
                    yield from _walk_ast(child)


def _event_sort_key(
    event: TraceEvent, execution_order: dict[NodeKey, int]
) -> tuple[int, int, int, str]:
    byte_start = event.span.byte_start if event.span is not None else -1
    key = _event_node(event)
    node_id = key.node_id if key is not None else -1
    ordinal = execution_order.get(key, 1_000_000 + max(byte_start, 0))
    return ordinal, byte_start, node_id, event.kind


def _event_node(event: TraceEvent) -> NodeKey | None:
    if event.fact is not None:
        return event.fact.node
    if event.edge is not None:
        return event.edge.call_site
    return None


def _execution_order(project: "ProjectIndex", function: Node) -> dict[NodeKey, int]:
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

    body = function.get("body")
    if isinstance(body, dict):
        visit(body)
    return result


def _issue_sort_key(issue: ReentrancyIssue) -> tuple[str, int, int, int]:
    interaction_start = (
        issue.interaction.span.byte_start if issue.interaction.span is not None else -1
    )
    write_start = (
        issue.state_write.span.byte_start if issue.state_write.span is not None else -1
    )
    return (
        issue.entry.compilation_id,
        issue.entry.node_id,
        interaction_start,
        write_start,
    )
