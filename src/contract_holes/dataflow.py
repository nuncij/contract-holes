from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import TYPE_CHECKING

from .callgraph import BUILTIN_MEMBERS, CallEdge
from .project import Node, NodeKey, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


USER_CONTROLLED_TAINTS = frozenset(
    {"external-parameter", "external-return", "msg.data", "msg.sender", "msg.value", "tx.origin"}
)
PURE_BUILTINS = frozenset(
    {
        "abi",
        "addmod",
        "assert",
        "blockhash",
        "ecrecover",
        "gasleft",
        "keccak256",
        "mulmod",
        "require",
        "ripemd160",
        "sha256",
    }
)
AUTHORIZATION_NAME = re.compile(
    r"(?:allow|auth|guard|owner|admin|operator|permission|role|whitelist)", re.IGNORECASE
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
CREATED_TAINT = "fresh-created"


def node_is_unconditional(
    project: "ProjectIndex", node: NodeKey | Node | None
) -> bool:
    if isinstance(node, NodeKey):
        node = project.node_for_key(node)
    current = project.parent(node) if node is not None else None
    while current is not None:
        node_type = str(current.get("nodeType", ""))
        if node_type in CONDITIONAL_NODE_TYPES:
            return False
        if node_type in {"FunctionDefinition", "ModifierDefinition"}:
            return True
        current = project.parent(current)
    return True


@dataclass(frozen=True, slots=True)
class FlowValue:
    taints: frozenset[str] = frozenset()
    origins: frozenset[NodeKey] = frozenset()
    unknown: bool = False

    @property
    def user_controlled(self) -> bool:
        return bool(self.taints & USER_CONTROLLED_TAINTS)

    @classmethod
    def merge(cls, *values: "FlowValue") -> "FlowValue":
        if not values:
            return cls()
        return cls(
            taints=frozenset().union(*(value.taints for value in values)),
            origins=frozenset().union(*(value.origins for value in values)),
            unknown=any(value.unknown for value in values),
        )


@dataclass(frozen=True, slots=True)
class FlowFact:
    kind: str
    function: NodeKey
    node: NodeKey | None
    declaration: NodeKey | None
    value: FlowValue
    span: SourceSpan | None
    metadata: dict[str, object] = field(default_factory=dict)


class DataFlowAnalysis:
    """Conservative intra-procedural value facts for compiler-backed rules."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        edges_by_site: dict[NodeKey, CallEdge] = {
            edge.call_site: edge
            for edge in project.call_graph.edges
            if edge.call_site is not None
        }
        facts: list[FlowFact] = []
        callable_nodes = {
            **project.functions_by_id,
            **project.modifiers_by_id,
        }
        for key in sorted(callable_nodes):
            analyzer = _FunctionAnalyzer(project, key, callable_nodes[key], edges_by_site)
            facts.extend(analyzer.analyze())
        self.facts: tuple[FlowFact, ...] = tuple(sorted(facts, key=_fact_sort_key))
        by_function: dict[NodeKey, list[FlowFact]] = {}
        by_kind: dict[str, list[FlowFact]] = {}
        for fact in self.facts:
            by_function.setdefault(fact.function, []).append(fact)
            by_kind.setdefault(fact.kind, []).append(fact)
        self.by_function = {key: tuple(values) for key, values in by_function.items()}
        self.by_kind = {key: tuple(values) for key, values in by_kind.items()}
        self.argument_values: dict[NodeKey, FlowValue] = {
            fact.node: fact.value
            for fact in self.by_kind.get("call-argument", ())
            if fact.node is not None
        }

    def facts_for(
        self,
        *,
        function: NodeKey | Node | None = None,
        kind: str | None = None,
        path: Path | str | None = None,
    ) -> tuple[FlowFact, ...]:
        if function is not None:
            key = (
                function
                if isinstance(function, NodeKey)
                else self.project.key_for_node(function)
            )
            candidates = self.by_function.get(key, ()) if key else ()
        elif kind is not None:
            candidates = self.by_kind.get(kind, ())
        else:
            candidates = self.facts
        resolved_path = Path(path).resolve() if path is not None else None
        return tuple(
            fact
            for fact in candidates
            if (kind is None or fact.kind == kind)
            and (
                resolved_path is None
                or (fact.span is not None and fact.span.path.resolve() == resolved_path)
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "facts": [self._fact_dict(fact) for fact in self.facts],
        }

    def value_for_argument(self, argument: NodeKey | Node) -> FlowValue | None:
        key = (
            argument
            if isinstance(argument, NodeKey)
            else self.project.key_for_node(argument)
        )
        return self.argument_values.get(key) if key is not None else None

    @staticmethod
    def _fact_dict(fact: FlowFact) -> dict[str, object]:
        return {
            "kind": fact.kind,
            "function": _key_text(fact.function),
            "node": _key_text(fact.node) if fact.node else None,
            "declaration": _key_text(fact.declaration) if fact.declaration else None,
            "taints": sorted(fact.value.taints),
            "origins": sorted(_key_text(key) for key in fact.value.origins),
            "unknown": fact.value.unknown,
            "user_controlled": fact.value.user_controlled,
            "location": _span_dict(fact.span),
            "metadata": fact.metadata,
        }


class _FunctionAnalyzer:
    def __init__(
        self,
        project: "ProjectIndex",
        function_key: NodeKey,
        function: Node,
        edges_by_site: dict[NodeKey, CallEdge],
    ):
        self.project = project
        self.function_key = function_key
        self.function = function
        self.edges_by_site = edges_by_site
        self.facts: list[FlowFact] = []
        self.environment: dict[NodeKey, FlowValue] = {}
        self._timelock_delay_vars: set[NodeKey] = set()
        self._timelock_pending_vars: set[NodeKey] = set()
        self._timelock_anchor: tuple[int, Node] | None = None

    def analyze(self) -> list[FlowFact]:
        self._initialize_parameters()
        self._modifier_authorization_facts()
        body = self.function.get("body")
        if isinstance(body, dict):
            self.environment = self._statement(body, self.environment)
        if (
            self._timelock_pending_vars
            and self._timelock_delay_vars
            and self._timelock_pending_vars.isdisjoint(self._timelock_delay_vars)
        ):
            assert self._timelock_anchor is not None
            self._fact(
                "authorization",
                self._timelock_anchor[1],
                value=FlowValue(
                    origins=frozenset(self._timelock_pending_vars)
                ),
                metadata={
                    "context": "timelock",
                    "mechanisms": ["timelock:delay-and-pending"],
                    "deadline_declarations": sorted(
                        _key_text(key) for key in self._timelock_delay_vars
                    ),
                },
            )
        return self.facts

    def _initialize_parameters(self) -> None:
        parameters = self.function.get("parameters", {})
        values = parameters.get("parameters", []) if isinstance(parameters, dict) else []
        externally_callable = self.function.get("visibility") in {"external", "public"}
        for parameter in values:
            if not isinstance(parameter, dict):
                continue
            key = self.project.key_for_node(parameter)
            if key is None:
                continue
            taint = "external-parameter" if externally_callable else "internal-parameter"
            value = FlowValue(
                taints=frozenset({taint}),
                origins=frozenset({key}),
                unknown=not externally_callable,
            )
            self.environment[key] = value
            self._fact(
                "input",
                parameter,
                declaration=key,
                value=value,
                metadata={
                    "name": str(parameter.get("name", "")),
                    "externally_controlled": externally_callable,
                },
            )

    def _modifier_authorization_facts(self) -> None:
        modifiers = self.function.get("modifiers", [])
        if not isinstance(modifiers, list):
            return
        for invocation in modifiers:
            if not isinstance(invocation, dict):
                continue
            name_node = invocation.get("modifierName")
            name = str(name_node.get("name", "")) if isinstance(name_node, dict) else ""
            if AUTHORIZATION_NAME.search(name):
                self._fact(
                    "authorization",
                    invocation,
                    metadata={"mechanisms": [f"modifier:{name}"]},
                )

    def _statement(
        self, statement: Node, environment: dict[NodeKey, FlowValue]
    ) -> dict[NodeKey, FlowValue]:
        previous = self.environment
        self.environment = dict(environment)
        node_type = statement.get("nodeType")
        if node_type in {"Block", "UncheckedBlock"}:
            for child in statement.get("statements", []):
                if isinstance(child, dict):
                    self.environment = self._statement(child, self.environment)
        elif node_type == "ExpressionStatement":
            expression = statement.get("expression")
            if isinstance(expression, dict):
                self._value(expression)
        elif node_type == "VariableDeclarationStatement":
            initial = statement.get("initialValue")
            value = self._value(initial) if isinstance(initial, dict) else FlowValue(unknown=True)
            declarations = statement.get("declarations", [])
            if isinstance(declarations, list):
                for declaration in declarations:
                    if isinstance(declaration, dict):
                        self._write_declaration(declaration, value, statement)
        elif node_type == "IfStatement":
            condition = statement.get("condition")
            if isinstance(condition, dict):
                condition_value = self._value(condition)
                self._authorization_condition(condition, condition_value, "if")
            baseline = dict(self.environment)
            true_body = statement.get("trueBody")
            false_body = statement.get("falseBody")
            true_environment = (
                self._statement(true_body, dict(baseline))
                if isinstance(true_body, dict)
                else dict(baseline)
            )
            false_environment = (
                self._statement(false_body, dict(baseline))
                if isinstance(false_body, dict)
                else dict(baseline)
            )
            self.environment = _merge_environments(
                baseline, true_environment, false_environment
            )
        elif node_type in {"WhileStatement", "DoWhileStatement"}:
            condition = statement.get("condition")
            if isinstance(condition, dict):
                self._value(condition)
            baseline = dict(self.environment)
            body = statement.get("body")
            body_environment = (
                self._statement(body, dict(baseline))
                if isinstance(body, dict)
                else dict(baseline)
            )
            self.environment = _merge_environments(baseline, body_environment)
        elif node_type == "ForStatement":
            initialization = statement.get("initializationExpression")
            if isinstance(initialization, dict):
                if initialization.get("nodeType", "").endswith("Statement"):
                    self.environment = self._statement(initialization, self.environment)
                else:
                    self._value(initialization)
            condition = statement.get("condition")
            if isinstance(condition, dict):
                self._value(condition)
            baseline = dict(self.environment)
            body = statement.get("body")
            body_environment = (
                self._statement(body, dict(baseline))
                if isinstance(body, dict)
                else dict(baseline)
            )
            loop_expression = statement.get("loopExpression")
            self.environment = body_environment
            if isinstance(loop_expression, dict):
                if loop_expression.get("nodeType") == "ExpressionStatement":
                    self.environment = self._statement(
                        loop_expression, self.environment
                    )
                else:
                    self._value(loop_expression)
            self.environment = _merge_environments(baseline, self.environment)
        elif node_type in {"Return", "EmitStatement", "RevertStatement"}:
            expression = (
                statement.get("expression")
                or statement.get("eventCall")
                or statement.get("errorCall")
            )
            if isinstance(expression, dict):
                value = self._value(expression)
                if node_type == "Return":
                    self._fact("return", expression, value=value)
        elif node_type == "TryStatement":
            external_call = statement.get("externalCall")
            if isinstance(external_call, dict):
                self._value(external_call)
            baseline = dict(self.environment)
            branches: list[dict[NodeKey, FlowValue]] = []
            clauses = statement.get("clauses", [])
            if isinstance(clauses, list):
                for clause in clauses:
                    block = clause.get("block") if isinstance(clause, dict) else None
                    if isinstance(block, dict):
                        branches.append(self._statement(block, dict(baseline)))
            self.environment = _merge_environments(baseline, *branches)
        elif node_type in {
            "Break",
            "Continue",
            "PlaceholderStatement",
        }:
            pass
        elif node_type == "InlineAssembly":
            self._fact(
                "unknown-expression",
                statement,
                value=FlowValue(taints=frozenset({"assembly"}), unknown=True),
                metadata={"node_type": "InlineAssembly"},
            )
        else:
            self._fact(
                "unknown-expression",
                statement,
                value=FlowValue(unknown=True),
                metadata={"node_type": str(node_type or "unknown-statement")},
            )
        result = dict(self.environment)
        self.environment = previous
        return result

    def _value(self, expression: Node) -> FlowValue:
        node_type = expression.get("nodeType")
        if node_type == "Literal":
            return FlowValue()
        if node_type in {"Identifier", "IdentifierPath"}:
            return self._identifier_value(expression)
        if node_type == "MemberAccess":
            return self._member_value(expression)
        if node_type in {"IndexAccess", "IndexRangeAccess"}:
            values = [
                self._value(child)
                for name in ("baseExpression", "indexExpression", "startExpression", "endExpression")
                if isinstance((child := expression.get(name)), dict)
            ]
            return FlowValue.merge(*values)
        if node_type in {"BinaryOperation", "Conditional"}:
            values = [
                self._value(child)
                for name in ("leftExpression", "rightExpression", "condition", "trueExpression", "falseExpression")
                if isinstance((child := expression.get(name)), dict)
            ]
            return FlowValue.merge(*values)
        if node_type == "TupleExpression":
            components = expression.get("components", [])
            return FlowValue.merge(
                *(
                    self._value(component)
                    for component in components
                    if isinstance(component, dict)
                )
            )
        if node_type == "Assignment":
            right = expression.get("rightHandSide")
            left = expression.get("leftHandSide")
            value = self._value(right) if isinstance(right, dict) else FlowValue(unknown=True)
            if expression.get("operator") != "=" and isinstance(left, dict):
                value = FlowValue.merge(self._value(left), value)
            if isinstance(left, dict):
                if (
                    expression.get("operator") == "="
                    and left.get("nodeType") in {"IndexAccess", "IndexRangeAccess"}
                ):
                    self._value(left)
                write_metadata = (
                    {"value_is_zero": True}
                    if expression.get("operator") == "="
                    and isinstance(right, dict)
                    and _is_zero_constant(right)
                    else None
                )
                self._write_target(
                    left, value, expression, metadata=write_metadata
                )
            return value
        if node_type == "UnaryOperation":
            sub_expression = expression.get("subExpression")
            value = (
                self._value(sub_expression)
                if isinstance(sub_expression, dict)
                else FlowValue(unknown=True)
            )
            if expression.get("operator") in {"++", "--", "delete"} and isinstance(
                sub_expression, dict
            ):
                self._write_target(sub_expression, value, expression)
            return value
        if node_type == "FunctionCall":
            return self._function_call_value(expression)
        if node_type == "FunctionCallOptions":
            values = [
                self._value(option)
                for option in expression.get("options", [])
                if isinstance(option, dict)
            ]
            return FlowValue.merge(*values)
        if node_type in {"ElementaryTypeNameExpression", "NewExpression"}:
            return FlowValue()
        self._fact(
            "unknown-expression",
            expression,
            value=FlowValue(unknown=True),
            metadata={"node_type": str(node_type or "unknown-expression")},
        )
        return FlowValue(unknown=True)

    def _identifier_value(self, expression: Node) -> FlowValue:
        resolution = self.project.resolve_reference_detail(expression)
        if resolution.node is None:
            if resolution.status == "builtin":
                return FlowValue()
            value = FlowValue(unknown=True)
            self._fact(
                "unknown-expression",
                expression,
                value=value,
                metadata={"name": str(expression.get("name", "")), "reason": resolution.status},
            )
            return value
        if resolution.node.get("nodeType") != "VariableDeclaration":
            return FlowValue()
        assert resolution.key is not None
        declaration = resolution.node
        if declaration.get("stateVariable") is True:
            value = FlowValue(
                taints=frozenset({"state"}),
                origins=frozenset({resolution.key}),
            )
            scope = "state"
        else:
            value = self.environment.get(
                resolution.key,
                FlowValue(origins=frozenset({resolution.key}), unknown=True),
            )
            scope = "local"
        self._fact(
            "read",
            expression,
            declaration=resolution.key,
            value=value,
            metadata={"name": str(declaration.get("name", "")), "scope": scope},
        )
        return value

    def _member_value(self, expression: Node) -> FlowValue:
        owner = expression.get("expression")
        owner_name = str(owner.get("name", "")) if isinstance(owner, dict) else ""
        member_name = str(expression.get("memberName", ""))
        special = f"{owner_name}.{member_name}"
        if special in {
            "msg.data",
            "msg.sender",
            "msg.value",
            "tx.origin",
        }:
            key = self.project.key_for_node(expression)
            value = FlowValue(
                taints=frozenset({special}),
                origins=frozenset({key}) if key else frozenset(),
            )
            self._fact(
                "input",
                expression,
                value=value,
                metadata={"name": special, "externally_controlled": True},
            )
            return value
        if owner_name == "block":
            key = self.project.key_for_node(expression)
            value = FlowValue(
                taints=frozenset({"environment"}),
                origins=frozenset({key}) if key else frozenset(),
            )
            self._fact("read", expression, value=value, metadata={"name": special, "scope": "environment"})
            return value
        return self._value(owner) if isinstance(owner, dict) else FlowValue(unknown=True)

    def _function_call_value(self, call: Node) -> FlowValue:
        raw_arguments = call.get("arguments", [])
        arguments = [
            argument
            for argument in raw_arguments
            if isinstance(argument, dict)
        ] if isinstance(raw_arguments, list) else []
        argument_values = [self._value(argument) for argument in arguments]
        for index, (argument, value) in enumerate(zip(arguments, argument_values)):
            self._fact(
                "call-argument",
                argument,
                value=value,
                metadata={"index": index},
            )
        option_names, option_expressions = _call_options(call)
        option_values = [self._value(option) for option in option_expressions]
        call_key = self.project.key_for_node(call)
        edge = self.edges_by_site.get(call_key) if call_key else None
        expression = _unwrap_call_options(call.get("expression"))
        call_name = _call_name(expression)

        if call_name in {"require", "assert"} and arguments:
            condition = arguments[0]
            if isinstance(condition, dict):
                condition_value = argument_values[0] if argument_values else FlowValue()
                self._authorization_condition(condition, condition_value, call_name)

        if call_name == "ecrecover":
            self._fact(
                "signature-recovery",
                call,
                value=FlowValue.merge(*argument_values),
                metadata={"primitive": "ecrecover"},
            )

        if edge is not None and edge.is_sink:
            parent = self.project.parent(call)
            target_expression = _call_target_expression(call, edge)
            target_value = (
                self._value(target_expression)
                if target_expression is not None
                else FlowValue(unknown=True)
            )
            callee = (
                self.project.node_for_key(edge.callee)
                if edge.callee is not None
                else None
            )
            callee_mutability = (
                callee.get("stateMutability") if callee is not None else None
            )
            result_ignored = bool(
                isinstance(parent, dict)
                and parent.get("nodeType") == "ExpressionStatement"
            )
            sink_metadata: dict[str, object] = {
                "edge_kind": edge.kind,
                "confidence": edge.confidence,
                "target": edge.target,
                "receiver": _call_receiver(self.project, call),
                "empty_calldata": _has_empty_calldata(call, edge),
                "callee_mutability": callee_mutability,
                "result_ignored": result_ignored,
            }
            self._fact(
                "external-target",
                call,
                value=target_value,
                metadata=sink_metadata,
            )
            if callee is None or callee.get("stateMutability") != "pure":
                self._fact(
                    "external-interaction",
                    call,
                    value=FlowValue.merge(*argument_values, *option_values),
                    metadata={
                        "edge_kind": edge.kind,
                        "confidence": edge.confidence,
                        "target": edge.target,
                        "receiver": _call_receiver(self.project, call),
                        "result_ignored": result_ignored,
                        "callee_mutability": callee_mutability,
                    },
                )
            transfer_value = _transferred_value(
                edge, option_names, option_values, argument_values
            )
            if transfer_value is not None:
                self._fact(
                    "value-transfer",
                    call,
                    value=transfer_value,
                    metadata={"edge_kind": edge.kind, "target": edge.target},
                )
            if edge.kind == "creation":
                return_value_taints = frozenset({CREATED_TAINT})
            else:
                return_value_taints = frozenset({"external-return"})
            return FlowValue(
                taints=return_value_taints,
                origins=frozenset({call_key}) if call_key else frozenset(),
                unknown=True,
            )
        if edge is not None:
            return FlowValue.merge(
                *argument_values,
                FlowValue(
                    taints=frozenset({"internal-return"}),
                    origins=frozenset({call_key}) if call_key else frozenset(),
                    unknown=True,
                ),
            )
        if call.get("kind") in {"typeConversion", "structConstructorCall"}:
            return FlowValue.merge(*argument_values)
        if call_name in PURE_BUILTINS or call_name in BUILTIN_MEMBERS:
            return FlowValue.merge(*argument_values, *option_values)
        resolved = (
            self.project.resolve_reference_detail(expression)
            if isinstance(expression, dict)
            else None
        )
        if resolved and resolved.node is not None and resolved.node.get("nodeType") in {
            "EventDefinition",
            "ErrorDefinition",
            "StructDefinition",
        }:
            return FlowValue.merge(*argument_values)
        value = FlowValue.merge(
            *argument_values,
            *option_values,
            FlowValue(unknown=True),
        )
        self._fact(
            "unknown-expression",
            call,
            value=value,
            metadata={"node_type": "FunctionCall", "target": call_name},
        )
        return value

    def _authorization_condition(
        self, condition: Node, value: FlowValue, context: str
    ) -> None:
        mechanisms = _authorization_mechanisms(condition)
        if context in {"require", "assert"}:
            delay_vars = elapsed_delay_condition(self.project, condition)
            pending_vars = pending_value_condition(self.project, condition)
            if (delay_vars or pending_vars) and node_is_unconditional(
                self.project, condition
            ):
                self._timelock_delay_vars.update(delay_vars)
                self._timelock_pending_vars.update(pending_vars)
                span = self.project.source_span(condition)
                start = span.byte_start if span is not None else -1
                if self._timelock_anchor is None or start > self._timelock_anchor[0]:
                    self._timelock_anchor = (start, condition)
        if mechanisms:
            self._fact(
                "authorization",
                condition,
                value=value,
                metadata={"context": context, "mechanisms": sorted(mechanisms)},
            )

    def _write_target(
        self,
        target: Node,
        value: FlowValue,
        site: Node,
        *,
        metadata: dict[str, object] | None = None,
    ) -> None:
        declarations = _target_declarations(self.project, target)
        if not declarations:
            self._fact(
                "unknown-expression",
                target,
                value=FlowValue.merge(value, FlowValue(unknown=True)),
                metadata={"node_type": "unresolved-write-target"},
            )
            return
        for declaration in declarations:
            node = self.project.node_for_key(declaration)
            if node is not None:
                write_metadata = dict(metadata or {})
                if _caller_owned_mapping_target(target):
                    write_metadata["index_ownership"] = "msg.sender"
                self._write_declaration(node, value, site, metadata=write_metadata)

    def _write_declaration(
        self,
        declaration: Node,
        value: FlowValue,
        site: Node,
        *,
        metadata: dict[str, object] | None = None,
    ) -> None:
        key = self.project.key_for_node(declaration)
        if key is None:
            return
        state_variable = declaration.get("stateVariable") is True
        scope = "state" if state_variable else "local"
        if not state_variable:
            self.environment[key] = value
        self._fact(
            "write",
            site,
            declaration=key,
            value=value,
            metadata={
                "name": str(declaration.get("name", "")),
                "scope": scope,
                **(metadata or {}),
            },
        )
        if not state_variable and (value.origins or value.taints):
            self._fact(
                "alias",
                site,
                declaration=key,
                value=value,
                metadata={"name": str(declaration.get("name", ""))},
            )

    def _fact(
        self,
        kind: str,
        node: Node,
        *,
        declaration: NodeKey | None = None,
        value: FlowValue = FlowValue(),
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.facts.append(
            FlowFact(
                kind=kind,
                function=self.function_key,
                node=self.project.key_for_node(node),
                declaration=declaration,
                value=value,
                span=self.project.source_span(node),
                metadata=metadata or {},
            )
        )


def _merge_environments(
    baseline: dict[NodeKey, FlowValue],
    *branches: dict[NodeKey, FlowValue],
) -> dict[NodeKey, FlowValue]:
    if not branches:
        return dict(baseline)
    result: dict[NodeKey, FlowValue] = {}
    keys = set(baseline).union(*(branch.keys() for branch in branches))
    for key in keys:
        values: list[FlowValue] = []
        for branch in branches:
            if key in branch:
                values.append(branch[key])
            elif key in baseline:
                values.append(baseline[key])
            else:
                values.append(FlowValue(unknown=True))
        result[key] = FlowValue.merge(*values)
    return result


def _target_declarations(project: "ProjectIndex", target: Node) -> tuple[NodeKey, ...]:
    node_type = target.get("nodeType")
    if node_type in {"Identifier", "IdentifierPath"}:
        resolution = project.resolve_reference_detail(target)
        if resolution.node is not None and resolution.node.get("nodeType") == "VariableDeclaration":
            return (resolution.key,) if resolution.key else ()
        return ()
    if node_type in {"IndexAccess", "IndexRangeAccess"}:
        base = target.get("baseExpression")
        return _target_declarations(project, base) if isinstance(base, dict) else ()
    if node_type == "MemberAccess":
        owner = target.get("expression")
        owner_targets = (
            _target_declarations(project, owner) if isinstance(owner, dict) else ()
        )
        if owner_targets:
            return owner_targets
        resolution = project.resolve_reference_detail(target)
        if resolution.node is not None and resolution.node.get("nodeType") == "VariableDeclaration":
            return (resolution.key,) if resolution.key else ()
        return ()
    if node_type == "TupleExpression":
        result: list[NodeKey] = []
        for component in target.get("components", []):
            if isinstance(component, dict):
                result.extend(_target_declarations(project, component))
        return tuple(dict.fromkeys(result))
    return ()


def _caller_owned_mapping_target(target: Node) -> bool:
    if target.get("nodeType") != "IndexAccess":
        return False
    index = target.get("indexExpression")
    if not isinstance(index, dict) or index.get("nodeType") != "MemberAccess":
        return False
    owner = index.get("expression")
    return bool(
        isinstance(owner, dict)
        and owner.get("nodeType") == "Identifier"
        and owner.get("name") == "msg"
        and index.get("memberName") == "sender"
    )


def _authorization_mechanisms(condition: Node) -> set[str]:
    mechanisms: set[str] = set()
    for node in _walk_ast(condition):
        node_type = node.get("nodeType")
        if node_type == "BinaryOperation" and node.get("operator") in {"==", "!="}:
            mechanisms.update(_sender_primitives(node))
        elif node_type == "FunctionCall":
            name = _call_name(_unwrap_call_options(node.get("expression")))
            if AUTHORIZATION_NAME.search(name):
                mechanisms.add(f"call:{name}")
        elif node_type == "IndexAccess":
            base = node.get("baseExpression")
            base_name = _call_name(base)
            if AUTHORIZATION_NAME.search(base_name):
                senders = _sender_primitives(node)
                mechanisms.update(f"mapping:{base_name}:{sender}" for sender in senders)
    return mechanisms


def _sender_primitives(node: Node) -> set[str]:
    result: set[str] = set()
    for candidate in _walk_ast(node):
        if candidate.get("nodeType") != "MemberAccess":
            continue
        owner = candidate.get("expression")
        owner_name = str(owner.get("name", "")) if isinstance(owner, dict) else ""
        member_name = str(candidate.get("memberName", ""))
        value = f"{owner_name}.{member_name}"
        if value in {"msg.sender", "tx.origin"}:
            result.add(value)
    return result


def elapsed_delay_condition(
    project: "ProjectIndex", condition: Node
) -> frozenset[NodeKey]:
    """State deadlines guarded by timestamp >= deadline or the reversed form."""
    comparison = _direct_comparison(condition)
    if comparison is None:
        return frozenset()
    left = comparison.get("leftExpression")
    right = comparison.get("rightExpression")
    deadline = None
    if (
        comparison.get("operator") == ">="
        and isinstance(left, dict)
        and _is_block_time_reference(left)
        and isinstance(right, dict)
    ):
        deadline = _mutable_state_declaration(project, right)
    elif (
        comparison.get("operator") == "<="
        and isinstance(right, dict)
        and _is_block_time_reference(right)
        and isinstance(left, dict)
    ):
        deadline = _mutable_state_declaration(project, left)
    return frozenset({deadline}) if deadline is not None else frozenset()


def pending_value_condition(
    project: "ProjectIndex", condition: Node
) -> frozenset[NodeKey]:
    """State declarations proven nonzero by a direct `state != zero` guard."""
    comparison = _direct_comparison(condition)
    if comparison is None or comparison.get("operator") != "!=":
        return frozenset()
    left = comparison.get("leftExpression")
    right = comparison.get("rightExpression")
    if not isinstance(left, dict) or not isinstance(right, dict):
        return frozenset()
    left_state = _mutable_state_declaration(project, left)
    right_state = _mutable_state_declaration(project, right)
    if left_state is not None and _is_zero_constant(right):
        return frozenset({left_state})
    if right_state is not None and _is_zero_constant(left):
        return frozenset({right_state})
    return frozenset()


def _is_block_time_reference(node: Node) -> bool:
    if node.get("nodeType") == "MemberAccess":
        owner = node.get("expression")
        return bool(
            isinstance(owner, dict)
            and owner.get("nodeType") == "Identifier"
            and owner.get("name") == "block"
            and node.get("memberName") == "timestamp"
        )
    return node.get("nodeType") == "Identifier" and node.get("name") == "now"


def _mutable_state_declaration(
    project: "ProjectIndex", node: Node
) -> NodeKey | None:
    if node.get("nodeType") not in {"Identifier", "IdentifierPath"}:
        return None
    resolution = project.resolve_reference_detail(node)
    declaration = resolution.node if resolution is not None else None
    if (
        declaration is None
        or declaration.get("nodeType") != "VariableDeclaration"
        or declaration.get("stateVariable") is not True
        or declaration.get("constant") is True
    ):
        return None
    return resolution.key


def _is_zero_constant(node: Node) -> bool:
    if node.get("nodeType") == "Literal":
        return node.get("value") in {"0", "0x0"} or node.get("hexValue") in {
            "0",
            "0x0",
        }
    if node.get("nodeType") == "FunctionCall" and node.get("kind") == "typeConversion":
        arguments = node.get("arguments", [])
        return bool(
            isinstance(arguments, list)
            and len(arguments) == 1
            and isinstance(arguments[0], dict)
            and _is_zero_constant(arguments[0])
        )
    return False


def _direct_comparison(node: Node) -> Node | None:
    if (
        node.get("nodeType") == "BinaryOperation"
        and node.get("operator") in {">=", ">", "<=", "<", "==", "!="}
    ):
        return node
    return None


def _call_options(call: Node) -> tuple[list[str], list[Node]]:
    expression = call.get("expression")
    if not isinstance(expression, dict) or expression.get("nodeType") != "FunctionCallOptions":
        return [], []
    names = [str(name) for name in expression.get("names", [])]
    options = [option for option in expression.get("options", []) if isinstance(option, dict)]
    return names, options


def _transferred_value(
    edge: CallEdge,
    option_names: list[str],
    option_values: list[FlowValue],
    argument_values: list[FlowValue],
) -> FlowValue | None:
    if "value" in option_names:
        index = option_names.index("value")
        if index < len(option_values):
            return option_values[index]
    if edge.kind in {"low-level-send", "low-level-transfer"} and argument_values:
        return argument_values[0]
    return None


def _unwrap_call_options(expression: object) -> object:
    while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
        expression = expression.get("expression")
    return expression


def _call_name(expression: object) -> str:
    if not isinstance(expression, dict):
        return "<call>"
    return str(expression.get("name") or expression.get("memberName") or "<call>")


def _call_receiver(project: "ProjectIndex", call: Node) -> str | None:
    expression = _unwrap_call_options(call.get("expression"))
    if not isinstance(expression, dict) or expression.get("nodeType") != "MemberAccess":
        return None
    owner = expression.get("expression")
    if not isinstance(owner, dict):
        return None
    span = project.source_span(owner)
    if span is None:
        return str(owner.get("name")) if owner.get("name") else None
    source = project.source_for_id(span.compilation_id, span.source_id)
    if source is None:
        return None
    text = source.source.text[span.start : span.end].strip()
    return text or (str(owner.get("name")) if owner.get("name") else None)


def _call_target_expression(call: Node, edge: CallEdge) -> Node | None:
    expression = _unwrap_call_options(call.get("expression"))
    if not isinstance(expression, dict):
        return None
    if expression.get("nodeType") == "MemberAccess":
        owner = expression.get("expression")
        return owner if isinstance(owner, dict) else None
    if edge.kind == "function-pointer":
        return expression
    return None


def _has_empty_calldata(call: Node, edge: CallEdge) -> bool:
    if edge.kind != "low-level-call":
        return False
    arguments = call.get("arguments", [])
    if not isinstance(arguments, list) or len(arguments) != 1:
        return False
    argument = arguments[0]
    if not isinstance(argument, dict) or argument.get("nodeType") != "Literal":
        return False
    value = argument.get("value")
    hex_value = argument.get("hexValue")
    return value in {"", None} and hex_value in {"", None}


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


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"


def _span_dict(span: SourceSpan | None) -> dict[str, object] | None:
    if span is None:
        return None
    return {"path": str(span.path), "line": span.line, "column": span.column}


def _fact_sort_key(fact: FlowFact) -> tuple[str, int, int, str, int]:
    byte_start = fact.span.byte_start if fact.span else -1
    node_id = fact.node.node_id if fact.node else -1
    declaration_id = fact.declaration.node_id if fact.declaration else -1
    return _key_text(fact.function), byte_start, node_id, fact.kind, declaration_id
