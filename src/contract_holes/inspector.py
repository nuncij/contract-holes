from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .compiler import CompilerError, ForgeCompiler, find_project_root
from .dataflow import FlowFact
from .project import Node, NodeKey, ProjectIndex, ProjectIndexError, SourceSpan
from .scanner import ScanError, discover_sources


class InspectionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class InspectionFilters:
    files: tuple[str, ...] = ()
    contracts: tuple[str, ...] = ()
    functions: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        files: Iterable[str] = (),
        contracts: Iterable[str] = (),
        functions: Iterable[str] = (),
    ) -> "InspectionFilters":
        return cls(
            files=tuple(sorted(set(files))),
            contracts=tuple(sorted(set(contracts))),
            functions=tuple(sorted(set(functions))),
        )


def inspect_paths(
    paths: Iterable[Path | str],
    *,
    include_dependencies: bool = False,
    offline: bool = False,
    filters: InspectionFilters = InspectionFilters(),
    compiler: ForgeCompiler | None = None,
) -> dict[str, object]:
    try:
        files = discover_sources(paths, include_dependencies=include_dependencies)
        if not files:
            raise InspectionError("no Solidity source files found to inspect")
        root = find_project_root(files)
        compilation = (compiler or ForgeCompiler()).compile(
            files,
            project_root=root,
            offline=offline,
        )
        project = ProjectIndex(compilation)
    except (CompilerError, ProjectIndexError, ScanError) as exc:
        raise InspectionError(str(exc)) from exc
    return ProjectInspector(
        project,
        root=root,
        compiler_versions=compilation.compiler_versions,
        filters=filters,
    ).to_dict()


