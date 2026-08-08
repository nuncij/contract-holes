from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from .compiler import CompilationResult, CompiledSource
from .source import SoliditySource


class ProjectIndexError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True, order=True)
class NodeKey:
    compilation_id: str
    node_id: int


@dataclass(frozen=True, slots=True)
class SourceSpan:
    path: Path
    compilation_id: str
    source_id: int
    byte_start: int
    byte_length: int
    start: int
    end: int
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class ReferenceResolution:
    status: str
    reference_id: int | None
    key: NodeKey | None
    node: dict[str, object] | None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status == "resolved" and self.node is not None


@dataclass(frozen=True, slots=True)
class IndexedSource:
    path: Path
    compilation_id: str
    source_id: int
    ast: dict[str, object]
    source: SoliditySource


Node: TypeAlias = dict[str, object]
SourceKey: TypeAlias = tuple[str, int]


DECLARATION_NODE_TYPES = frozenset(
    {
        "ContractDefinition",
        "EnumDefinition",
        "EnumValue",
        "ErrorDefinition",
        "EventDefinition",
        "FunctionDefinition",
        "ModifierDefinition",
        "StructDefinition",
        "UserDefinedValueTypeDefinition",
        "VariableDeclaration",
    }
)


class ProjectIndex:
    """Cross-source lookup for one or more solc compilation groups."""

    def __init__(self, compilation: CompilationResult):
        self.sources: tuple[IndexedSource, ...] = tuple(
            self._indexed_source(source) for source in compilation.sources
        )
        self.sources_by_id: dict[SourceKey, IndexedSource] = {}
        self.sources_by_path: dict[Path, tuple[IndexedSource, ...]] = {}
        self.nodes_by_id: dict[NodeKey, Node] = {}
        self.declarations_by_id: dict[NodeKey, Node] = {}
        self.contracts_by_id: dict[NodeKey, Node] = {}
        self.functions_by_id: dict[NodeKey, Node] = {}
        self.modifiers_by_id: dict[NodeKey, Node] = {}
        self._node_keys_by_object: dict[int, NodeKey] = {}
        self._node_sources_by_object: dict[int, IndexedSource] = {}
        self._parents_by_object: dict[int, Node | None] = {}
        self._build()
        from .inheritance import InheritanceResolver

        self.inheritance = InheritanceResolver(self)
        from .callgraph import CallGraph

        self.call_graph = CallGraph(self)
        from .dataflow import DataFlowAnalysis

        self.data_flow = DataFlowAnalysis(self)
        from .authorization import AuthorizationAnalysis

        self.authorization = AuthorizationAnalysis(self)
        from .signature import SignatureAnalysis

        self.signature = SignatureAnalysis(self)
        from .proxy import ProxyAnalysis

        self.proxy = ProxyAnalysis(self)
        from .token import TokenAnalysis

        self.token = TokenAnalysis(self)
        from .target_taint import CallTargetAnalysis

        self.target_taint = CallTargetAnalysis(self)
        from .reentrancy import ReentrancyAnalysis

        self.reentrancy = ReentrancyAnalysis(self)

    def source_for_path(self, path: Path | str) -> IndexedSource | None:
        candidates = self.sources_by_path.get(Path(path).resolve(), ())
        return candidates[0] if candidates else None

    def source_for_id(self, compilation_id: str, source_id: int) -> IndexedSource | None:
        return self.sources_by_id.get((compilation_id, source_id))

    def key_for_node(self, node: Node) -> NodeKey | None:
        return self._node_keys_by_object.get(id(node))

    def source_for_node(self, node: Node) -> IndexedSource | None:
        return self._node_sources_by_object.get(id(node))

    def parent(self, node: Node) -> Node | None:
        return self._parents_by_object.get(id(node))

    def enclosing_node(self, node: Node, node_type: str) -> Node | None:
        current = self.parent(node)
        while current is not None:
            if current.get("nodeType") == node_type:
                return current
            current = self.parent(current)
        return None

    def node_for_key(self, key: NodeKey) -> Node | None:
        return self.nodes_by_id.get(key)

    def resolve_reference(
        self, node: Node, field: str = "referencedDeclaration"
    ) -> Node | None:
        return self.resolve_reference_detail(node, field).node

    def resolve_reference_detail(
        self, node: Node, field: str = "referencedDeclaration"
    ) -> ReferenceResolution:
        reference = node.get(field)
        if not isinstance(reference, int):
            return ReferenceResolution(
                status="missing",
                reference_id=None,
                key=None,
                node=None,
                reason=f"field {field!r} has no numeric declaration reference",
            )
        return self.resolve_id(node, reference)

    def resolve_id(self, context_node: Node, reference_id: int) -> ReferenceResolution:
        if reference_id < 0:
            return ReferenceResolution(
                status="builtin",
                reference_id=reference_id,
                key=None,
                node=None,
                reason="negative solc IDs refer to built-in or generated declarations",
            )
        source = self.source_for_node(context_node)
        if source is None:
            return ReferenceResolution(
                status="unknown-context",
                reference_id=reference_id,
                key=None,
                node=None,
                reason="AST node is not part of this project index",
            )
        key = NodeKey(source.compilation_id, reference_id)
        target = self.nodes_by_id.get(key)
        if target is None:
            return ReferenceResolution(
                status="unresolved",
                reference_id=reference_id,
                key=key,
                node=None,
                reason="referenced AST node is absent from compiler build-info",
            )
        return ReferenceResolution(
            status="resolved",
            reference_id=reference_id,
            key=key,
            node=target,
        )

    def source_span(self, node: Node) -> SourceSpan | None:
        parsed = _parse_src(node.get("src"))
        if parsed is None:
            return None
        byte_start, byte_length, source_id = parsed
        context = self.source_for_node(node)
        if context is None or source_id < 0:
            return None
        source = self.source_for_id(context.compilation_id, source_id)
        if source is None:
            return None
        character_range = source.source.ast_range(node)
        if character_range is None:
            return None
        start, end = character_range
        line, column = source.source.location(start)
        end_line, end_column = source.source.location(end)
        return SourceSpan(
            path=source.path,
            compilation_id=source.compilation_id,
            source_id=source.source_id,
            byte_start=byte_start,
            byte_length=byte_length,
            start=start,
            end=end,
            line=line,
            column=column,
            end_line=end_line,
            end_column=end_column,
        )

    def _indexed_source(self, source: CompiledSource) -> IndexedSource:
        content = source.content
        if content is None:
            try:
                content = source.path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ProjectIndexError(
                    f"could not load compiler source {source.path}: {exc}"
                ) from exc
        solidity_source = SoliditySource(source.path, content, ast=source.ast)
        return IndexedSource(
            path=source.path.resolve(),
            compilation_id=source.compilation_id,
            source_id=source.source_id,
            ast=source.ast,
            source=solidity_source,
        )

    def _build(self) -> None:
        paths: dict[Path, list[IndexedSource]] = {}
        for source in self.sources:
            source_key = (source.compilation_id, source.source_id)
            existing_source = self.sources_by_id.get(source_key)
            if existing_source and existing_source.path != source.path:
                raise ProjectIndexError(
                    "duplicate solc source ID "
                    f"{source.source_id} in compilation {source.compilation_id!r}"
                )
            self.sources_by_id[source_key] = source
            paths.setdefault(source.path, []).append(source)
            self._index_tree(source.ast, source, parent=None)
        self.sources_by_path = {
            path: tuple(
                sorted(items, key=lambda item: (item.compilation_id, item.source_id))
            )
            for path, items in paths.items()
        }
        for source in self.sources:
            source.source.project_index = self
            source.source.compilation_id = source.compilation_id

    def _index_tree(
        self, node: Node, source: IndexedSource, parent: Node | None
    ) -> None:
        self._node_sources_by_object[id(node)] = source
        self._parents_by_object[id(node)] = parent
        node_id = node.get("id")
        if isinstance(node_id, int):
            key = NodeKey(source.compilation_id, node_id)
            existing = self.nodes_by_id.get(key)
            if existing is not None and existing is not node:
                raise ProjectIndexError(
                    f"duplicate AST node ID {node_id} in compilation {source.compilation_id!r}"
                )
            self.nodes_by_id[key] = node
            self._node_keys_by_object[id(node)] = key
            node_type = node.get("nodeType")
            if node_type in DECLARATION_NODE_TYPES:
                self.declarations_by_id[key] = node
            if node_type == "ContractDefinition":
                self.contracts_by_id[key] = node
            elif node_type == "FunctionDefinition":
                self.functions_by_id[key] = node
            elif node_type == "ModifierDefinition":
                self.modifiers_by_id[key] = node
        for value in node.values():
            if isinstance(value, dict) and "nodeType" in value:
                self._index_tree(value, source, parent=node)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict) and "nodeType" in child:
                        self._index_tree(child, source, parent=node)


def _parse_src(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    pieces = value.split(":", 2)
    if len(pieces) != 3:
        return None
    try:
        return int(pieces[0]), int(pieces[1]), int(pieces[2])
    except ValueError:
        return None
