from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from .project import Node, NodeKey, ReferenceResolution

if TYPE_CHECKING:
    from .project import ProjectIndex


@dataclass(frozen=True, slots=True)
class UnresolvedSymbol:
    owner: NodeKey
    relation: str
    reference_id: int | None
    reason: str


@dataclass(frozen=True, slots=True)
class ContractSemantics:
    contract: NodeKey
    direct_bases: tuple[NodeKey, ...]
    linearized_contracts: tuple[NodeKey, ...]
    state_variables: tuple[NodeKey, ...]
    visible_state_variables: tuple[NodeKey, ...]
    effective_functions: tuple[NodeKey, ...]
    effective_modifiers: tuple[NodeKey, ...]
    unresolved: tuple[UnresolvedSymbol, ...]


class InheritanceResolver:
    """Resolve compiler-provided inheritance and effective contract symbols."""

    def __init__(self, project: "ProjectIndex"):
        self.project = project
        self.contracts: dict[NodeKey, ContractSemantics] = {}
        for key in sorted(project.contracts_by_id):
            self.contracts[key] = self._contract_semantics(key)

    def for_contract(self, contract: NodeKey | Node) -> ContractSemantics | None:
        key = contract if isinstance(contract, NodeKey) else self.project.key_for_node(contract)
        return self.contracts.get(key) if key else None

    def state_variable_nodes(
        self, contract: NodeKey | Node, *, visible_only: bool = False
    ) -> tuple[Node, ...]:
        semantics = self.for_contract(contract)
        if semantics is None:
            return ()
        keys = (
            semantics.visible_state_variables
            if visible_only
            else semantics.state_variables
        )
        return self._nodes(keys)

    def effective_function_nodes(self, contract: NodeKey | Node) -> tuple[Node, ...]:
        semantics = self.for_contract(contract)
        return self._nodes(semantics.effective_functions) if semantics else ()

    def effective_modifier_nodes(self, contract: NodeKey | Node) -> tuple[Node, ...]:
        semantics = self.for_contract(contract)
        return self._nodes(semantics.effective_modifiers) if semantics else ()

    def override_resolutions(self, function: Node) -> tuple[ReferenceResolution, ...]:
        base_functions = function.get("baseFunctions", [])
        if not isinstance(base_functions, list):
            return ()
        return tuple(
            self.project.resolve_id(function, reference)
            for reference in base_functions
            if isinstance(reference, int)
        )

    def overridden_function_nodes(self, function: Node) -> tuple[Node, ...]:
        return tuple(
            resolution.node
            for resolution in self.override_resolutions(function)
            if resolution.node is not None
        )

    def modifier_resolutions(self, function: Node) -> tuple[ReferenceResolution, ...]:
        modifiers = function.get("modifiers", [])
        if not isinstance(modifiers, list):
            return ()
        resolutions: list[ReferenceResolution] = []
        for invocation in modifiers:
            if not isinstance(invocation, dict):
                continue
            modifier_name = invocation.get("modifierName")
            if isinstance(modifier_name, dict):
                resolutions.append(self.project.resolve_reference_detail(modifier_name))
        return tuple(resolutions)

    def super_target(self, member: Node) -> ReferenceResolution:
        expression = member.get("expression")
        if (
            member.get("nodeType") != "MemberAccess"
            or not isinstance(expression, dict)
            or expression.get("name") != "super"
        ):
            return ReferenceResolution(
                status="not-super",
                reference_id=None,
                key=None,
                node=None,
                reason="member access is not rooted at super",
            )
        return self.project.resolve_reference_detail(member)

    def _contract_semantics(self, key: NodeKey) -> ContractSemantics:
        contract = self.project.contracts_by_id[key]
        unresolved: list[UnresolvedSymbol] = []
        direct_bases = self._direct_bases(key, contract, unresolved)
        linearized = self._linearized_contracts(key, contract, direct_bases, unresolved)

        state_variables: list[NodeKey] = []
        visible_variables: list[NodeKey] = []
        seen_state: set[NodeKey] = set()
        for contract_key in reversed(linearized):
            for variable_key in self._direct_children(contract_key, "VariableDeclaration"):
                variable = self.project.nodes_by_id[variable_key]
                if variable.get("stateVariable") is not True or variable_key in seen_state:
                    continue
                seen_state.add(variable_key)
                state_variables.append(variable_key)
                if contract_key == key or variable.get("visibility") != "private":
                    visible_variables.append(variable_key)

        effective_functions = self._effective_functions(key, linearized)
        effective_modifiers = self._effective_modifiers(linearized)
        return ContractSemantics(
            contract=key,
            direct_bases=direct_bases,
            linearized_contracts=linearized,
            state_variables=tuple(state_variables),
            visible_state_variables=tuple(visible_variables),
            effective_functions=effective_functions,
            effective_modifiers=effective_modifiers,
            unresolved=tuple(_deduplicate_unresolved(unresolved)),
        )

    def _direct_bases(
        self,
        owner: NodeKey,
        contract: Node,
        unresolved: list[UnresolvedSymbol],
    ) -> tuple[NodeKey, ...]:
        result: list[NodeKey] = []
        base_contracts = contract.get("baseContracts", [])
        if not isinstance(base_contracts, list):
            return ()
        for specifier in base_contracts:
            if not isinstance(specifier, dict):
                continue
            base_name = specifier.get("baseName")
            if not isinstance(base_name, dict):
                unresolved.append(
                    UnresolvedSymbol(owner, "direct-base", None, "base has no compiler name node")
                )
                continue
            resolution = self.project.resolve_reference_detail(base_name)
            if resolution.node is None or resolution.node.get("nodeType") != "ContractDefinition":
                unresolved.append(
                    UnresolvedSymbol(
                        owner,
                        "direct-base",
                        resolution.reference_id,
                        resolution.reason or "base reference is not a contract",
                    )
                )
                continue
            assert resolution.key is not None
            if resolution.key not in result:
                result.append(resolution.key)
        return tuple(result)

    def _linearized_contracts(
        self,
        owner: NodeKey,
        contract: Node,
        direct_bases: tuple[NodeKey, ...],
        unresolved: list[UnresolvedSymbol],
    ) -> tuple[NodeKey, ...]:
        result: list[NodeKey] = []
        values = contract.get("linearizedBaseContracts")
        if isinstance(values, list) and values:
            for reference in values:
                if not isinstance(reference, int):
                    continue
                resolution = self.project.resolve_id(contract, reference)
                if resolution.node is None or resolution.node.get("nodeType") != "ContractDefinition":
                    unresolved.append(
                        UnresolvedSymbol(
                            owner,
                            "linearized-base",
                            reference,
                            resolution.reason or "linearized reference is not a contract",
                        )
                    )
                    continue
                assert resolution.key is not None
                if resolution.key not in result:
                    result.append(resolution.key)
        else:
            result.extend(
                self._fallback_linearization(owner, direct_bases, set(), unresolved)
            )
        if owner in result:
            result.remove(owner)
        result.insert(0, owner)
        return tuple(result)

    def _fallback_linearization(
        self,
        owner: NodeKey,
        bases: tuple[NodeKey, ...],
        visiting: set[NodeKey],
        unresolved: list[UnresolvedSymbol],
    ) -> list[NodeKey]:
        result = [owner]
        if owner in visiting:
            return result
        visiting = {*visiting, owner}
        for base in bases:
            if base not in result:
                result.append(base)
            base_node = self.project.contracts_by_id.get(base)
            if base_node is None:
                continue
            nested_bases = self._direct_bases(base, base_node, unresolved)
            for ancestor in self._fallback_linearization(
                base, nested_bases, visiting, unresolved
            ):
                if ancestor not in result:
                    result.append(ancestor)
        return result

    def _effective_functions(
        self, owner: NodeKey, linearized: tuple[NodeKey, ...]
    ) -> tuple[NodeKey, ...]:
        result: list[NodeKey] = []
        signatures: set[str] = set()
        for contract_key in linearized:
            for function_key in self._direct_children(contract_key, "FunctionDefinition"):
                function = self.project.nodes_by_id[function_key]
                if contract_key != owner and (
                    function.get("visibility") == "private"
                    or function.get("kind") == "constructor"
                ):
                    continue
                signature = _function_signature(function)
                if signature in signatures:
                    continue
                signatures.add(signature)
                result.append(function_key)
        return tuple(result)

    def _effective_modifiers(
        self, linearized: tuple[NodeKey, ...]
    ) -> tuple[NodeKey, ...]:
        result: list[NodeKey] = []
        names: set[str] = set()
        for contract_key in linearized:
            for modifier_key in self._direct_children(contract_key, "ModifierDefinition"):
                modifier = self.project.nodes_by_id[modifier_key]
                name = str(modifier.get("name", ""))
                if name in names:
                    continue
                names.add(name)
                result.append(modifier_key)
        return tuple(result)

    def _direct_children(self, contract_key: NodeKey, node_type: str) -> tuple[NodeKey, ...]:
        contract = self.project.contracts_by_id.get(contract_key)
        if contract is None:
            return ()
        children = contract.get("nodes", [])
        if not isinstance(children, list):
            return ()
        result: list[NodeKey] = []
        for child in children:
            if not isinstance(child, dict) or child.get("nodeType") != node_type:
                continue
            child_key = self.project.key_for_node(child)
            if child_key is not None:
                result.append(child_key)
        return tuple(result)

    def _nodes(self, keys: tuple[NodeKey, ...]) -> tuple[Node, ...]:
        return tuple(
            node for key in keys if (node := self.project.node_for_key(key)) is not None
        )