class ProjectInspector:
    """Deterministic, source-free JSON view of compiler analysis state."""

    def __init__(
        self,
        project: ProjectIndex,
        *,
        root: Path,
        compiler_versions: Iterable[str] = (),
        filters: InspectionFilters = InspectionFilters(),
    ):
        self.project = project
        self.root = root.resolve()
        self.compiler_versions = tuple(sorted(set(compiler_versions)))
        self.filters = filters
        callable_nodes = {
            **project.functions_by_id,
            **project.modifiers_by_id,
        }
        self.callable_nodes = callable_nodes
        self.selected_callables = tuple(
            key
            for key, node in sorted(callable_nodes.items())
            if self._matches_callable(node)
        )
        selected_callable_set = set(self.selected_callables)
        self.selected_functions = tuple(
            key for key in sorted(project.functions_by_id) if key in selected_callable_set
        )
        self.selected_modifiers = tuple(
            key for key in sorted(project.modifiers_by_id) if key in selected_callable_set
        )
        self.selected_contracts = tuple(
            key
            for key, contract in sorted(project.contracts_by_id.items())
            if self._matches_contract(contract, selected_callable_set)
        )
        self.selected_sources = tuple(
            source for source in project.sources if self._matches_source(source.path)
        )
        if filters.contracts:
            contract_sources = {
                self.project.source_for_node(self.project.contracts_by_id[key]).path
                for key in self.selected_contracts
            }
            self.selected_sources = tuple(
                source for source in self.selected_sources if source.path in contract_sources
            )
        if filters.functions:
            callable_sources = {
                self.project.source_for_node(callable_nodes[key]).path
                for key in self.selected_callables
            }
            self.selected_sources = tuple(
                source for source in self.selected_sources if source.path in callable_sources
            )
        if filters.files or filters.contracts or filters.functions:
            if not (
                self.selected_sources
                or self.selected_contracts
                or self.selected_callables
            ):
                raise InspectionError("inspection filters matched no compiler nodes")

    def to_dict(self) -> dict[str, object]:
        sources = [self._source_dict(source) for source in self.selected_sources]
        contracts = [
            self._contract_dict(key, self.project.contracts_by_id[key])
            for key in self.selected_contracts
        ]
        callables = [self._callable_dict(key) for key in self.selected_callables]
        selected = set(self.selected_callables)
        edges = [
            self._edge_dict(edge)
            for edge in self.project.call_graph.edges
            if edge.caller in selected
        ]
        facts = [
            self._fact_dict(fact)
            for fact in self.project.data_flow.facts
            if fact.function in selected
        ]
        guarded = [
            self._qualified_name(key)
            for key in sorted(self.project.reentrancy.guarded_functions)
            if key in selected
        ]
        issues = [
            self._issue_dict(issue)
            for issue in self.project.reentrancy.issues
            if issue.entry in selected
        ]
        target_issues = [
            self._target_issue_dict(issue)
            for issue in self.project.target_taint.issues
            if issue.entry in selected
        ]
        return {
            "schema_version": "1.0",
            "project_root": str(self.root),
            "compiler_versions": list(self.compiler_versions),
            "filters": {
                "files": list(self.filters.files),
                "contracts": list(self.filters.contracts),
                "functions": list(self.filters.functions),
            },
            "summary": {
                "sources": len(sources),
                "contracts": len(contracts),
                "functions": len(self.selected_functions),
                "modifiers": len(self.selected_modifiers),
                "call_edges": len(edges),
                "facts": len(facts),
                "guarded_functions": len(guarded),
                "reentrancy_issues": len(issues),
                "target_taint_issues": len(target_issues),
            },
            "project_index": {"sources": sources, "contracts": contracts},
            "inheritance": contracts,
            "call_graph": {"nodes": callables, "edges": edges},
            "data_flow": {"facts": facts},
            "reentrancy": {
                "guarded_functions": guarded,
                "issues": issues,
            },
            "target_taint": {"issues": target_issues},
        }

    def _matches_source(self, path: Path) -> bool:
        if not self.filters.files:
            return True
        candidate = path.resolve().as_posix()
        for raw_filter in self.filters.files:
            normalized = raw_filter.replace("\\", "/").removeprefix("./")
            filter_path = Path(raw_filter)
            if filter_path.is_absolute() and path.resolve() == filter_path.resolve():
                return True
            if candidate == normalized or candidate.endswith(f"/{normalized}"):
                return True
        return False

    def _matches_contract(
        self, contract: Node, selected_callables: set[NodeKey]
    ) -> bool:
        source = self.project.source_for_node(contract)
        if source is None or not self._matches_source(source.path):
            return False
        if self.filters.contracts and str(contract.get("name", "")) not in set(
            self.filters.contracts
        ):
            return False
        if not self.filters.functions:
            return True
        return any(
            key in selected_callables
            and self.project.enclosing_node(node, "ContractDefinition") is contract
            for key, node in self.callable_nodes.items()
        )

    def _matches_callable(self, node: Node) -> bool:
        source = self.project.source_for_node(node)
        if source is None or not self._matches_source(source.path):
            return False
        contract = self.project.enclosing_node(node, "ContractDefinition")
        contract_name = str(contract.get("name", "")) if contract else ""
        if self.filters.contracts and contract_name not in set(self.filters.contracts):
            return False
        if not self.filters.functions:
            return True
        name = _callable_name(node)
        qualified = f"{contract_name}.{name}" if contract_name else name
        return any(value in {name, qualified} for value in self.filters.functions)

    def _source_dict(self, source) -> dict[str, object]:
        nodes = [
            (key, node)
            for key, node in self.project.nodes_by_id.items()
            if self.project.source_for_node(node) is source
        ]
        declarations = [
            key for key, _ in nodes if key in self.project.declarations_by_id
        ]
        contracts = [
            str(node.get("name", ""))
            for _, node in nodes
            if node.get("nodeType") == "ContractDefinition"
        ]
        return {
            "path": self._path(source.path),
            "compilation_id": source.compilation_id,
            "source_id": source.source_id,
            "node_count": len(nodes),
            "declaration_count": len(declarations),
            "contracts": sorted(contracts),
        }

    def _contract_dict(self, key: NodeKey, contract: Node) -> dict[str, object]:
        semantics = self.project.inheritance.for_contract(key)
        assert semantics is not None
        return {
            "id": _key_text(key),
            "name": str(contract.get("name", "")),
            "kind": str(contract.get("contractKind", "contract")),
            "location": self._span_dict(self.project.source_span(contract)),
            "direct_bases": [
                self._qualified_name(base) for base in semantics.direct_bases
            ],
            "linearized_bases": [
                self._qualified_name(base) for base in semantics.linearized_contracts
            ],
            "state_variables": [
                self._declaration_dict(variable)
                for variable in semantics.state_variables
            ],
            "visible_state_variables": [
                self._declaration_dict(variable)
                for variable in semantics.visible_state_variables
            ],
            "effective_functions": [
                self._qualified_name(function)
                for function in semantics.effective_functions
            ],
            "effective_modifiers": [
                self._qualified_name(modifier)
                for modifier in semantics.effective_modifiers
            ],
            "unresolved": [
                {
                    "relation": item.relation,
                    "reference_id": item.reference_id,
                    "reason": item.reason,
                }
                for item in semantics.unresolved
            ],
        }

    def _declaration_dict(self, key: NodeKey) -> dict[str, object]:
        node = self.project.node_for_key(key)
        if node is None:
            return {"id": _key_text(key), "name": "<unknown>", "location": None}
        return {
            "id": _key_text(key),
            "name": str(node.get("name", "")),
            "visibility": str(node.get("visibility", "")),
            "declared_in": self._owner_name(node),
            "location": self._span_dict(self.project.source_span(node)),
        }

    def _callable_dict(self, key: NodeKey) -> dict[str, object]:
        node = self.callable_nodes[key]
        modifiers = node.get("modifiers", [])
        modifier_names: list[str] = []
        if isinstance(modifiers, list):
            for invocation in modifiers:
                name_node = invocation.get("modifierName") if isinstance(invocation, dict) else None
                if isinstance(name_node, dict):
                    modifier_names.append(
                        str(name_node.get("name") or name_node.get("namePath") or "")
                    )
        return {
            "id": _key_text(key),
            "name": _callable_name(node),
            "qualified_name": self._qualified_name(key),
            "node_type": str(node.get("nodeType", "")),
            "kind": str(node.get("kind", "modifier")),
            "visibility": str(node.get("visibility", "")),
            "state_mutability": str(node.get("stateMutability", "")),
            "modifiers": sorted(modifier_names),
            "location": self._span_dict(self.project.source_span(node)),
        }

    def _edge_dict(self, edge) -> dict[str, object]:
        return {
            "caller": self._qualified_name(edge.caller),
            "callee": self._qualified_name(edge.callee) if edge.callee else None,
            "kind": edge.kind,
            "confidence": edge.confidence,
            "is_sink": edge.is_sink,
            "target": edge.target,
            "reason": edge.reason,
            "location": self._span_dict(edge.span),
        }

    def _fact_dict(self, fact: FlowFact) -> dict[str, object]:
        return {
            "kind": fact.kind,
            "function": self._qualified_name(fact.function),
            "node": _key_text(fact.node) if fact.node else None,
            "declaration": (
                self._qualified_name(fact.declaration) if fact.declaration else None
            ),
            "taints": sorted(fact.value.taints),
            "origins": sorted(_key_text(key) for key in fact.value.origins),
            "unknown": fact.value.unknown,
            "user_controlled": fact.value.user_controlled,
            "location": self._span_dict(fact.span),
            "metadata": fact.metadata,
        }

    def _issue_dict(self, issue) -> dict[str, object]:
        analysis = self.project.reentrancy
        trace: list[dict[str, object]] = []
        for event in issue.trace:
            item = analysis.event_dict(event)
            if item.get("path") is not None:
                item["path"] = self._path(Path(str(item["path"])))
            trace.append(item)
        return {
            "entry_function": self._qualified_name(issue.entry),
            "interaction_function": self._qualified_name(issue.interaction.function),
            "state_write_function": self._qualified_name(issue.state_write.function),
            "state_variable": analysis.state_variable_name(issue.state_write),
            "trace": trace,
        }

    def _target_issue_dict(self, issue) -> dict[str, object]:
        analysis = self.project.target_taint
        trace: list[dict[str, object]] = []
        for step in issue.trace:
            item = analysis.step_dict(step)
            if item.get("path") is not None:
                item["path"] = self._path(Path(str(item["path"])))
            trace.append(item)
        return {
            "entry_function": analysis.function_name(issue.entry),
            "sink_function": analysis.function_name(issue.sink.function),
            "call_kind": issue.sink.metadata.get("edge_kind"),
            "target": issue.sink.metadata.get("receiver"),
            "taints": list(issue.taints),
            "trace": trace,
        }

    def _qualified_name(self, key: NodeKey) -> str:
        node = self.project.node_for_key(key)
        if node is None:
            return _key_text(key)
        name = _callable_name(node)
        contract = self.project.enclosing_node(node, "ContractDefinition")
        if contract is None:
            return name
        contract_name = str(contract.get("name", "<contract>"))
        return f"{contract_name}.{name}"

    def _owner_name(self, node: Node) -> str | None:
        contract = self.project.enclosing_node(node, "ContractDefinition")
        return str(contract.get("name")) if contract is not None else None

    def _span_dict(self, span: SourceSpan | None) -> dict[str, object] | None:
        if span is None:
            return None
        return {
            "path": self._path(span.path),
            "line": span.line,
            "column": span.column,
            "end_line": span.end_line,
            "end_column": span.end_column,
        }

    def _path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.root).as_posix()
        except ValueError:
            return str(resolved)


def _callable_name(node: Node) -> str:
    return str(node.get("name") or node.get("kind") or "<anonymous>")


def _key_text(key: NodeKey) -> str:
    return f"{key.compilation_id}:{key.node_id}"
