from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact
from .execution import execution_order
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


FOLLOW_EDGE_KINDS = frozenset({"internal", "super", "library", "modifier"})
SPOT_MEMBERS = frozenset({"getReserves", "slot0"})
TWAP_MEMBERS = frozenset({"consult", "observe", "getTwap", "twap"})
SWAP_ARGUMENTS = {
    "swapExactTokensForTokens": (1, 4),
    "swapExactTokensForETH": (1, 4),
    "swapExactETHForTokens": (0, 3),
    "swapTokensForExactTokens": (0, 4),
}
FRESHNESS_NAME = re.compile(
    r"(?:updatedat|updated_at|heartbeat|maxage|max_age|stale|fresh|age)",
    re.IGNORECASE,
)
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


@dataclass(frozen=True, slots=True)
class MarketTraceEvent:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    label: str
    node: NodeKey | None = None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    origins: frozenset[NodeKey] = frozenset()
    guaranteed: bool = True
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketIssue:
    kind: str
    entry: NodeKey
    source: MarketTraceEvent
    action: MarketTraceEvent
    hazards: tuple[str, ...]
    trace: tuple[MarketTraceEvent, ...]


class MarketAnalysis:
    """Trace oracle/spot values to actions and inspect swap protections."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        issues: dict[
            tuple[str, NodeKey, NodeKey | None, NodeKey | None], MarketIssue
        ] = {}
        for entry, function in sorted(project.functions_by_id.items()):
            if not self._is_external_entry(function):
                continue
            trace = self.trace_from(entry)
            for index, event in enumerate(trace):
                if event.kind == "swap":
                    hazards = tuple(event.metadata.get("hazards", ()))
                    if hazards:
                        issue = MarketIssue(
                            "swap-protection",
                            entry,
                            event,
                            event,
                            hazards,
                            trace[: index + 1],
                        )
                        issues.setdefault(
                            (issue.kind, entry, event.node, event.node), issue
                        )
                    continue
                if event.kind not in {"oracle-read", "spot-read"}:
                    continue
                action_index = next(
                    (
                        candidate
                        for candidate in range(index + 1, len(trace))
                        if trace[candidate].kind == "action"
                        and bool(trace[candidate].origins & event.origins)
                    ),
                    None,
                )
                if action_index is None:
                    continue
                action = trace[action_index]
                prefix = trace[: action_index + 1]
                if event.kind == "oracle-read":
                    protected = any(
                        candidate.kind == "freshness-check"
                        and candidate.guaranteed
                        and candidate_index > index
                        for candidate_index, candidate in enumerate(prefix)
                    )
                    if protected:
                        continue
                    kind = "stale-oracle"
                    hazards = ("missing-freshness-check",)
                else:
                    protected = any(
                        candidate.kind == "twap-read"
                        and candidate_index <= action_index
                        for candidate_index, candidate in enumerate(prefix)
                    )
                    if protected:
                        continue
                    kind = "spot-price"
                    hazards = ("manipulable-spot-price",)
                issue = MarketIssue(
                    kind, entry, event, action, hazards, prefix
                )
                issues.setdefault(
                    (kind, entry, event.node, action.node), issue
                )
        self.issues: tuple[MarketIssue, ...] = tuple(
            sorted(issues.values(), key=_issue_sort_key)
        )

    def trace_from(self, function: NodeKey | Node) -> tuple[MarketTraceEvent, ...]:
        key = (
            function
            if isinstance(function, NodeKey)
            else self.project.key_for_node(function)
        )
        if key is None:
            return ()
        node = self.project.node_for_key(key)
        span = self.project.source_span(node) if node is not None else None
        entry = MarketTraceEvent(
            "entry", key, span, self.function_name(key), node=key
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
        return f"{contract.get('name')}.{name}" if contract is not None else name

    def event_dict(self, event: MarketTraceEvent) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": event.kind,
            "function": self.function_name(event.function),
            "label": event.label,
            "origins": sorted(_key_text(origin) for origin in event.origins),
            "guaranteed": event.guaranteed,
            "path": str(event.span.path) if event.span is not None else None,
            "line": event.span.line if event.span is not None else None,
            "column": event.span.column if event.span is not None else None,
            **event.metadata,
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
        if event.fact is not None and event.kind == "action":
            result["action_kind"] = (
                "state-write" if event.fact.kind == "write" else "external-interaction"
            )
            if event.fact.kind == "write":
                result["state_variable"] = event.fact.metadata.get("name", "<state>")
        return result

    def _unfold(
        self,
        function: NodeKey,
        stack: frozenset[NodeKey],
        inherited_guarantee: bool,
    ) -> list[MarketTraceEvent]:
        if function in stack:
            return []
        function_node = self.project.node_for_key(function)
        if function_node is None:
            return []
        events: list[MarketTraceEvent] = []
        for fact in self.project.data_flow.facts_for(function=function):
            event = self._fact_event(function, fact, inherited_guarantee)
            if event is not None:
                events.append(event)
        events.extend(
            self._freshness_events(function, function_node, inherited_guarantee)
        )
        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in FOLLOW_EDGE_KINDS
            ):
                continue
            events.append(
                MarketTraceEvent(
                    "call",
                    function,
                    edge.span,
                    edge.target,
                    node=edge.call_site,
                    edge=edge,
                    guaranteed=(
                        inherited_guarantee and self._is_unconditional(edge.call_site)
                    ),
                )
            )
        order = execution_order(self.project, function_node)
        events.sort(key=lambda event: _event_sort_key(event, order))

        result: list[MarketTraceEvent] = []
        next_stack = stack | {function}
        for event in events:
            result.append(event)
            if event.edge is not None and event.edge.callee not in next_stack:
                result.extend(
                    self._unfold(event.edge.callee, next_stack, event.guaranteed)
                )
        return result

    def _fact_event(
        self, function: NodeKey, fact: FlowFact, inherited_guarantee: bool
    ) -> MarketTraceEvent | None:
        guaranteed = inherited_guarantee and self._is_unconditional(fact.node)
        if fact.kind == "write" and fact.metadata.get("scope") == "state":
            return MarketTraceEvent(
                "action",
                function,
                fact.span,
                str(fact.metadata.get("name") or "<state>"),
                node=fact.node,
                fact=fact,
                origins=fact.value.origins,
                guaranteed=guaranteed,
            )
        if fact.kind != "external-interaction" or fact.node is None:
            return None
        call = self.project.node_for_key(fact.node)
        member = _call_member(call)
        if member == "latestRoundData":
            return MarketTraceEvent(
                "oracle-read",
                function,
                fact.span,
                member,
                node=fact.node,
                fact=fact,
                origins=frozenset({fact.node}),
                guaranteed=guaranteed,
            )
        if member in SPOT_MEMBERS:
            return MarketTraceEvent(
                "spot-read",
                function,
                fact.span,
                member,
                node=fact.node,
                fact=fact,
                origins=frozenset({fact.node}),
                guaranteed=guaranteed,
            )
        if member in TWAP_MEMBERS:
            return MarketTraceEvent(
                "twap-read",
                function,
                fact.span,
                member,
                node=fact.node,
                fact=fact,
                origins=frozenset({fact.node}),
                guaranteed=guaranteed,
            )
        if member in SWAP_ARGUMENTS:
            hazards = self._swap_hazards(call, member)
            return MarketTraceEvent(
                "swap",
                function,
                fact.span,
                member,
                node=fact.node,
                fact=fact,
                guaranteed=guaranteed,
                metadata={"hazards": list(hazards)},
            )
        return MarketTraceEvent(
            "action",
            function,
            fact.span,
            member or str(fact.metadata.get("target", "external interaction")),
            node=fact.node,
            fact=fact,
            origins=fact.value.origins,
            guaranteed=guaranteed,
        )

    def _freshness_events(
        self,
        function: NodeKey,
        function_node: Node,
        inherited_guarantee: bool,
    ) -> list[MarketTraceEvent]:
        body = function_node.get("body")
        if not isinstance(body, dict):
            return []
        result: list[MarketTraceEvent] = []
        for call in _walk_ast(body):
            if call.get("nodeType") != "FunctionCall" or _call_name(call) not in {
                "require",
                "assert",
            }:
                continue
            arguments = call.get("arguments", [])
            condition = (
                arguments[0]
                if isinstance(arguments, list) and arguments
                else None
            )
            if not isinstance(condition, dict):
                continue
            if not _contains_timestamp(condition) or not _contains_freshness_name(
                condition
            ):
                continue
            span = self.project.source_span(condition)
            key = self.project.key_for_node(condition)
            result.append(
                MarketTraceEvent(
                    "freshness-check",
                    function,
                    span,
                    "oracle timestamp bound",
                    node=key,
                    guaranteed=inherited_guarantee and self._is_unconditional(key),
                )
            )
        return result

    def _swap_hazards(self, call: Node | None, member: str) -> tuple[str, ...]:
        if call is None:
            return ()
        arguments = call.get("arguments", [])
        if not isinstance(arguments, list):
            return ()
        min_index, deadline_index = SWAP_ARGUMENTS[member]
        hazards: list[str] = []
        if min_index >= len(arguments) or _is_zero(arguments[min_index]):
            hazards.append("missing-minimum-output")
        if deadline_index >= len(arguments) or _is_current_timestamp(
            self.project, arguments[deadline_index]
        ):
            hazards.append("ineffective-deadline")
        return tuple(hazards)

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

    @staticmethod
    def _is_external_entry(function: Node) -> bool:
        return bool(
            function.get("nodeType") == "FunctionDefinition"
            and function.get("visibility") in {"public", "external"}
            and function.get("kind") != "constructor"
            and isinstance(function.get("body"), dict)
        )


def _call_member(call: Node | None) -> str:
    if call is None:
        return ""
    expression = call.get("expression")
    while (
        isinstance(expression, dict)
        and expression.get("nodeType") == "FunctionCallOptions"
    ):
        expression = expression.get("expression")
    return (
        str(expression.get("memberName", ""))
        if isinstance(expression, dict) and expression.get("nodeType") == "MemberAccess"
        else ""
    )


def _call_name(call: Node) -> str:
    expression = call.get("expression")
    return str(expression.get("name", "")) if isinstance(expression, dict) else ""


def _contains_timestamp(node: Node) -> bool:
    return any(
        candidate.get("nodeType") == "MemberAccess"
        and candidate.get("memberName") == "timestamp"
        and isinstance((owner := candidate.get("expression")), dict)
        and owner.get("name") == "block"
        for candidate in _walk_ast(node)
    )


def _contains_freshness_name(node: Node) -> bool:
    return any(
        FRESHNESS_NAME.search(
            str(candidate.get("name") or candidate.get("memberName") or "")
        )
        for candidate in _walk_ast(node)
    )


def _is_zero(node: object) -> bool:
    return bool(
        isinstance(node, dict)
        and node.get("nodeType") == "Literal"
        and str(node.get("value", "")) == "0"
    )


def _is_current_timestamp(project: "ProjectIndex", node: object) -> bool:
    if not isinstance(node, dict):
        return True
    span = project.source_span(node)
    if span is None:
        return False
    source = project.source_for_id(span.compilation_id, span.source_id)
    if source is None:
        return False
    text = re.sub(r"\s+", "", source.source.text[span.start : span.end])
    return text in {"block.timestamp", "now"} or _is_zero(node)


def _walk_ast(node: Node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        children: list[Node] = []
        for value in current.values():
            if isinstance(value, dict) and "nodeType" in value:
                children.append(value)
            elif isinstance(value, list):
                children.extend(
                    child
                    for child in value
                    if isinstance(child, dict) and "nodeType" in child
                )
        for child in reversed(children):
            stack.append(child)


def _event_sort_key(
    event: MarketTraceEvent, order: dict[NodeKey, int]
) -> tuple[int, int, int, str]:
    byte_start = event.span.byte_start if event.span is not None else -1
    node_id = event.node.node_id if event.node is not None else -1
    ordinal = order.get(event.node, 1_000_000 + max(byte_start, 0))
    return ordinal, byte_start, node_id, event.kind


def _issue_sort_key(issue: MarketIssue) -> tuple[str, int, int, str]:
    start = issue.source.span.byte_start if issue.source.span is not None else -1
    return issue.entry.compilation_id, issue.entry.node_id, start, issue.kind


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"
