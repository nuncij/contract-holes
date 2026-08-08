from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact, FlowValue
from .execution import execution_order
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


FOLLOW_EDGE_KINDS = frozenset({"internal", "super", "library", "modifier"})
TOKEN_CONTRACT_NAME = re.compile(r"(?:erc20|token)", re.IGNORECASE)
RETURN_VALUE_MEMBERS = frozenset({"approve", "transfer", "transferFrom"})


@dataclass(frozen=True, slots=True)
class TokenTraceEvent:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    label: str
    node: NodeKey | None = None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    origins: frozenset[NodeKey] = frozenset()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TokenIssue:
    kind: str
    entry: NodeKey
    token_call: TokenTraceEvent
    state_write: TokenTraceEvent | None
    trace: tuple[TokenTraceEvent, ...]


class TokenAnalysis:
    """Trace ERC-20 calls to ignored results and nominal-amount accounting."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        self._edges_by_site = {
            edge.call_site: edge
            for edge in project.call_graph.edges
            if edge.call_site is not None
        }
        issues: dict[
            tuple[str, NodeKey, NodeKey | None, NodeKey | None], TokenIssue
        ] = {}
        for entry, function in sorted(project.functions_by_id.items()):
            if not self._is_external_entry(function):
                continue
            trace = self.trace_from(entry)
            for index, event in enumerate(trace):
                if event.kind != "token-call":
                    continue
                if (
                    event.metadata.get("bool_return") is True
                    and event.metadata.get("result_ignored") is True
                ):
                    issue = TokenIssue(
                        "ignored-return", entry, event, None, trace[: index + 1]
                    )
                    issues.setdefault(
                        (issue.kind, entry, event.node, None), issue
                    )
                if (
                    event.metadata.get("member") == "transferFrom"
                    and event.metadata.get("inbound") is True
                    and event.origins
                ):
                    write_index = next(
                        (
                            candidate
                            for candidate in range(index + 1, len(trace))
                            if trace[candidate].kind == "state-write"
                            and bool(trace[candidate].origins & event.origins)
                        ),
                        None,
                    )
                    if write_index is not None:
                        write = trace[write_index]
                        issue = TokenIssue(
                            "nominal-amount-accounting",
                            entry,
                            event,
                            write,
                            trace[: write_index + 1],
                        )
                        issues.setdefault(
                            (issue.kind, entry, event.node, write.node), issue
                        )
        self.issues: tuple[TokenIssue, ...] = tuple(
            sorted(issues.values(), key=_issue_sort_key)
        )

    def trace_from(self, function: NodeKey | Node) -> tuple[TokenTraceEvent, ...]:
        key = (
            function
            if isinstance(function, NodeKey)
            else self.project.key_for_node(function)
        )
        if key is None:
            return ()
        node = self.project.node_for_key(key)
        span = self.project.source_span(node) if node is not None else None
        entry = TokenTraceEvent(
            "entry", key, span, self.function_name(key), node=key
        )
        return (entry, *self._unfold(key, frozenset(), {}))

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

    def event_dict(self, event: TokenTraceEvent) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": event.kind,
            "function": self.function_name(event.function),
            "label": event.label,
            "origins": sorted(_key_text(origin) for origin in event.origins),
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
        if event.fact is not None and event.kind == "state-write":
            result["state_variable"] = event.fact.metadata.get("name", "<state>")
        return result

    def _unfold(
        self,
        function: NodeKey,
        stack: frozenset[NodeKey],
        origin_environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> list[TokenTraceEvent]:
        if function in stack:
            return []
        function_node = self.project.node_for_key(function)
        if function_node is None:
            return []
        local_events: list[TokenTraceEvent] = []
        for fact in self.project.data_flow.facts_for(function=function):
            event = self._fact_event(function, fact, origin_environment)
            if event is not None:
                local_events.append(event)
        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in FOLLOW_EDGE_KINDS
            ):
                continue
            local_events.append(
                TokenTraceEvent(
                    "call",
                    function,
                    edge.span,
                    edge.target,
                    node=edge.call_site,
                    edge=edge,
                )
            )
        order = execution_order(self.project, function_node)
        local_events.sort(key=lambda event: _event_sort_key(event, order))

        result: list[TokenTraceEvent] = []
        next_stack = stack | {function}
        for event in local_events:
            result.append(event)
            if event.edge is not None and event.edge.callee not in next_stack:
                result.extend(
                    self._unfold(
                        event.edge.callee,
                        next_stack,
                        self._callee_environment(
                            event.edge, origin_environment
                        ),
                    )
                )
        return result

    def _fact_event(
        self,
        function: NodeKey,
        fact: FlowFact,
        origin_environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> TokenTraceEvent | None:
        if fact.kind == "write" and fact.metadata.get("scope") == "state":
            return TokenTraceEvent(
                "state-write",
                function,
                fact.span,
                str(fact.metadata.get("name") or "<state>"),
                node=fact.node,
                fact=fact,
                origins=self._normalized_origins(fact.value, origin_environment),
            )
        if fact.kind != "external-interaction" or fact.node is None:
            return None
        call = self.project.node_for_key(fact.node)
        edge = self._edges_by_site.get(fact.node)
        info = self._token_call_info(call, edge)
        if info is None:
            return None
        member, bool_return = info
        arguments = call.get("arguments", []) if call is not None else []
        amount = (
            arguments[2]
            if member == "transferFrom"
            and isinstance(arguments, list)
            and len(arguments) >= 3
            and isinstance(arguments[2], dict)
            else None
        )
        amount_value = (
            self.project.data_flow.value_for_argument(amount)
            if amount is not None
            else None
        )
        recipient = (
            arguments[1]
            if member == "transferFrom"
            and isinstance(arguments, list)
            and len(arguments) >= 2
            and isinstance(arguments[1], dict)
            else None
        )
        return TokenTraceEvent(
            "token-call",
            function,
            fact.span,
            member,
            node=fact.node,
            fact=fact,
            origins=(
                self._normalized_origins(amount_value, origin_environment)
                if amount_value is not None
                else frozenset()
            ),
            metadata={
                "member": member,
                "bool_return": bool_return,
                "result_ignored": fact.metadata.get("result_ignored") is True,
                "inbound": bool(
                    recipient is not None and _is_address_this(self.project, recipient)
                ),
            },
        )

    def _token_call_info(
        self, call: Node | None, edge: CallEdge | None
    ) -> tuple[str, bool] | None:
        if call is None or edge is None:
            return None
        expression = call.get("expression")
        while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
            expression = expression.get("expression")
        if not isinstance(expression, dict) or expression.get("nodeType") != "MemberAccess":
            return None
        member = str(expression.get("memberName", ""))
        if member not in RETURN_VALUE_MEMBERS and member != "balanceOf":
            return None
        resolution = self.project.resolve_reference_detail(expression)
        callee = (
            self.project.node_for_key(edge.callee)
            if edge.callee is not None
            else resolution.node
        )
        contract = (
            self.project.enclosing_node(callee, "ContractDefinition")
            if callee is not None
            else None
        )
        if contract is None or not TOKEN_CONTRACT_NAME.search(
            str(contract.get("name", ""))
        ):
            return None
        return member, _returns_bool(callee)

    def _callee_environment(
        self,
        edge: CallEdge,
        origin_environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> dict[NodeKey, frozenset[NodeKey]]:
        call = self.project.node_for_key(edge.call_site) if edge.call_site else None
        callee = self.project.node_for_key(edge.callee) if edge.callee else None
        if call is None or callee is None:
            return {}
        arguments = call.get("arguments", [])
        if not isinstance(arguments, list):
            return {}
        result: dict[NodeKey, frozenset[NodeKey]] = {}
        for argument, parameter in zip(arguments, _parameters(callee)):
            if not isinstance(argument, dict):
                continue
            parameter_key = self.project.key_for_node(parameter)
            value = self.project.data_flow.value_for_argument(argument)
            if parameter_key is None or value is None:
                continue
            result[parameter_key] = self._normalized_origins(
                value, origin_environment
            )
        return result

    @staticmethod
    def _normalized_origins(
        value: FlowValue,
        environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> frozenset[NodeKey]:
        return frozenset(
            normalized
            for origin in value.origins
            for normalized in environment.get(origin, frozenset({origin}))
        )

    @staticmethod
    def _is_external_entry(function: Node) -> bool:
        return bool(
            function.get("nodeType") == "FunctionDefinition"
            and function.get("visibility") in {"public", "external"}
            and function.get("kind") != "constructor"
            and isinstance(function.get("body"), dict)
        )


def _returns_bool(function: Node) -> bool:
    returns = function.get("returnParameters")
    parameters = returns.get("parameters", []) if isinstance(returns, dict) else []
    if not isinstance(parameters, list) or len(parameters) != 1:
        return False
    descriptions = (
        parameters[0].get("typeDescriptions")
        if isinstance(parameters[0], dict)
        else None
    )
    return bool(
        isinstance(descriptions, dict)
        and str(descriptions.get("typeString", "")).strip() == "bool"
    )


def _parameters(function: Node) -> tuple[Node, ...]:
    parameters = function.get("parameters")
    values = parameters.get("parameters", []) if isinstance(parameters, dict) else []
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, dict))


def _is_address_this(project: "ProjectIndex", node: Node) -> bool:
    span = project.source_span(node)
    if span is None:
        return False
    source = project.source_for_id(span.compilation_id, span.source_id)
    if source is None:
        return False
    text = re.sub(r"\s+", "", source.source.text[span.start : span.end])
    return text in {"address(this)", "payable(address(this))", "this"}


def _event_sort_key(
    event: TokenTraceEvent, order: dict[NodeKey, int]
) -> tuple[int, int, int, str]:
    byte_start = event.span.byte_start if event.span is not None else -1
    node_id = event.node.node_id if event.node is not None else -1
    ordinal = order.get(event.node, 1_000_000 + max(byte_start, 0))
    return ordinal, byte_start, node_id, event.kind


def _issue_sort_key(issue: TokenIssue) -> tuple[str, int, int, str]:
    start = issue.token_call.span.byte_start if issue.token_call.span is not None else -1
    return issue.entry.compilation_id, issue.entry.node_id, start, issue.kind


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"