def _function_signature(function: Node) -> str:
    kind = str(function.get("kind", "function"))
    name = str(function.get("name") or kind)
    parameters = function.get("parameters", {})
    values = parameters.get("parameters", []) if isinstance(parameters, dict) else []
    types = [
        _parameter_type(parameter)
        for parameter in values
        if isinstance(parameter, dict)
    ]
    return f"{name}({','.join(types)})"


def _parameter_type(parameter: Node) -> str:
    descriptions = parameter.get("typeDescriptions", {})
    if not isinstance(descriptions, dict):
        return "?"
    identifier = descriptions.get("typeIdentifier")
    if isinstance(identifier, str):
        return re.sub(
            r"_(?:memory|storage|calldata)(?:_ptr)?(?=_|$)", "", identifier
        )
    type_name = descriptions.get("typeString")
    if not isinstance(type_name, str):
        return "?"
    return re.sub(r"\s+(?:memory|storage(?:\s+ref)?|calldata)(?=\s|$)", "", type_name)


def _deduplicate_unresolved(values: list[UnresolvedSymbol]) -> list[UnresolvedSymbol]:
    result: list[UnresolvedSymbol] = []
    seen: set[tuple[NodeKey, str, int | None, str]] = set()
    for value in values:
        marker = (value.owner, value.relation, value.reference_id, value.reason)
        if marker not in seen:
            seen.add(marker)
            result.append(value)
    return result
