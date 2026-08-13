from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact
from .execution import execution_order
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


FOLLOW_EDGE_KINDS = frozenset({"internal", "super", "library", "modifier"})
CONDITIONAL_NODE_TYPES = frozenset(
    {
        "Conditional",
        "DoWhileStatement",
        "ForStatement",
        "IfStatement",
        "TryCatchClause",
        "TryStatement",
        "WhileStatement",
    }
)
PRIVILEGED_STATE_NAME = re.compile(
    r"(?:"
    r"owner|admin|implementation|beacon|guardian|operator|pauser|paused|"
    r"minter|upgrader|treasury|authority|whitelist|allowlist|role|"
    r"protocolfee|feerecipient|feecollector|feeadmin|feerate|feecontroller|"
    r"(?:^|_)(?:fee|fees)(?:_|$)"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class AuthorizationTraceEvent:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    guaranteed: bool = True
    label: str = ""

    @property
    def protective(self) -> bool:
        return self.kind == "authorization" and self.guaranteed


@dataclass(frozen=True, slots=True)
class AuthorizationIssue:
    entry: NodeKey
    state_write: AuthorizationTraceEvent
    trace: tuple[AuthorizationTraceEvent, ...]


class AuthorizationAnalysis:
    """Find externally reachable privileged writes without dominating authorization."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        self.sensitive_writes: tuple[FlowFact, ...] = tuple(
            fact
            for fact in project.data_flow.facts_for(kind="write")
            if self._is_sensitive_write(fact)
        )
        self._sensitive_nodes = frozenset(
            fact.node for fact in self.sensitive_writes if fact.node is not None
        )

        issues: dict[tuple[NodeKey, NodeKey | None, NodeKey | None], AuthorizationIssue] = {}
        for entry, function in sorted(project.functions_by_id.items()):
            if not self._is_external_entry(function):
                continue
            trace = self.trace_from(entry)
            for index, event in enumerate(trace):
                if event.kind != "write":
                    continue
                if any(candidate.protective for candidate in trace[:index]):
                    continue
                issue = AuthorizationIssue(entry, event, trace[: index + 1])
                declaration = event.fact.declaration if event.fact is not None else None
                node = event.fact.node if event.fact is not None else None
                issues.setdefault((entry, declaration, node), issue)
        self.issues: tuple[AuthorizationIssue, ...] = tuple(
            sorted(issues.values(), key=_issue_sort_key)
        )

    def trace_from(
        self, function: NodeKey | Node
    ) -> tuple[AuthorizationTraceEvent, ...]:
        key = (
            function
            if isinstance(function, NodeKey)
            else self.project.key_for_node(function)
        )
        if key is None:
            return ()
        node = self.project.node_for_key(key)
        span = self.project.source_span(node) if node is not None else None
        entry = AuthorizationTraceEvent(
            "entry", key, span, label=self.function_name(key)
        )
        return (entry, *self._unfold(key, frozenset(), True))

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

    def state_variable_name(self, event: AuthorizationTraceEvent) -> str:
        declaration = event.fact.declaration if event.fact is not None else None
        node = self.project.node_for_key(declaration) if declaration is not None else None
        return str(node.get("name") or "<state>") if node is not None else "<state>"

    def event_dict(self, event: AuthorizationTraceEvent) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": event.kind,
            "function": self.function_name(event.function),
            "label": event.label,
            "guaranteed": event.guaranteed,
            "protective": event.protective,
            "path": str(event.span.path) if event.span is not None else None,
            "line": event.span.line if event.span is not None else None,
            "column": event.span.column if event.span is not None else None,
        }
        if event.edge is not None:
            result.update(
                {
                    "call_kind": event.edge.kind,
                    "callee": (
                        self.function_name(event.edge.callee)
                        if event.edge.callee is not None
                        else None
                    ),
                }
            )
        if event.fact is not None and event.kind == "authorization":
            result["mechanisms"] = event.fact.metadata.get("mechanisms", [])
            result["context"] = event.fact.metadata.get("context", "modifier")
        elif event.fact is not None and event.kind == "write":
            result["state_variable"] = self.state_variable_name(event)
        return result

    def _unfold(
        self,
        function: NodeKey,
        stack: frozenset[NodeKey],
        inherited_guarantee: bool,
    ) -> list[AuthorizationTraceEvent]:
        if function in stack:
            return []
        function_node = self.project.node_for_key(function)
        if function_node is None:
            return []
        byte_limit = self._modifier_placeholder_start(function_node)
        local_events: list[AuthorizationTraceEvent] = []
        for fact in self.project.data_flow.facts_for(function=function):
            if byte_limit is not None and not _before_limit(fact.span, byte_limit):
                continue
            if fact.kind == "authorization" and fact.metadata.get("context") != "if":
                guaranteed = inherited_guarantee and self._is_unconditional(fact.node)
                local_events.append(
                    AuthorizationTraceEvent(
                        "authorization",
                        function,
                        fact.span,
                        fact=fact,
                        guaranteed=guaranteed,
                        label=", ".join(
                            str(value)
                            for value in fact.metadata.get("mechanisms", [])
                        ),
                    )
                )
            elif fact.kind == "write" and fact.node in self._sensitive_nodes:
                local_events.append(
                    AuthorizationTraceEvent(
                        "write",
                        function,
                        fact.span,
                        fact=fact,
                        guaranteed=inherited_guarantee and self._is_unconditional(fact.node),
                        label=str(fact.metadata.get("name") or "<state>"),
                    )
                )
        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in FOLLOW_EDGE_KINDS
                or (byte_limit is not None and not _before_limit(edge.span, byte_limit))
            ):
                continue
            guaranteed = inherited_guarantee and self._is_unconditional(edge.call_site)
            local_events.append(
                AuthorizationTraceEvent(
                    "call",
                    function,
                    edge.span,
                    edge=edge,
                    guaranteed=guaranteed,
                    label=edge.target,
                )
            )

        order = execution_order(self.project, function_node)
        local_events.sort(key=lambda event: _event_sort_key(event, order))
        result: list[AuthorizationTraceEvent] = []
        next_stack = stack | {function}
        for event in local_events:
            result.append(event)
            if event.edge is not None and event.edge.callee not in next_stack:
                result.extend(
                    self._unfold(event.edge.callee, next_stack, event.guaranteed)
                )
        return result

    def _is_sensitive_write(self, fact: FlowFact) -> bool:
        if fact.metadata.get("scope") != "state" or fact.declaration is None:
            return False
        declaration = self.project.node_for_key(fact.declaration)
        if declaration is None:
            return False
        return bool(PRIVILEGED_STATE_NAME.search(str(declaration.get("name", ""))))

    def _is_unconditional(self, key: NodeKey | None) -> bool:
        node = self.project.node_for_key(key) if key is not None else None
        current = self.project.parent(node) if node is not None else None
        while current is not None:
            node_type = str(current.get("nodeType", ""))
            if node_type in CONDITIONAL_NODE_TYPES:
                return False
            if node_type in {"FunctionDefinition", "ModifierDefinition"}:
                break
            current = self.project.parent(current)
        return True

    def _modifier_placeholder_start(self, function: Node) -> int | None:
        if function.get("nodeType") != "ModifierDefinition":
            return None
        body = function.get("body")
        if not isinstance(body, dict):
            return None
        starts = [
            span.byte_start
            for node in _walk_ast(body)
            if node.get("nodeType") == "PlaceholderStatement"
            and (span := self.project.source_span(node)) is not None
        ]
        return min(starts) if starts else None

    @staticmethod
    def _is_external_entry(function: Node) -> bool:
        return bool(
            function.get("nodeType") == "FunctionDefinition"
            and function.get("visibility") in {"public", "external"}
            and function.get("kind") != "constructor"
            and isinstance(function.get("body"), dict)
        )


def _before_limit(span: SourceSpan | None, byte_limit: int) -> bool:
    return span is not None and span.byte_start < byte_limit


def _event_sort_key(
    event: AuthorizationTraceEvent, order: dict[NodeKey, int]
) -> tuple[int, int, int, str]:
    byte_start = event.span.byte_start if event.span is not None else -1
    node = event.fact.node if event.fact is not None else (
        event.edge.call_site if event.edge is not None else None
    )
    node_id = node.node_id if node is not None else -1
    ordinal = order.get(node, 1_000_000 + max(byte_start, 0))
    return ordinal, byte_start, node_id, event.kind


def _walk_ast(node: Node):
    yield node
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            yield from _walk_ast(value)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict) and "nodeType" in child:
                    yield from _walk_ast(child)


def _issue_sort_key(issue: AuthorizationIssue) -> tuple[str, int, int, int]:
    write_start = (
        issue.state_write.span.byte_start if issue.state_write.span is not None else -1
    )
    declaration = (
        issue.state_write.fact.declaration
        if issue.state_write.fact is not None
        else None
    )
    declaration_id = declaration.node_id if declaration is not None else -1
    return (
        issue.entry.compilation_id,
        issue.entry.node_id,
        write_start,
        declaration_id,
    )
