from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


FOLLOW_EDGE_KINDS = frozenset({"internal", "super", "library", "modifier"})
INITIALIZER_NAME = re.compile(
    r"^(?:initialize|initializer|init|setup)(?:$|[A-Z_0-9])", re.IGNORECASE
)
INITIALIZER_MODIFIER = re.compile(
    r"(?:^|_)(?:re)?initializer(?:$|_)|onlyinitializing", re.IGNORECASE
)
INITIALIZER_GUARD_STATE = re.compile(
    r"(?:initialized|initializing|initversion|init_version)", re.IGNORECASE
)
PROXY_NAME = re.compile(r"(?:proxy|delegator|dispatcher)", re.IGNORECASE)
VERSIONED_CONTRACT = re.compile(r"^(?P<base>.+?)_?V(?P<version>\d+)$")


@dataclass(frozen=True, slots=True)
class ProxyTraceStep:
    kind: str
    owner: NodeKey
    span: SourceSpan | None
    label: str
    node: NodeKey | None = None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProxyIssue:
    kind: str
    contract: NodeKey
    entry: NodeKey | None
    sink: ProxyTraceStep
    trace: tuple[ProxyTraceStep, ...]
    metadata: dict[str, object] = field(default_factory=dict)


class ProxyAnalysis:
    """Classify initializer, proxy storage, and versioned layout hazards."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        issues = [
            *self._initializer_issues(),
            *self._proxy_storage_issues(),
            *self._layout_issues(),
        ]
        self.issues: tuple[ProxyIssue, ...] = tuple(
            sorted(issues, key=_issue_sort_key)
        )

    def owner_name(self, owner: NodeKey) -> str:
        node = self.project.node_for_key(owner)
        if node is None:
            return f"{owner.compilation_id}:{owner.node_id}"
        node_type = node.get("nodeType")
        name = str(node.get("name") or node.get("kind") or "<anonymous>")
        if node_type == "ContractDefinition":
            return name
        contract = self.project.enclosing_node(node, "ContractDefinition")
        return f"{contract.get('name')}.{name}" if contract is not None else name

    def event_dict(self, step: ProxyTraceStep) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": step.kind,
            "owner": self.owner_name(step.owner),
            "label": step.label,
            "path": str(step.span.path) if step.span is not None else None,
            "line": step.span.line if step.span is not None else None,
            "column": step.span.column if step.span is not None else None,
            **step.metadata,
        }
        if step.edge is not None:
            result.update(
                {
                    "call_kind": step.edge.kind,
                    "callee": (
                        self.owner_name(step.edge.callee)
                        if step.edge.callee is not None
                        else None
                    ),
                }
            )
        if step.fact is not None and step.fact.kind == "write":
            result["state_variable"] = step.fact.metadata.get("name", "<state>")
        return result

    def _initializer_issues(self) -> list[ProxyIssue]:
        issues: list[ProxyIssue] = []
        for entry, function in sorted(self.project.functions_by_id.items()):
            if not self._is_initializer_entry(function):
                continue
            reachable = frozenset(self.project.call_graph.reachable_from(entry))
            writes = tuple(
                fact
                for key in reachable
                for fact in self.project.data_flow.facts_for(function=key, kind="write")
                if fact.metadata.get("scope") == "state"
                and not INITIALIZER_GUARD_STATE.search(
                    str(fact.metadata.get("name", ""))
                )
            )
            if not writes or self._has_initializer_guard(function, reachable, writes):
                continue
            sink_fact = min(writes, key=_fact_location_key)
            contract = self.project.enclosing_node(function, "ContractDefinition")
            contract_key = self.project.key_for_node(contract) if contract else None
            if contract_key is None:
                continue
            trace = [
                ProxyTraceStep(
                    "initializer-entry",
                    entry,
                    self.project.source_span(function),
                    self.owner_name(entry),
                    node=entry,
                )
            ]
            trace.extend(self._call_path_steps(entry, sink_fact.function))
            sink = ProxyTraceStep(
                "state-write",
                sink_fact.function,
                sink_fact.span,
                str(sink_fact.metadata.get("name") or "<state>"),
                node=sink_fact.node,
                fact=sink_fact,
            )
            trace.append(sink)
            issues.append(
                ProxyIssue(
                    "unguarded-initializer",
                    contract_key,
                    entry,
                    sink,
                    tuple(trace),
                    {
                        "initializer": self.owner_name(entry),
                        "state_variable": sink.label,
                    },
                )
            )
        return issues

    def _proxy_storage_issues(self) -> list[ProxyIssue]:
        issues: list[ProxyIssue] = []
        for contract_key, contract in sorted(self.project.contracts_by_id.items()):
            delegate_sites = self._delegatecall_sites(contract_key, contract)
            if not delegate_sites:
                continue
            proxy_like = bool(PROXY_NAME.search(str(contract.get("name", "")))) or any(
                self._is_fallback_owner(site.owner) for site in delegate_sites
            )
            if not proxy_like:
                continue
            variables = self._storage_variables(contract_key)
            if not variables:
                continue
            sink = delegate_sites[0]
            first_variable = variables[0]
            variable_span = self.project.source_span(first_variable)
            variable_key = self.project.key_for_node(first_variable)
            trace = (
                ProxyTraceStep(
                    "structured-storage",
                    contract_key,
                    variable_span,
                    str(first_variable.get("name") or "<state>"),
                    node=variable_key,
                    metadata={"type": _type_string(first_variable)},
                ),
                sink,
            )
            issues.append(
                ProxyIssue(
                    "proxy-storage-collision",
                    contract_key,
                    sink.owner,
                    sink,
                    trace,
                    {
                        "state_variables": [
                            {
                                "name": str(variable.get("name") or "<state>"),
                                "type": _type_string(variable),
                            }
                            for variable in variables
                        ]
                    },
                )
            )
        return issues

    def _layout_issues(self) -> list[ProxyIssue]:
        groups: dict[tuple[str, str], list[tuple[int, NodeKey, Node]]] = {}
        for key, contract in sorted(self.project.contracts_by_id.items()):
            if contract.get("contractKind", "contract") != "contract":
                continue
            match = VERSIONED_CONTRACT.match(str(contract.get("name", "")))
            if match is None:
                continue
            marker = (key.compilation_id, match.group("base"))
            groups.setdefault(marker, []).append(
                (int(match.group("version")), key, contract)
            )

        issues: list[ProxyIssue] = []
        for versions in groups.values():
            ordered = sorted(versions)
            for (_, previous_key, previous), (_, current_key, current) in zip(
                ordered, ordered[1:]
            ):
                previous_layout = self._storage_variables(previous_key)
                current_layout = self._storage_variables(current_key)
                mismatch = _layout_mismatch(previous_layout, current_layout)
                if mismatch is None:
                    continue
                index, previous_variable, current_variable = mismatch
                previous_span = (
                    self.project.source_span(previous_variable)
                    if previous_variable is not None
                    else self.project.source_span(previous)
                )
                current_span = (
                    self.project.source_span(current_variable)
                    if current_variable is not None
                    else self.project.source_span(current)
                )
                before = ProxyTraceStep(
                    "previous-layout",
                    previous_key,
                    previous_span,
                    _variable_label(previous_variable),
                    node=(
                        self.project.key_for_node(previous_variable)
                        if previous_variable is not None
                        else previous_key
                    ),
                    metadata={"index": index},
                )
                after = ProxyTraceStep(
                    "incompatible-layout",
                    current_key,
                    current_span,
                    _variable_label(current_variable),
                    node=(
                        self.project.key_for_node(current_variable)
                        if current_variable is not None
                        else current_key
                    ),
                    metadata={"index": index},
                )
                issues.append(
                    ProxyIssue(
                        "incompatible-upgrade-layout",
                        current_key,
                        None,
                        after,
                        (before, after),
                        {
                            "previous_contract": str(previous.get("name", "")),
                            "current_contract": str(current.get("name", "")),
                            "mismatch_index": index,
                            "previous_layout": _layout_dict(previous_layout),
                            "current_layout": _layout_dict(current_layout),
                        },
                    )
                )
        return issues

    def _has_initializer_guard(
        self,
        function: Node,
        reachable: frozenset[NodeKey],
        writes: tuple[FlowFact, ...],
    ) -> bool:
        modifiers = function.get("modifiers", [])
        if isinstance(modifiers, list):
            for invocation in modifiers:
                name_node = (
                    invocation.get("modifierName")
                    if isinstance(invocation, dict)
                    else None
                )
                name = str(
                    name_node.get("name") or name_node.get("namePath") or ""
                ) if isinstance(name_node, dict) else ""
                if INITIALIZER_MODIFIER.search(name):
                    return True

        meaningful_start = min(
            (fact.span.byte_start for fact in writes if fact.span is not None),
            default=None,
        )
        guard_declarations: set[NodeKey] = set()
        for key in reachable:
            node = self.project.node_for_key(key)
            body = node.get("body") if node is not None else None
            if not isinstance(body, dict):
                continue
            for call in _walk_ast(body):
                if call.get("nodeType") != "FunctionCall" or _call_name(call) not in {
                    "require",
                    "assert",
                }:
                    continue
                span = self.project.source_span(call)
                if (
                    key == self.project.key_for_node(function)
                    and meaningful_start is not None
                    and span is not None
                    and span.byte_start >= meaningful_start
                ):
                    continue
                arguments = call.get("arguments", [])
                condition = (
                    arguments[0]
                    if isinstance(arguments, list) and arguments
                    else None
                )
                if not isinstance(condition, dict):
                    continue
                for candidate in _walk_ast(condition):
                    if candidate.get("nodeType") not in {
                        "Identifier",
                        "IdentifierPath",
                    }:
                        continue
                    resolution = self.project.resolve_reference_detail(candidate)
                    declaration = resolution.node
                    if (
                        declaration is not None
                        and resolution.key is not None
                        and declaration.get("stateVariable") is True
                        and INITIALIZER_GUARD_STATE.search(
                            str(declaration.get("name", ""))
                        )
                    ):
                        guard_declarations.add(resolution.key)
        written_declarations = {
            fact.declaration
            for key in reachable
            for fact in self.project.data_flow.facts_for(function=key, kind="write")
            if fact.metadata.get("scope") == "state"
        }
        return bool(guard_declarations & written_declarations)

    def _delegatecall_sites(
        self, contract_key: NodeKey, contract: Node
    ) -> tuple[ProxyTraceStep, ...]:
        sites: dict[tuple[int, int], ProxyTraceStep] = {}
        for fact in self.project.data_flow.facts_for(kind="external-interaction"):
            if fact.metadata.get("edge_kind") != "low-level-delegatecall":
                continue
            function = self.project.node_for_key(fact.function)
            owner = (
                self.project.enclosing_node(function, "ContractDefinition")
                if function is not None
                else None
            )
            if owner is not contract:
                continue
            start = fact.span.byte_start if fact.span is not None else -1
            sites[(fact.function.node_id, start)] = ProxyTraceStep(
                "delegatecall",
                fact.function,
                fact.span,
                str(fact.metadata.get("receiver") or "delegatecall"),
                node=fact.node,
                fact=fact,
            )

        for node in _walk_ast(contract):
            if node.get("nodeType") != "InlineAssembly":
                continue
            span = self.project.source_span(node)
            if span is None or "delegatecall" not in _source_text(self.project, span):
                continue
            function = self.project.enclosing_node(node, "FunctionDefinition")
            function_key = self.project.key_for_node(function) if function else None
            if function_key is None:
                continue
            sites.setdefault(
                (function_key.node_id, span.byte_start),
                ProxyTraceStep(
                    "delegatecall",
                    function_key,
                    span,
                    "assembly delegatecall",
                    node=self.project.key_for_node(node),
                    metadata={"evidence": "compiler-inline-assembly"},
                ),
            )
        return tuple(sorted(sites.values(), key=_step_location_key))

    def _storage_variables(self, contract: NodeKey) -> tuple[Node, ...]:
        semantics = self.project.inheritance.for_contract(contract)
        if semantics is None:
            return ()
        result: list[Node] = []
        for key in semantics.state_variables:
            variable = self.project.node_for_key(key)
            if variable is None:
                continue
            if variable.get("constant") is True or variable.get("mutability") == "immutable":
                continue
            result.append(variable)
        return tuple(result)

    def _call_path_steps(
        self, entry: NodeKey, target: NodeKey
    ) -> tuple[ProxyTraceStep, ...]:
        if entry == target:
            return ()
        pending: deque[tuple[NodeKey, tuple[CallEdge, ...]]] = deque([(entry, ())])
        visited = {entry}
        while pending:
            function, path = pending.popleft()
            for edge in self.project.call_graph.edges_from(function):
                if (
                    edge.callee is None
                    or edge.is_sink
                    or edge.kind not in FOLLOW_EDGE_KINDS
                    or edge.callee in visited
                ):
                    continue
                next_path = (*path, edge)
                if edge.callee == target:
                    return tuple(
                        ProxyTraceStep(
                            "call",
                            item.caller,
                            item.span,
                            item.target,
                            node=item.call_site,
                            edge=item,
                        )
                        for item in next_path
                    )
                visited.add(edge.callee)
                pending.append((edge.callee, next_path))
        return ()

    def _is_fallback_owner(self, function: NodeKey) -> bool:
        node = self.project.node_for_key(function)
        return bool(
            node is not None
            and node.get("nodeType") == "FunctionDefinition"
            and node.get("kind") in {"fallback", "receive"}
        )

    @staticmethod
    def _is_initializer_entry(function: Node) -> bool:
        return bool(
            function.get("nodeType") == "FunctionDefinition"
            and function.get("visibility") in {"public", "external"}
            and function.get("kind") == "function"
            and INITIALIZER_NAME.search(str(function.get("name", "")))
            and isinstance(function.get("body"), dict)
        )


def _layout_mismatch(
    previous: tuple[Node, ...], current: tuple[Node, ...]
) -> tuple[int, Node | None, Node | None] | None:
    for index in range(max(len(previous), len(current))):
        before = previous[index] if index < len(previous) else None
        after = current[index] if index < len(current) else None
        if before is None:
            return None
        if after is None or _variable_signature(before) != _variable_signature(after):
            return index, before, after
    return None


def _layout_dict(variables: tuple[Node, ...]) -> list[dict[str, str]]:
    return [
        {"name": str(variable.get("name", "")), "type": _type_string(variable)}
        for variable in variables
    ]


def _variable_signature(variable: Node) -> tuple[str, str]:
    return str(variable.get("name", "")), _type_string(variable)


def _variable_label(variable: Node | None) -> str:
    if variable is None:
        return "<missing>"
    return f"{variable.get('name', '<state>')}:{_type_string(variable)}"


def _type_string(node: Node) -> str:
    descriptions = node.get("typeDescriptions")
    if not isinstance(descriptions, dict):
        return "?"
    return str(descriptions.get("typeString") or descriptions.get("typeIdentifier") or "?")


def _call_name(call: Node) -> str:
    expression = call.get("expression")
    while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
        expression = expression.get("expression")
    if not isinstance(expression, dict):
        return "<call>"
    return str(expression.get("name") or expression.get("memberName") or "<call>")


def _source_text(project: "ProjectIndex", span: SourceSpan) -> str:
    source = project.source_for_id(span.compilation_id, span.source_id)
    return source.source.text[span.start : span.end] if source is not None else ""


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


def _fact_location_key(fact: FlowFact) -> tuple[str, int, int]:
    return (
        str(fact.span.path) if fact.span is not None else "",
        fact.span.byte_start if fact.span is not None else -1,
        fact.function.node_id,
    )


def _step_location_key(step: ProxyTraceStep) -> tuple[str, int, int]:
    return (
        str(step.span.path) if step.span is not None else "",
        step.span.byte_start if step.span is not None else -1,
        step.owner.node_id,
    )


def _issue_sort_key(issue: ProxyIssue) -> tuple[str, int, str, int]:
    return (
        issue.contract.compilation_id,
        issue.contract.node_id,
        issue.kind,
        issue.sink.span.byte_start if issue.sink.span is not None else -1,
    )
