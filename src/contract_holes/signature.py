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
REPLAY_STATE_NAME = re.compile(
    r"(?:nonce|used(?:hash|digest|signature)|consumed(?:hash|digest|signature)|"
    r"executed(?:hash|digest)|replay)",
    re.IGNORECASE,
)
NONCE_STATE_NAME = re.compile(r"nonce", re.IGNORECASE)
DEADLINE_NAME = re.compile(
    r"(?:deadline|expiry|expires|expiration|validuntil|valid_until)", re.IGNORECASE
)
RECOVERED_SIGNER_NAME = re.compile(r"(?:signer|recovered)", re.IGNORECASE)
DOMAIN_SEPARATOR_NAME = re.compile(r"domain_?separator", re.IGNORECASE)
CHAIN_ID_NAME = re.compile(r"chain_?id", re.IGNORECASE)
VERIFYING_CONTRACT_NAME = re.compile(
    r"(?:verifying_?contract|contract_?address)", re.IGNORECASE
)
HAZARD_ORDER = (
    "missing-replay-protection",
    "missing-deadline",
    "weak-domain-separation",
    "unchecked-zero-recovery",
)


@dataclass(frozen=True, slots=True)
class SignatureTraceEvent:
    kind: str
    function: NodeKey
    span: SourceSpan | None
    fact: FlowFact | None = None
    edge: CallEdge | None = None
    node: NodeKey | None = None
    declaration: NodeKey | None = None
    guaranteed: bool = True
    label: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def protective(self) -> bool:
        return self.kind in {
            "deadline-check",
            "replay-protection",
            "zero-recovery-check",
        } and self.guaranteed


@dataclass(frozen=True, slots=True)
class SignatureIssue:
    entry: NodeKey
    recovery: SignatureTraceEvent
    action: SignatureTraceEvent
    hazards: tuple[str, ...]
    missing_domain_components: tuple[str, ...]
    trace: tuple[SignatureTraceEvent, ...]


