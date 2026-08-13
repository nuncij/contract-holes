from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .callgraph import CallEdge
from .dataflow import FlowFact, FlowValue, USER_CONTROLLED_TAINTS
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


FOLLOW_EDGE_KINDS = frozenset({"internal", "super", "library", "modifier"})
TARGET_EDGE_KINDS = frozenset(
    {
        "external",
        "external-dynamic",
        "function-pointer",
        "low-level-call",
        "low-level-delegatecall",
        "low-level-staticcall",
    }
)


@dataclass(frozen=True, slots=True)
class TargetTraceStep:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    label: str
    taints: tuple[str, ...] = ()
    node: NodeKey | None = None
    edge: CallEdge | None = None


@dataclass(frozen=True, slots=True)
class CallTargetIssue:
    entry: NodeKey
    sink: FlowFact
    trace: tuple[TargetTraceStep, ...]
    taints: tuple[str, ...]


class CallTargetAnalysis:
    """Propagate external inputs to dangerous call destinations across helpers."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        self.target_facts = tuple(
            fact
            for fact in project.data_flow.facts_for(kind="external-target")
            if self._eligible_target(fact)
        )
        targets_by_function: dict[NodeKey, list[FlowFact]] = {}
        for fact in self.target_facts:
            targets_by_function.setdefault(fact.function, []).append(fact)
        self.targets_by_function = {
            key: tuple(values) for key, values in targets_by_function.items()
        }
        self.input_facts: dict[NodeKey, FlowFact] = {}
        for fact in project.data_flow.facts_for(kind="input"):
            if fact.node is not None:
                self.input_facts.setdefault(fact.node, fact)
            if fact.declaration is not None:
                self.input_facts.setdefault(fact.declaration, fact)

        issues: dict[tuple[NodeKey, NodeKey | None], CallTargetIssue] = {}
        provenance: dict[
            tuple[NodeKey, NodeKey | None], frozenset[NodeKey] | None
        ] = {}
        for entry, function in sorted(project.functions_by_id.items()):
            if not _is_external_entry(function):
                continue
            environment = self._entry_environment(entry, function)
            self._walk(
                entry=entry,
                function=entry,
                environment=environment,
                fixed_environment={},
                call_prefix=(),
                stack=frozenset(),
                issues=issues,
                provenance=provenance,
            )
        self.issues: tuple[CallTargetIssue, ...] = tuple(
            sorted(issues.values(), key=_issue_sort_key)
        )
        self.fixed_provenance = provenance

    def provenance_for(
        self, entry: NodeKey, sink: FlowFact
    ) -> dict[str, object] | None:
        declarations = self.fixed_provenance.get((entry, sink.node))
        if not declarations:
            return None
        return {
            "kind": "immutable-state",
            "declarations": sorted(
                str(node.get("name"))
                for key in declarations
                if (node := self.project.node_for_key(key)) is not None
            ),
            "user_controlled": False,
        }

    def function_name(self, key: NodeKey) -> str:
        node = self.project.node_for_key(key)
        if node is None:
            return f"{key.compilation_id}:{key.node_id}"
        name = str(node.get("name") or node.get("kind") or "<anonymous>")
        contract = self.project.enclosing_node(node, "ContractDefinition")
        return f"{contract.get('name')}.{name}" if contract is not None else name

    def step_dict(self, step: TargetTraceStep) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": step.kind,
            "function": self.function_name(step.function),
            "label": step.label,
            "taints": list(step.taints),
            "path": str(step.span.path) if step.span is not None else None,
            "line": step.span.line if step.span is not None else None,
            "column": step.span.column if step.span is not None else None,
        }
        if step.edge is not None:
            result.update(
                {
                    "call_kind": step.edge.kind,
                    "callee": (
                        self.function_name(step.edge.callee)
                        if step.edge.callee is not None
                        else None
                    ),
                }
            )
        return result

    def _walk(
        self,
        *,
        entry: NodeKey,
        function: NodeKey,
        environment: dict[NodeKey, tuple[TargetTraceStep, ...]],
        fixed_environment: dict[NodeKey, frozenset[NodeKey]],
        call_prefix: tuple[TargetTraceStep, ...],
        stack: frozenset[NodeKey],
        issues: dict[tuple[NodeKey, NodeKey | None], CallTargetIssue],
        provenance: dict[
            tuple[NodeKey, NodeKey | None], frozenset[NodeKey] | None
        ],
    ) -> None:
        if function in stack:
            return
        next_stack = stack | {function}
        for sink in self.targets_by_function.get(function, ()):
            self._record_fixed_provenance(
                entry, sink, fixed_environment, provenance
            )
            if not self._sink_eligible(sink, entry):
                continue
            controlled_path = self._controlled_path(
                sink.value, environment, function, call_prefix
            )
            if controlled_path is None:
                continue
            propagated_taints = tuple(
                sorted(
                    {
                        taint
                        for step in controlled_path
                        for taint in step.taints
                        if taint in USER_CONTROLLED_TAINTS
                    }
                    | set(sink.value.taints & USER_CONTROLLED_TAINTS)
                )
            )
            sink_step = TargetTraceStep(
                kind="sink",
                function=function,
                span=sink.span,
                node=sink.node,
                label=str(
                    sink.metadata.get("receiver")
                    or sink.metadata.get("target")
                    or "<target>"
                ),
                taints=propagated_taints,
            )
            trace = (*controlled_path, sink_step)
            taints = tuple(
                sorted(
                    {
                        taint
                        for step in trace
                        for taint in step.taints
                        if taint in USER_CONTROLLED_TAINTS
                    }
                )
            )
            issue = CallTargetIssue(entry, sink, trace, taints)
            key = (entry, sink.node)
            existing = issues.get(key)
            if existing is None or _trace_sort_key(trace) < _trace_sort_key(
                existing.trace
            ):
                issues[key] = issue

        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in FOLLOW_EDGE_KINDS
                or edge.callee in next_stack
            ):
                continue
            call_step = TargetTraceStep(
                kind="call",
                function=function,
                span=edge.span,
                node=edge.call_site,
                edge=edge,
                label=edge.target,
            )
            callee_environment = self._callee_environment(
                edge, environment, function, call_prefix
            )
            callee_fixed_environment = self._callee_fixed_environment(
                edge, fixed_environment
            )
            self._walk(
                entry=entry,
                function=edge.callee,
                environment=callee_environment,
                fixed_environment=callee_fixed_environment,
                call_prefix=(*call_prefix, call_step),
                stack=next_stack,
                issues=issues,
                provenance=provenance,
            )

    def _entry_environment(
        self, function_key: NodeKey, function: Node
    ) -> dict[NodeKey, tuple[TargetTraceStep, ...]]:
        result: dict[NodeKey, tuple[TargetTraceStep, ...]] = {}
        for parameter in _parameters(function):
            key = self.project.key_for_node(parameter)
            if key is None:
                continue
            fact = self.input_facts.get(key)
            if fact is None or not fact.value.user_controlled:
                continue
            result[key] = (
                TargetTraceStep(
                    kind="input",
                    function=function_key,
                    span=fact.span,
                    node=fact.node,
                    label=str(fact.metadata.get("name") or parameter.get("name") or "input"),
                    taints=tuple(sorted(fact.value.taints & USER_CONTROLLED_TAINTS)),
                ),
            )
        return result

    def _callee_environment(
        self,
        edge: CallEdge,
        environment: dict[NodeKey, tuple[TargetTraceStep, ...]],
        function: NodeKey,
        call_prefix: tuple[TargetTraceStep, ...],
    ) -> dict[NodeKey, tuple[TargetTraceStep, ...]]:
        if edge.callee is None or edge.call_site is None:
            return {}
        call = self.project.node_for_key(edge.call_site)
        callee = self.project.node_for_key(edge.callee)
        if call is None or callee is None:
            return {}
        arguments = call.get("arguments", [])
        if not isinstance(arguments, list):
            return {}
        result: dict[NodeKey, tuple[TargetTraceStep, ...]] = {}
        call_step = TargetTraceStep(
            kind="call",
            function=function,
            span=edge.span,
            node=edge.call_site,
            edge=edge,
            label=edge.target,
        )
        for argument, parameter in zip(arguments, _parameters(callee)):
            if not isinstance(argument, dict):
                continue
            value = self.project.data_flow.value_for_argument(argument)
            if value is None:
                continue
            controlled_path = self._controlled_path(
                value, environment, function, call_prefix
            )
            parameter_key = self.project.key_for_node(parameter)
            if controlled_path is None or parameter_key is None:
                continue
            result[parameter_key] = (
                *controlled_path,
                call_step,
                TargetTraceStep(
                    kind="parameter",
                    function=edge.callee,
                    span=self.project.source_span(parameter),
                    node=parameter_key,
                    label=str(parameter.get("name") or "parameter"),
                    taints=tuple(
                        sorted(
                            {
                                taint
                                for step in controlled_path
                                for taint in step.taints
                            }
                        )
                    ),
                ),
            )
        return result

    def _callee_fixed_environment(
        self,
        edge: CallEdge,
        environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> dict[NodeKey, frozenset[NodeKey]]:
        if edge.callee is None or edge.call_site is None:
            return {}
        call = self.project.node_for_key(edge.call_site)
        callee = self.project.node_for_key(edge.callee)
        if call is None or callee is None:
            return {}
        arguments = call.get("arguments", [])
        if not isinstance(arguments, list):
            return {}
        result: dict[NodeKey, frozenset[NodeKey]] = {}
        for argument, parameter in zip(arguments, _parameters(callee)):
            if not isinstance(argument, dict):
                continue
            value = self.project.data_flow.value_for_argument(argument)
            parameter_key = self.project.key_for_node(parameter)
            if value is None or parameter_key is None:
                continue
            declarations = self._fixed_declarations(value, environment)
            if declarations:
                result[parameter_key] = declarations
        return result

    def _record_fixed_provenance(
        self,
        entry: NodeKey,
        sink: FlowFact,
        environment: dict[NodeKey, frozenset[NodeKey]],
        observations: dict[
            tuple[NodeKey, NodeKey | None], frozenset[NodeKey] | None
        ],
    ) -> None:
        declarations = self._fixed_declarations(sink.value, environment)
        key = (entry, sink.node)
        if key not in observations:
            observations[key] = declarations or None
        elif not declarations:
            observations[key] = None
        elif observations[key] is not None:
            observations[key] |= declarations

    def _fixed_declarations(
        self,
        value: FlowValue,
        environment: dict[NodeKey, frozenset[NodeKey]],
    ) -> frozenset[NodeKey]:
        if value.user_controlled or not value.origins:
            return frozenset()
        result: set[NodeKey] = set()
        for origin in value.origins:
            if origin in environment:
                result.update(environment[origin])
                continue
            declaration = self.project.node_for_key(origin)
            if not _is_fixed_target_declaration(declaration):
                return frozenset()
            result.add(origin)
        return frozenset(result)

    def _controlled_path(
        self,
        value: FlowValue,
        environment: dict[NodeKey, tuple[TargetTraceStep, ...]],
        function: NodeKey,
        call_prefix: tuple[TargetTraceStep, ...],
    ) -> tuple[TargetTraceStep, ...] | None:
        inherited = [environment[origin] for origin in value.origins if origin in environment]
        if inherited:
            return min(inherited, key=_trace_sort_key)
        if not value.user_controlled:
            return None
        controlled_taints = tuple(sorted(value.taints & USER_CONTROLLED_TAINTS))
        candidates: list[TargetTraceStep] = []
        for origin in sorted(value.origins):
            fact = self.input_facts.get(origin)
            node = self.project.node_for_key(origin)
            span = fact.span if fact is not None else (
                self.project.source_span(node) if node is not None else None
            )
            label = (
                str(fact.metadata.get("name"))
                if fact is not None and fact.metadata.get("name")
                else controlled_taints[0] if controlled_taints else "external input"
            )
            candidates.append(
                TargetTraceStep(
                    kind="input",
                    function=function,
                    span=span,
                    node=origin,
                    label=label,
                    taints=controlled_taints,
                )
            )
        if not candidates:
            node = self.project.node_for_key(function)
            candidates.append(
                TargetTraceStep(
                    kind="input",
                    function=function,
                    span=self.project.source_span(node) if node is not None else None,
                    label=controlled_taints[0] if controlled_taints else "external input",
                    taints=controlled_taints,
                )
            )
        source = min(candidates, key=_step_sort_key)
        return (*call_prefix, source)

    def _sink_eligible(self, sink: FlowFact, entry: NodeKey) -> bool:
        if not self._is_read_only_sink(sink):
            return True
        if sink.metadata.get("result_ignored") is True:
            return False
        return not self._entry_is_read_only(entry)

    @staticmethod
    def _is_read_only_sink(fact: FlowFact) -> bool:
        if str(fact.metadata.get("edge_kind", "")) == "low-level-staticcall":
            return True
        return str(fact.metadata.get("callee_mutability")) in {"view", "pure"}

    def _entry_is_read_only(self, entry: NodeKey) -> bool:
        function = self.project.node_for_key(entry)
        return bool(
            function is not None
            and function.get("stateMutability") in {"view", "pure"}
        )

    @staticmethod
    def _eligible_target(fact: FlowFact) -> bool:
        edge_kind = str(fact.metadata.get("edge_kind", ""))
        if edge_kind not in TARGET_EDGE_KINDS:
            return False
        return not (
            edge_kind == "low-level-call"
            and fact.metadata.get("empty_calldata") is True
        )


def _parameters(function: Node) -> tuple[Node, ...]:
    parameter_list = function.get("parameters")
    values = parameter_list.get("parameters", []) if isinstance(parameter_list, dict) else []
    return tuple(value for value in values if isinstance(value, dict))


def _is_external_entry(function: Node) -> bool:
    return bool(
        function.get("nodeType") == "FunctionDefinition"
        and function.get("visibility") in {"external", "public"}
        and function.get("kind") != "constructor"
        and isinstance(function.get("body"), dict)
    )


def _is_fixed_target_declaration(node: Node | None) -> bool:
    return bool(
        node is not None
        and node.get("nodeType") == "VariableDeclaration"
        and node.get("stateVariable") is True
        and (node.get("mutability") == "immutable" or node.get("constant") is True)
    )


def _step_sort_key(step: TargetTraceStep) -> tuple[str, int, int, str]:
    span = step.span
    return (
        str(span.path) if span is not None else "",
        span.byte_start if span is not None else -1,
        step.node.node_id if step.node is not None else -1,
        step.label,
    )


def _trace_sort_key(trace: tuple[TargetTraceStep, ...]) -> tuple[object, ...]:
    return (len(trace), *(_step_sort_key(step) for step in trace))


def _issue_sort_key(issue: CallTargetIssue) -> tuple[str, int, str, int]:
    span = issue.sink.span
    return (
        issue.entry.compilation_id,
        issue.entry.node_id,
        str(span.path) if span is not None else "",
        span.byte_start if span is not None else -1,
    )
