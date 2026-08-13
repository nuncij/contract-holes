from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .project import Node, NodeKey, ReferenceResolution, SourceSpan

if TYPE_CHECKING:
    from .project import ProjectIndex


LOW_LEVEL_MEMBERS = frozenset(
    {"call", "delegatecall", "staticcall", "send", "transfer"}
)
BUILTIN_MEMBERS = frozenset(
    {
        "concat",
        "decode",
        "encode",
        "encodeCall",
        "encodePacked",
        "encodeWithSelector",
        "encodeWithSignature",
        "pop",
        "push",
    }
)


@dataclass(frozen=True, slots=True)
class CallEdge:
    caller: NodeKey
    callee: NodeKey | None
    call_site: NodeKey | None
    kind: str
    confidence: str
    is_sink: bool
    target: str
    span: SourceSpan | None = None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.callee is not None


class CallGraph:
    """Deterministic call edges derived from solc declaration references."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        callable_nodes = {
            **project.functions_by_id,
            **project.modifiers_by_id,
        }
        self.nodes: tuple[NodeKey, ...] = tuple(sorted(callable_nodes))
        edges: list[CallEdge] = []
        for caller in self.nodes:
            node = callable_nodes[caller]
            edges.extend(self._modifier_edges(caller, node))
            body = node.get("body")
            if not isinstance(body, dict):
                continue
            for candidate in _walk_ast(body):
                if candidate.get("nodeType") != "FunctionCall":
                    continue
                edge = self._call_edge(caller, candidate)
                if edge is not None:
                    edges.append(edge)
        self.edges: tuple[CallEdge, ...] = tuple(sorted(edges, key=_edge_sort_key))
        outgoing: dict[NodeKey, list[CallEdge]] = {key: [] for key in self.nodes}
        incoming: dict[NodeKey, list[CallEdge]] = {key: [] for key in self.nodes}
        for edge in self.edges:
            outgoing.setdefault(edge.caller, []).append(edge)
            if edge.callee is not None:
                incoming.setdefault(edge.callee, []).append(edge)
        self.outgoing: dict[NodeKey, tuple[CallEdge, ...]] = {
            key: tuple(values) for key, values in outgoing.items()
        }
        self.incoming: dict[NodeKey, tuple[CallEdge, ...]] = {
            key: tuple(values) for key, values in incoming.items()
        }

    def edges_from(self, caller: NodeKey | Node) -> tuple[CallEdge, ...]:
        key = caller if isinstance(caller, NodeKey) else self.project.key_for_node(caller)
        return self.outgoing.get(key, ()) if key else ()

    def edges_to(self, callee: NodeKey | Node) -> tuple[CallEdge, ...]:
        key = callee if isinstance(callee, NodeKey) else self.project.key_for_node(callee)
        return self.incoming.get(key, ()) if key else ()

    def reachable_from(
        self, start: NodeKey | Node, *, include_sinks: bool = False
    ) -> tuple[NodeKey, ...]:
        start_key = start if isinstance(start, NodeKey) else self.project.key_for_node(start)
        if start_key is None:
            return ()
        visited = {start_key}
        pending = [start_key]
        while pending:
            caller = pending.pop()
            for edge in self.outgoing.get(caller, ()):
                if edge.callee is None or (edge.is_sink and not include_sinks):
                    continue
                if edge.callee not in visited:
                    visited.add(edge.callee)
                    pending.append(edge.callee)
        return tuple(sorted(visited))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "nodes": [self._node_dict(key) for key in self.nodes],
            "edges": [self._edge_dict(edge) for edge in self.edges],
        }

    def _modifier_edges(self, caller: NodeKey, function: Node) -> list[CallEdge]:
        if function.get("nodeType") != "FunctionDefinition":
            return []
        modifiers = function.get("modifiers", [])
        if not isinstance(modifiers, list):
            return []
        result: list[CallEdge] = []
        for invocation in modifiers:
            if not isinstance(invocation, dict):
                continue
            modifier_name = invocation.get("modifierName")
            if not isinstance(modifier_name, dict):
                continue
            resolution = self.project.resolve_reference_detail(modifier_name)
            if resolution.node is None or resolution.node.get("nodeType") != "ModifierDefinition":
                result.append(
                    self._edge(
                        caller,
                        invocation,
                        None,
                        kind="modifier",
                        confidence="unknown",
                        is_sink=False,
                        target=str(modifier_name.get("name", "<modifier>")),
                        reason=resolution.reason or "modifier declaration is unresolved",
                    )
                )
                continue
            result.append(
                self._edge(
                    caller,
                    invocation,
                    resolution.key,
                    kind="modifier",
                    confidence="exact",
                    is_sink=False,
                    target=str(resolution.node.get("name", "<modifier>")),
                )
            )
        return result

    def _call_edge(self, caller: NodeKey, call: Node) -> CallEdge | None:
        call_kind = call.get("kind")
        if call_kind in {"typeConversion", "structConstructorCall"}:
            return None
        expression = _unwrap_call_options(call.get("expression"))
        if not isinstance(expression, dict):
            return self._edge(
                caller,
                call,
                None,
                kind="dynamic",
                confidence="unknown",
                is_sink=True,
                target="<expression>",
                reason="call expression has no compiler AST node",
            )
        node_type = expression.get("nodeType")
        if node_type in {"Identifier", "IdentifierPath"}:
            return self._identifier_call(caller, call, expression)
        if node_type == "MemberAccess":
            return self._member_call(caller, call, expression)
        if node_type == "NewExpression":
            return self._creation_call(caller, call, expression)
        return self._edge(
            caller,
            call,
            None,
            kind="dynamic",
            confidence="unknown",
            is_sink=True,
            target=str(expression.get("name") or node_type or "<expression>"),
            reason=f"unsupported call expression {node_type!r}",
        )

    def _identifier_call(self, caller: NodeKey, call: Node, expression: Node) -> CallEdge | None:
        resolution = self.project.resolve_reference_detail(expression)
        target_name = str(expression.get("name", "<function>"))
        if resolution.node is not None and resolution.node.get("nodeType") == "FunctionDefinition":
            return self._resolved_function_edge(
                caller,
                call,
                resolution,
                target_name,
                member_owner=None,
            )
        if resolution.node is not None and resolution.node.get("nodeType") in {
            "EventDefinition",
            "ErrorDefinition",
            "StructDefinition",
        }:
            return None
        if resolution.node is not None and resolution.node.get("nodeType") == "VariableDeclaration":
            type_name = _type_string(expression) or _type_string(resolution.node) or ""
            if type_name.startswith("function"):
                external = " external" in type_name
                return self._edge(
                    caller,
                    call,
                    None,
                    kind="function-pointer",
                    confidence="dynamic",
                    is_sink=external,
                    target=target_name,
                    reason="function value selects its destination at runtime",
                )
        if resolution.status == "builtin":
            return None
        return self._edge(
            caller,
            call,
            None,
            kind="unresolved",
            confidence="unknown",
            is_sink=False,
            target=target_name,
            reason=resolution.reason or "callee declaration is unresolved",
        )

    def _member_call(self, caller: NodeKey, call: Node, member: Node) -> CallEdge | None:
        member_name = str(member.get("memberName", "<member>"))
        owner = member.get("expression")
        owner_name = str(owner.get("name", "")) if isinstance(owner, dict) else ""
        owner_resolution = (
            self.project.resolve_reference_detail(owner)
            if isinstance(owner, dict) and owner.get("nodeType") == "Identifier"
            else None
        )
        is_value_type_owner = bool(
            owner_resolution is not None
            and owner_resolution.node is not None
            and owner_resolution.node.get("nodeType")
            == "UserDefinedValueTypeDefinition"
        )
        if isinstance(owner, dict) and (
            owner.get("nodeType") == "ElementaryTypeNameExpression"
            or is_value_type_owner
        ):
            return None
        if member_name in LOW_LEVEL_MEMBERS:
            return self._edge(
                caller,
                call,
                None,
                kind=f"low-level-{member_name}",
                confidence="dynamic",
                is_sink=True,
                target=member_name,
                reason="runtime target is not a statically selected Solidity function",
            )
        if member_name in BUILTIN_MEMBERS:
            resolution = self.project.resolve_reference_detail(member)
            if resolution.status in {"builtin", "missing"}:
                return None
        if owner_name == "super":
            resolution = self.project.inheritance.super_target(member)
            return self._edge_from_resolution(
                caller,
                call,
                resolution,
                kind="super",
                confidence="exact",
                is_sink=False,
                target=member_name,
            )
        resolution = self.project.resolve_reference_detail(member)
        if resolution.node is not None and resolution.node.get("nodeType") == "FunctionDefinition":
            if owner_name == "this":
                return self._edge_from_resolution(
                    caller,
                    call,
                    resolution,
                    kind="external-self",
                    confidence="exact",
                    is_sink=True,
                    target=member_name,
                )
            return self._resolved_function_edge(
                caller,
                call,
                resolution,
                member_name,
                member_owner=owner,
            )
        if resolution.status == "builtin":
            return None
        return self._edge(
            caller,
            call,
            None,
            kind="external-dynamic",
            confidence="dynamic",
            is_sink=True,
            target=member_name,
            reason=resolution.reason or "member destination is selected at runtime",
        )

    def _resolved_function_edge(
        self,
        caller: NodeKey,
        call: Node,
        resolution: ReferenceResolution,
        target_name: str,
        member_owner: object,
    ) -> CallEdge:
        assert resolution.node is not None and resolution.key is not None
        target_contract = self.project.enclosing_node(
            resolution.node, "ContractDefinition"
        )
        contract_kind = (
            target_contract.get("contractKind")
            if isinstance(target_contract, dict)
            else None
        )
        visibility = resolution.node.get("visibility")
        if contract_kind == "library":
            is_sink = visibility in {"external", "public"}
            return self._edge_from_resolution(
                caller,
                call,
                resolution,
                kind="library",
                confidence="declaration" if is_sink else "exact",
                is_sink=is_sink,
                target=target_name,
            )
        if member_owner is not None:
            return self._edge_from_resolution(
                caller,
                call,
                resolution,
                kind="external",
                confidence="declaration",
                is_sink=True,
                target=target_name,
                reason="compiler resolves the interface declaration, not the runtime contract",
            )
        return self._edge_from_resolution(
            caller,
            call,
            resolution,
            kind="internal",
            confidence="exact",
            is_sink=False,
            target=target_name,
        )

    def _creation_call(self, caller: NodeKey, call: Node, expression: Node) -> CallEdge:
        type_name = expression.get("typeName")
        target = "<contract>"
        if isinstance(type_name, dict):
            target = str(type_name.get("name") or type_name.get("namePath") or target)
        return self._edge(
            caller,
            call,
            None,
            kind="creation",
            confidence="declaration",
            is_sink=True,
            target=target,
            reason="contract creation transfers control to constructor code",
        )

    def _edge_from_resolution(
        self,
        caller: NodeKey,
        call: Node,
        resolution: ReferenceResolution,
        *,
        kind: str,
        confidence: str,
        is_sink: bool,
        target: str,
        reason: str | None = None,
    ) -> CallEdge:
        return self._edge(
            caller,
            call,
            resolution.key if resolution.node is not None else None,
            kind=kind,
            confidence=confidence if resolution.node is not None else "unknown",
            is_sink=is_sink,
            target=target,
            reason=reason or (resolution.reason if resolution.node is None else None),
        )

    def _edge(
        self,
        caller: NodeKey,
        call_site: Node,
        callee: NodeKey | None,
        *,
        kind: str,
        confidence: str,
        is_sink: bool,
        target: str,
        reason: str | None = None,
    ) -> CallEdge:
        return CallEdge(
            caller=caller,
            callee=callee,
            call_site=self.project.key_for_node(call_site),
            kind=kind,
            confidence=confidence,
            is_sink=is_sink,
            target=target,
            span=self.project.source_span(call_site),
            reason=reason,
        )

    def _node_dict(self, key: NodeKey) -> dict[str, object]:
        node = self.project.nodes_by_id[key]
        contract = self.project.enclosing_node(node, "ContractDefinition")
        span = self.project.source_span(node)
        return {
            "id": _key_text(key),
            "name": str(node.get("name") or node.get("kind") or "<anonymous>"),
            "node_type": str(node.get("nodeType", "unknown")),
            "contract": str(contract.get("name")) if contract else None,
            "location": _span_dict(span),
        }

    def _edge_dict(self, edge: CallEdge) -> dict[str, object]:
        return {
            "caller": _key_text(edge.caller),
            "callee": _key_text(edge.callee) if edge.callee else None,
            "call_site": _key_text(edge.call_site) if edge.call_site else None,
            "kind": edge.kind,
            "confidence": edge.confidence,
            "is_sink": edge.is_sink,
            "target": edge.target,
            "reason": edge.reason,
            "location": _span_dict(edge.span),
        }


def _walk_ast(node: Node):
    yield node
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            yield from _walk_ast(value)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict) and "nodeType" in child:
                    yield from _walk_ast(child)


def _unwrap_call_options(expression: object) -> object:
    while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
        expression = expression.get("expression")
    return expression


def _type_string(node: Node) -> str | None:
    descriptions = node.get("typeDescriptions")
    if not isinstance(descriptions, dict):
        return None
    value = descriptions.get("typeString")
    return value if isinstance(value, str) else None


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"


def _span_dict(span: SourceSpan | None) -> dict[str, object] | None:
    if span is None:
        return None
    return {
        "path": str(span.path),
        "line": span.line,
        "column": span.column,
    }


def _edge_sort_key(edge: CallEdge) -> tuple[str, int, int, str, str]:
    byte_start = edge.span.byte_start if edge.span else -1
    call_site = edge.call_site.node_id if edge.call_site else -1
    callee = _key_text(edge.callee) if edge.callee else ""
    return _key_text(edge.caller), byte_start, call_site, edge.kind, callee