class SignatureAnalysis:
    """Trace signature recovery to actions and classify missing protections."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        issues: dict[tuple[NodeKey, NodeKey | None, NodeKey | None], SignatureIssue] = {}
        for entry, function in sorted(project.functions_by_id.items()):
            if not self._is_external_entry(function):
                continue
            trace = self.trace_from(entry)
            for recovery_index, recovery in enumerate(trace):
                if recovery.kind != "recovery":
                    continue
                action_index = next(
                    (
                        index
                        for index in range(recovery_index + 1, len(trace))
                        if trace[index].kind == "action"
                    ),
                    None,
                )
                if action_index is None:
                    continue
                action = trace[action_index]
                prefix = trace[: action_index + 1]
                if not any(
                    event.kind == "signer-validation"
                    and event.guaranteed
                    and index > recovery_index
                    for index, event in enumerate(prefix)
                ):
                    continue
                hazards, missing_domain = self._hazards(prefix, recovery)
                if not hazards:
                    continue
                issue = SignatureIssue(
                    entry=entry,
                    recovery=recovery,
                    action=action,
                    hazards=hazards,
                    missing_domain_components=missing_domain,
                    trace=prefix,
                )
                issues.setdefault((entry, recovery.node, action.node), issue)
        self.issues: tuple[SignatureIssue, ...] = tuple(
            sorted(issues.values(), key=_issue_sort_key)
        )

    def trace_from(
        self, function: NodeKey | Node
    ) -> tuple[SignatureTraceEvent, ...]:
        key = (
            function
            if isinstance(function, NodeKey)
            else self.project.key_for_node(function)
        )
        if key is None:
            return ()
        node = self.project.node_for_key(key)
        span = self.project.source_span(node) if node is not None else None
        entry = SignatureTraceEvent(
            "entry", key, span, node=key, label=self.function_name(key)
        )
        return (entry, *self._unfold(key, frozenset(), True, {}))

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

    def event_dict(self, event: SignatureTraceEvent) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": event.kind,
            "function": self.function_name(event.function),
            "label": event.label,
            "guaranteed": event.guaranteed,
            "protective": event.protective,
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
            if event.fact.kind == "write":
                result["action_kind"] = "state-write"
                result["state_variable"] = event.fact.metadata.get("name", "<state>")
            else:
                result["action_kind"] = "external-interaction"
                result["call_kind"] = event.fact.metadata.get("edge_kind")
        return result

    def _unfold(
        self,
        function: NodeKey,
        stack: frozenset[NodeKey],
        inherited_guarantee: bool,
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> list[SignatureTraceEvent]:
        if function in stack:
            return []
        function_node = self.project.node_for_key(function)
        if function_node is None:
            return []
        byte_limit = self._modifier_placeholder_start(function_node)
        local_events: list[SignatureTraceEvent] = []
        for fact in self.project.data_flow.facts_for(function=function):
            if byte_limit is not None and not _before_limit(fact.span, byte_limit):
                continue
            event = self._fact_event(
                function, fact, inherited_guarantee, feature_environment
            )
            if event is not None:
                local_events.append(event)
        local_events.extend(
            self._control_events(function, function_node, inherited_guarantee, byte_limit)
        )
        for edge in self.project.call_graph.edges_from(function):
            if (
                edge.callee is None
                or edge.is_sink
                or edge.kind not in FOLLOW_EDGE_KINDS
                or (byte_limit is not None and not _before_limit(edge.span, byte_limit))
            ):
                continue
            local_events.append(
                SignatureTraceEvent(
                    "call",
                    function,
                    edge.span,
                    edge=edge,
                    node=edge.call_site,
                    guaranteed=(
                        inherited_guarantee and self._is_unconditional(edge.call_site)
                    ),
                    label=edge.target,
                )
            )
        order = execution_order(self.project, function_node)
        local_events.sort(key=lambda event: _event_sort_key(event, order))

        result: list[SignatureTraceEvent] = []
        next_stack = stack | {function}
        for event in local_events:
            result.append(event)
            if event.edge is not None and event.edge.callee not in next_stack:
                callee_environment = self._callee_feature_environment(
                    event.edge,
                    function,
                    feature_environment,
                )
                result.extend(
                    self._unfold(
                        event.edge.callee,
                        next_stack,
                        event.guaranteed,
                        callee_environment,
                    )
                )
        return result

    def _fact_event(
        self,
        function: NodeKey,
        fact: FlowFact,
        inherited_guarantee: bool,
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> SignatureTraceEvent | None:
        guaranteed = inherited_guarantee and self._is_unconditional(fact.node)
        if fact.kind == "signature-recovery":
            call = self.project.node_for_key(fact.node) if fact.node is not None else None
            chain, contract, nonce = (
                self._digest_features(call, function, feature_environment)
                if call is not None
                else (False, False, False)
            )
            return SignatureTraceEvent(
                "recovery",
                function,
                fact.span,
                fact=fact,
                node=fact.node,
                declaration=self._recovery_result_declaration(call),
                guaranteed=guaranteed,
                label=str(fact.metadata.get("primitive", "ecrecover")),
                metadata={
                    "domain_chain_id": chain,
                    "domain_contract": contract,
                    "digest_state_nonce": nonce,
                },
            )
        if fact.kind == "write" and fact.metadata.get("scope") == "state":
            name = str(fact.metadata.get("name", ""))
            kind = "replay-protection" if REPLAY_STATE_NAME.search(name) else "action"
            return SignatureTraceEvent(
                kind,
                function,
                fact.span,
                fact=fact,
                node=fact.node,
                declaration=fact.declaration,
                guaranteed=guaranteed,
                label=name or "<state>",
                metadata=(
                    {
                        "replay_strategy": (
                            "nonce" if NONCE_STATE_NAME.search(name) else "digest"
                        )
                    }
                    if kind == "replay-protection"
                    else {}
                ),
            )
        if fact.kind == "external-interaction":
            if fact.metadata.get("edge_kind") == "low-level-staticcall":
                return None
            return SignatureTraceEvent(
                "action",
                function,
                fact.span,
                fact=fact,
                node=fact.node,
                guaranteed=guaranteed,
                label=str(fact.metadata.get("target", "external interaction")),
            )
        return None

    def _control_events(
        self,
        function: NodeKey,
        function_node: Node,
        inherited_guarantee: bool,
        byte_limit: int | None,
    ) -> list[SignatureTraceEvent]:
        body = function_node.get("body")
        if not isinstance(body, dict):
            return []
        events: list[SignatureTraceEvent] = []
        for call in _walk_ast(body):
            if call.get("nodeType") != "FunctionCall" or _call_name(call) not in {
                "require",
                "assert",
            }:
                continue
            arguments = call.get("arguments", [])
            condition = arguments[0] if isinstance(arguments, list) and arguments else None
            if not isinstance(condition, dict):
                continue
            for comparison in _walk_ast(condition):
                if comparison.get("nodeType") != "BinaryOperation":
                    continue
                span = self.project.source_span(comparison)
                if byte_limit is not None and not _before_limit(span, byte_limit):
                    continue
                comparison_key = self.project.key_for_node(comparison)
                guaranteed = inherited_guarantee and self._is_unconditional(
                    comparison_key
                )
                if self._is_deadline_comparison(comparison):
                    events.append(
                        SignatureTraceEvent(
                            "deadline-check",
                            function,
                            span,
                            node=comparison_key,
                            guaranteed=guaranteed,
                            label="timestamp expiry",
                        )
                    )
                zero_target = self._zero_recovery_target(comparison)
                if zero_target is not None:
                    declaration, recovery_node = zero_target
                    events.append(
                        SignatureTraceEvent(
                            "zero-recovery-check",
                            function,
                            span,
                            node=comparison_key,
                            declaration=declaration,
                            guaranteed=guaranteed,
                            label="recovered signer is nonzero",
                            metadata={
                                "recovery_node": (
                                    _key_text(recovery_node)
                                    if recovery_node is not None
                                    else None
                                )
                            },
                        )
                    )
                elif self._is_signer_validation(comparison):
                    events.append(
                        SignatureTraceEvent(
                            "signer-validation",
                            function,
                            span,
                            node=comparison_key,
                            guaranteed=guaranteed,
                            label="recovered signer gates action",
                        )
                    )
        return events

    def _hazards(
        self,
        prefix: tuple[SignatureTraceEvent, ...],
        recovery: SignatureTraceEvent,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        hazards: set[str] = set()
        replay_events = tuple(
            event
            for event in prefix
            if event.kind == "replay-protection" and event.protective
        )
        replay_protected = any(
            event.metadata.get("replay_strategy") == "digest"
            or (
                event.metadata.get("replay_strategy") == "nonce"
                and recovery.metadata.get("digest_state_nonce") is True
            )
            for event in replay_events
        )
        if not replay_protected:
            hazards.add("missing-replay-protection")
        if not any(
            event.kind == "deadline-check" and event.protective for event in prefix
        ):
            hazards.add("missing-deadline")
        missing_domain: list[str] = []
        if recovery.metadata.get("domain_chain_id") is not True:
            missing_domain.append("chain-id")
        if recovery.metadata.get("domain_contract") is not True:
            missing_domain.append("verifying-contract")
        if missing_domain:
            hazards.add("weak-domain-separation")
        if not any(self._zero_check_matches(event, recovery) for event in prefix):
            hazards.add("unchecked-zero-recovery")
        return (
            tuple(hazard for hazard in HAZARD_ORDER if hazard in hazards),
            tuple(missing_domain),
        )

    @staticmethod
    def _zero_check_matches(
        event: SignatureTraceEvent, recovery: SignatureTraceEvent
    ) -> bool:
        if event.kind != "zero-recovery-check" or not event.protective:
            return False
        if recovery.declaration is not None and event.declaration == recovery.declaration:
            return True
        recovery_node = event.metadata.get("recovery_node")
        return recovery.node is not None and recovery_node == _key_text(recovery.node)

    def _digest_features(
        self,
        call: Node,
        function: NodeKey,
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> tuple[bool, bool, bool]:
        arguments = call.get("arguments", [])
        digest = arguments[0] if isinstance(arguments, list) and arguments else None
        if not isinstance(digest, dict):
            return False, False, False
        before = self.project.source_span(call)
        return self._expression_domain(
            digest,
            function,
            before.byte_start if before is not None else None,
            frozenset(),
            feature_environment,
        )

    def _expression_domain(
        self,
        expression: Node,
        function: NodeKey,
        before: int | None,
        seen: frozenset[NodeKey],
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> tuple[bool, bool, bool]:
        chain = False
        contract = False
        nonce = False
        node_type = expression.get("nodeType")
        if node_type == "MemberAccess":
            owner = expression.get("expression")
            owner_name = str(owner.get("name", "")) if isinstance(owner, dict) else ""
            member = str(expression.get("memberName", ""))
            if owner_name == "block" and member == "chainid":
                chain = True
        if node_type == "FunctionCall" and _is_address_this(expression):
            contract = True
        if node_type in {"Identifier", "IdentifierPath"}:
            resolution = self.project.resolve_reference_detail(expression)
            declaration = resolution.node
            key = resolution.key
            if declaration is not None and key is not None:
                if key in feature_environment:
                    return feature_environment[key]
                name = str(declaration.get("name", ""))
                if declaration.get("stateVariable") is True:
                    if DOMAIN_SEPARATOR_NAME.search(name):
                        return True, True, False
                    chain = bool(CHAIN_ID_NAME.search(name))
                    contract = bool(VERIFYING_CONTRACT_NAME.search(name))
                    nonce = bool(NONCE_STATE_NAME.search(name))
                elif key not in seen:
                    definition = self._definition_expression(key, function, before)
                    if definition is not None:
                        nested = self._expression_domain(
                            definition,
                            function,
                            before,
                            seen | {key},
                            feature_environment,
                        )
                        chain = chain or nested[0]
                        contract = contract or nested[1]
                        nonce = nonce or nested[2]
        if node_type == "FunctionCall":
            callee = _call_expression(expression)
            resolution = (
                self.project.resolve_reference_detail(callee)
                if isinstance(callee, dict)
                else None
            )
            if (
                resolution is not None
                and resolution.node is not None
                and resolution.key is not None
                and resolution.key not in seen
                and resolution.node.get("nodeType") == "FunctionDefinition"
            ):
                body = resolution.node.get("body")
                if isinstance(body, dict):
                    callee_environment = self._call_feature_environment(
                        expression,
                        resolution.node,
                        function,
                        before,
                        feature_environment,
                    )
                    for node in _walk_ast(body):
                        if node.get("nodeType") != "Return":
                            continue
                        value = node.get("expression")
                        if isinstance(value, dict):
                            nested = self._expression_domain(
                                value,
                                resolution.key,
                                None,
                                seen | {resolution.key},
                                callee_environment,
                            )
                            chain = chain or nested[0]
                            contract = contract or nested[1]
                            nonce = nonce or nested[2]
        for child in _ast_children(expression):
            nested = self._expression_domain(
                child, function, before, seen, feature_environment
            )
            chain = chain or nested[0]
            contract = contract or nested[1]
            nonce = nonce or nested[2]
        return chain, contract, nonce

    def _callee_feature_environment(
        self,
        edge: CallEdge,
        function: NodeKey,
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> dict[NodeKey, tuple[bool, bool, bool]]:
        call = self.project.node_for_key(edge.call_site) if edge.call_site else None
        callee = self.project.node_for_key(edge.callee) if edge.callee else None
        if call is None or callee is None:
            return {}
        span = self.project.source_span(call)
        return self._call_feature_environment(
            call,
            callee,
            function,
            span.byte_start if span is not None else None,
            feature_environment,
        )

    def _call_feature_environment(
        self,
        call: Node,
        callee: Node,
        function: NodeKey,
        before: int | None,
        feature_environment: dict[NodeKey, tuple[bool, bool, bool]],
    ) -> dict[NodeKey, tuple[bool, bool, bool]]:
        arguments = call.get("arguments", [])
        if not isinstance(arguments, list):
            return {}
        result: dict[NodeKey, tuple[bool, bool, bool]] = {}
        for argument, parameter in zip(arguments, _parameters(callee)):
            if not isinstance(argument, dict):
                continue
            key = self.project.key_for_node(parameter)
            if key is None:
                continue
            result[key] = self._expression_domain(
                argument,
                function,
                before,
                frozenset(),
                feature_environment,
            )
        return result

    def _definition_expression(
        self, declaration: NodeKey, function: NodeKey, before: int | None
    ) -> Node | None:
        declaration_node = self.project.node_for_key(declaration)
        if declaration_node is None:
            return None
        parent = self.project.parent(declaration_node)
        if parent is not None and parent.get("nodeType") == "VariableDeclarationStatement":
            initial = parent.get("initialValue")
            if isinstance(initial, dict):
                return initial
        function_node = self.project.node_for_key(function)
        body = function_node.get("body") if function_node is not None else None
        if not isinstance(body, dict):
            return None
        candidates: list[tuple[int, Node]] = []
        for node in _walk_ast(body):
            if node.get("nodeType") != "Assignment":
                continue
            span = self.project.source_span(node)
            if span is None or (before is not None and span.byte_start >= before):
                continue
            left = node.get("leftHandSide")
            right = node.get("rightHandSide")
            if (
                isinstance(left, dict)
                and isinstance(right, dict)
                and _references_declaration(self.project, left, declaration)
            ):
                candidates.append((span.byte_start, right))
        return max(candidates, default=(0, None), key=lambda item: item[0])[1]

    def _recovery_result_declaration(self, call: Node) -> NodeKey | None:
        current: Node | None = call
        while current is not None:
            parent = self.project.parent(current)
            if parent is None:
                return None
            node_type = parent.get("nodeType")
            if node_type == "VariableDeclarationStatement":
                declarations = parent.get("declarations", [])
                if isinstance(declarations, list):
                    for declaration in declarations:
                        if isinstance(declaration, dict):
                            key = self.project.key_for_node(declaration)
                            if key is not None:
                                return key
                return None
            if node_type == "Assignment" and parent.get("rightHandSide") is current:
                left = parent.get("leftHandSide")
                return _first_declaration_reference(self.project, left)
            if node_type.endswith("Statement") or node_type in {
                "FunctionDefinition",
                "ModifierDefinition",
            }:
                return None
            current = parent
        return None

    def _is_deadline_comparison(self, comparison: Node) -> bool:
        operator = comparison.get("operator")
        if operator not in {"<", "<=", ">", ">="}:
            return False
        left = comparison.get("leftExpression")
        right = comparison.get("rightExpression")
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        return bool(
            (
                operator in {"<", "<="}
                and _contains_timestamp(left)
                and _contains_deadline(right)
            )
            or (
                operator in {">", ">="}
                and _contains_deadline(left)
                and _contains_timestamp(right)
            )
        )

    def _zero_recovery_target(
        self, comparison: Node
    ) -> tuple[NodeKey | None, NodeKey | None] | None:
        if comparison.get("operator") != "!=":
            return None
        left = comparison.get("leftExpression")
        right = comparison.get("rightExpression")
        if not isinstance(left, dict) or not isinstance(right, dict):
            return None
        if _is_zero_address(self.project, left):
            candidate = right
        elif _is_zero_address(self.project, right):
            candidate = left
        else:
            return None
        recovery_call = next(
            (
                node
                for node in _walk_ast(candidate)
                if node.get("nodeType") == "FunctionCall"
                and _call_name(node) == "ecrecover"
            ),
            None,
        )
        recovery_key = (
            self.project.key_for_node(recovery_call)
            if recovery_call is not None
            else None
        )
        declaration = _first_declaration_reference(self.project, candidate)
        return (declaration, recovery_key) if declaration is not None or recovery_key else None

    def _is_signer_validation(self, comparison: Node) -> bool:
        if comparison.get("operator") not in {"==", "!="}:
            return False
        for node in _walk_ast(comparison):
            if (
                node.get("nodeType") == "FunctionCall"
                and _call_name(node) == "ecrecover"
            ):
                return True
            if node.get("nodeType") not in {"Identifier", "IdentifierPath"}:
                continue
            resolution = self.project.resolve_reference_detail(node)
            declaration = resolution.node
            name = str(
                declaration.get("name", "")
                if declaration is not None
                else node.get("name", "")
            )
            if RECOVERED_SIGNER_NAME.search(name):
                return True
        return False

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


def _call_name(call: Node) -> str:
    expression = _call_expression(call)
    if not isinstance(expression, dict):
        return "<call>"
    return str(expression.get("name") or expression.get("memberName") or "<call>")


def _call_expression(call: Node) -> Node | None:
    expression = call.get("expression")
    while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
        expression = expression.get("expression")
    return expression if isinstance(expression, dict) else None


def _is_address_this(call: Node) -> bool:
    expression = _call_expression(call)
    if (
        not isinstance(expression, dict)
        or expression.get("nodeType") != "ElementaryTypeNameExpression"
    ):
        return False
    type_name = expression.get("typeName")
    if not isinstance(type_name, dict) or type_name.get("name") != "address":
        return False
    arguments = call.get("arguments", [])
    return bool(
        isinstance(arguments, list)
        and any(
            isinstance(argument, dict) and argument.get("name") == "this"
            for argument in arguments
        )
    )


def _is_zero_address(project: "ProjectIndex", node: Node) -> bool:
    if node.get("nodeType") == "Literal" and str(node.get("value", "")) == "0":
        return True
    span = project.source_span(node)
    if span is None:
        return False
    source = project.source_for_id(span.compilation_id, span.source_id)
    if source is None:
        return False
    text = re.sub(r"\s+", "", source.source.text[span.start : span.end])
    return text in {"address(0)", "address(0x0)", "payable(address(0))"}


def _contains_timestamp(node: Node) -> bool:
    return any(
        candidate.get("nodeType") == "MemberAccess"
        and candidate.get("memberName") == "timestamp"
        and isinstance((owner := candidate.get("expression")), dict)
        and owner.get("name") == "block"
        for candidate in _walk_ast(node)
    )


def _contains_deadline(node: Node) -> bool:
    return any(
        DEADLINE_NAME.search(
            str(candidate.get("name") or candidate.get("memberName") or "")
        )
        for candidate in _walk_ast(node)
    )


def _references_declaration(
    project: "ProjectIndex", expression: Node, declaration: NodeKey
) -> bool:
    return any(
        project.resolve_reference_detail(node).key == declaration
        for node in _walk_ast(expression)
        if node.get("nodeType") in {"Identifier", "IdentifierPath"}
    )


def _first_declaration_reference(
    project: "ProjectIndex", expression: object
) -> NodeKey | None:
    if not isinstance(expression, dict):
        return None
    for node in _walk_ast(expression):
        if node.get("nodeType") not in {"Identifier", "IdentifierPath"}:
            continue
        resolution = project.resolve_reference_detail(node)
        if (
            resolution.node is not None
            and resolution.node.get("nodeType") == "VariableDeclaration"
        ):
            return resolution.key
    return None


def _parameters(function: Node) -> tuple[Node, ...]:
    parameters = function.get("parameters")
    values = parameters.get("parameters", []) if isinstance(parameters, dict) else []
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, dict))


def _ast_children(node: Node):
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            yield value
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict) and "nodeType" in child:
                    yield child


def _walk_ast(node: Node):
    yield node
    for child in _ast_children(node):
        yield from _walk_ast(child)


def _before_limit(span: SourceSpan | None, byte_limit: int) -> bool:
    return span is not None and span.byte_start < byte_limit


def _event_sort_key(
    event: SignatureTraceEvent, order: dict[NodeKey, int]
) -> tuple[int, int, int, str]:
    byte_start = event.span.byte_start if event.span is not None else -1
    node_id = event.node.node_id if event.node is not None else -1
    ordinal = order.get(event.node, 1_000_000 + max(byte_start, 0))
    return ordinal, byte_start, node_id, event.kind


def _issue_sort_key(issue: SignatureIssue) -> tuple[str, int, int, int]:
    recovery_start = issue.recovery.span.byte_start if issue.recovery.span else -1
    action_start = issue.action.span.byte_start if issue.action.span else -1
    return (
        issue.entry.compilation_id,
        issue.entry.node_id,
        recovery_start,
        action_start,
    )


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"
