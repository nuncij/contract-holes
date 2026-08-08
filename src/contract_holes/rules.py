from __future__ import annotations

from collections.abc import Iterable
import re

from .models import Finding, RuleInfo, Severity
from .reentrancy import ReentrancyIssue
from .source import FunctionRegion, SoliditySource


class Rule:
    info: RuleInfo

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        raise NotImplementedError

    def finding(
        self,
        source: SoliditySource,
        offset: int,
        *,
        message: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Finding | None:
        if source.is_suppressed(self.info.rule_id, offset):
            return None
        line, column = source.location(offset)
        return Finding(
            rule_id=self.info.rule_id,
            severity=self.info.severity,
            title=self.info.title,
            message=message or self.info.description,
            path=source.path,
            line=line,
            column=column,
            excerpt=source.line_text(line),
            recommendation=self.info.recommendation,
            confidence=self.info.confidence,
            metadata=metadata or {},
        )


class RegexRule(Rule):
    pattern: re.Pattern[str]

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        for match in self.pattern.finditer(source.masked):
            finding = self.finding(source, match.start())
            if finding:
                yield finding


class TxOriginRule(RegexRule):
    info = RuleInfo(
        rule_id="SOL001",
        severity=Severity.HIGH,
        title="Authorization depends on tx.origin",
        description="tx.origin is unsafe for authorization because an intermediary contract can preserve the original signer.",
        recommendation="Authorize with msg.sender and explicit roles or ownership checks.",
    )
    pattern = re.compile(r"\btx\s*\.\s*origin\b")


LOW_LEVEL_CALL_RE = re.compile(
    r"\.\s*(?P<kind>call|send|staticcall|delegatecall)\s*(?:\{[^;{}]*\})?\s*\(",
    re.MULTILINE,
)


def _statement_prefix(masked: str, offset: int) -> str:
    boundary = max(
        masked.rfind(";", 0, offset),
        masked.rfind("{", 0, offset),
        masked.rfind("}", 0, offset),
    )
    return masked[boundary + 1 : offset]


class UncheckedLowLevelCallRule(Rule):
    info = RuleInfo(
        rule_id="SOL002",
        severity=Severity.MEDIUM,
        title="Unchecked low-level call result",
        description="A failed low-level call can be silently ignored, leaving contract state inconsistent.",
        recommendation="Capture the returned success value and revert or handle failure explicitly.",
    )

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        if source.ast:
            yield from self._scan_ast(source)
            return
        for match in LOW_LEVEL_CALL_RE.finditer(source.masked):
            prefix = _statement_prefix(source.masked, match.start())
            if "=" in prefix or re.search(r"\b(require|assert)\s*\(", prefix):
                continue
            target = prefix.strip()[-80:] or "<expression>"
            finding = self.finding(
                source,
                match.start(),
                metadata={"call_kind": match.group("kind"), "target": target},
            )
            if finding:
                yield finding

    def _scan_ast(self, source: SoliditySource) -> Iterable[Finding]:
        assert source.ast is not None
        if source.project_index is not None:
            yield from self._scan_data_flow(source)
            return
        for node, parent in _walk_ast(source.ast):
            if node.get("nodeType") != "FunctionCall" or not parent:
                continue
            if parent.get("nodeType") != "ExpressionStatement":
                continue
            member = _called_member(node)
            if not member or member.get("memberName") not in {
                "call",
                "send",
                "staticcall",
                "delegatecall",
            }:
                continue
            source_range = source.ast_range(node)
            if not source_range:
                continue
            target_node = member.get("expression")
            target_range = source.ast_range(target_node) if isinstance(target_node, dict) else None
            target = (
                source.text[target_range[0] : target_range[1]]
                if target_range
                else "<expression>"
            )
            finding = self.finding(
                source,
                source_range[0],
                metadata={
                    "call_kind": str(member.get("memberName")),
                    "target": target.strip(),
                    "evidence": "compiler-ast",
                },
            )
            if finding:
                yield finding

    def _scan_data_flow(self, source: SoliditySource) -> Iterable[Finding]:
        assert source.project_index is not None
        for fact in source.project_index.data_flow.facts_for(
            kind="external-interaction", path=source.path
        ):
            edge_kind = str(fact.metadata.get("edge_kind", ""))
            call_kind = edge_kind.removeprefix("low-level-")
            if call_kind not in {"call", "send", "staticcall", "delegatecall"}:
                continue
            if fact.metadata.get("result_ignored") is not True or fact.node is None:
                continue
            node = source.project_index.node_for_key(fact.node)
            if node is None:
                continue
            source_range = source.ast_range(node)
            if source_range is None:
                continue
            finding = self.finding(
                source,
                source_range[0],
                metadata={
                    "call_kind": call_kind,
                    "target": fact.metadata.get("receiver") or "<expression>",
                    "evidence": "compiler-data-flow",
                },
            )
            if finding:
                yield finding


class DelegateCallRule(RegexRule):
    info = RuleInfo(
        rule_id="SOL003",
        severity=Severity.HIGH,
        title="Delegatecall executes code in caller storage",
        description="delegatecall lets target code mutate this contract's storage and should be reviewed as a trust boundary.",
        recommendation="Allow only immutable or strictly authorized implementations and verify upgrade/storage-layout controls.",
        confidence="medium",
    )
    pattern = re.compile(r"\.\s*delegatecall\s*(?:\{[^;{}]*\})?\s*\(")


class SelfDestructRule(RegexRule):
    info = RuleInfo(
        rule_id="SOL004",
        severity=Severity.HIGH,
        title="Contract invokes selfdestruct",
        description="selfdestruct force-sends Ether and has fork-dependent semantics that can violate protocol assumptions.",
        recommendation="Remove selfdestruct; if legacy compatibility requires it, strictly constrain and document the call path.",
        confidence="high",
    )
    pattern = re.compile(r"\b(?:selfdestruct|suicide)\s*\(")


EXTERNAL_INTERACTION_RE = re.compile(
    r"\.\s*(?P<kind>call|send|transfer)\s*(?:\{[^;{}]*\})?\s*\(",
    re.MULTILINE,
)


def _mutation_pattern(variable: str) -> re.Pattern[str]:
    return re.compile(
        rf"\b{re.escape(variable)}\b"
        r"(?:\s*\[[^;\]]+\])*"
        r"(?:\s*\.\s*[A-Za-z_$][\w$]*)?"
        r"\s*(?:\+\+|--|[+\-*/%&|^]?=(?!=))",
        re.MULTILINE,
    )


class ReentrancyRule(Rule):
    info = RuleInfo(
        rule_id="SOL005",
        severity=Severity.HIGH,
        title="State update follows an external interaction",
        description="An external interaction occurs before persistent state is updated, enabling a possible reentrant call.",
        recommendation="Apply checks-effects-interactions and consider a reentrancy guard around the complete state transition.",
        confidence="medium",
    )

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        if source.project_index is not None:
            yield from self._scan_data_flow(source)
            return
        for function in source.functions:
            if not function.contract or not function.contract.state_variables:
                continue
            body = source.masked[function.body_start : function.body_end]
            for call in EXTERNAL_INTERACTION_RE.finditer(body):
                after_call = body[call.end() :]
                mutation = self._first_mutation(after_call, function)
                if mutation is None:
                    continue
                variable, relative_offset = mutation
                call_offset = function.body_start + call.start()
                mutation_offset = function.body_start + call.end() + relative_offset
                mutation_line, _ = source.location(mutation_offset)
                finding = self.finding(
                    source,
                    call_offset,
                    message=(
                        f"External {call.group('kind')} occurs before state variable "
                        f"{variable!r} is updated on line {mutation_line}."
                    ),
                    metadata={
                        "function": function.name,
                        "state_variable": variable,
                        "mutation_line": mutation_line,
                        "evidence": "source-heuristic",
                    },
                )
                if finding:
                    yield finding
                break

    def _scan_data_flow(self, source: SoliditySource) -> Iterable[Finding]:
        assert source.project_index is not None
        analysis = source.project_index.reentrancy
        current_path = source.path.resolve()
        for issue in analysis.issues:
            entry = source.project_index.node_for_key(issue.entry)
            entry_source = (
                source.project_index.source_for_node(entry) if entry is not None else None
            )
            if entry_source is None or entry_source.path.resolve() != current_path:
                continue
            anchor = self._finding_anchor(source, issue)
            if anchor is None:
                continue
            state_variable = analysis.state_variable_name(issue.state_write)
            interaction_name = analysis.function_name(issue.interaction.function)
            write_name = analysis.function_name(issue.state_write.function)
            interaction_line = (
                issue.interaction.span.line if issue.interaction.span is not None else None
            )
            mutation_line = (
                issue.state_write.span.line if issue.state_write.span is not None else None
            )
            finding = self.finding(
                source,
                anchor,
                message=(
                    f"External interaction in {interaction_name} occurs before "
                    f"state variable {state_variable!r} is updated in {write_name}."
                ),
                metadata={
                    "evidence": "compiler-interprocedural-data-flow",
                    "entry_function": analysis.function_name(issue.entry),
                    "interaction_function": interaction_name,
                    "state_write_function": write_name,
                    "state_variable": state_variable,
                    "interaction_line": interaction_line,
                    "mutation_line": mutation_line,
                    "trace": [analysis.event_dict(event) for event in issue.trace],
                },
            )
            if finding:
                yield finding

    @staticmethod
    def _finding_anchor(
        source: SoliditySource, issue: ReentrancyIssue
    ) -> int | None:
        current_path = source.path.resolve()
        interaction = issue.interaction
        if (
            interaction.span is not None
            and interaction.span.path.resolve() == current_path
        ):
            return interaction.span.start
        for event in issue.trace:
            if (
                event.kind == "call"
                and event.function == issue.entry
                and event.span is not None
                and event.span.path.resolve() == current_path
            ):
                return event.span.start
        entry_node = source.project_index.node_for_key(issue.entry)
        entry_span = (
            source.project_index.source_span(entry_node)
            if entry_node is not None
            else None
        )
        return entry_span.start if entry_span is not None else None

    @staticmethod
    def _first_mutation(text: str, function: FunctionRegion) -> tuple[str, int] | None:
        assert function.contract is not None
        matches: list[tuple[int, str]] = []
        for variable in function.contract.state_variables:
            match = _mutation_pattern(variable).search(text)
            if match:
                matches.append((match.start(), variable))
        if not matches:
            return None
        offset, variable = min(matches)
        return variable, offset


class WeakRandomnessRule(Rule):
    info = RuleInfo(
        rule_id="SOL006",
        severity=Severity.MEDIUM,
        title="Predictable on-chain value used as randomness",
        description="Block fields are observable or influenceable and cannot provide secure randomness by themselves.",
        recommendation="Use a commit-reveal construction or a verifiable randomness oracle for value-bearing decisions.",
        confidence="medium",
    )
    hash_pattern = re.compile(r"\b(?:keccak256|sha256)\s*\((?P<input>[^;]*)\)", re.DOTALL)
    weak_input = re.compile(
        r"\b(?:block\s*\.\s*(?:timestamp|prevrandao|number)|blockhash\s*\(|now\b)"
    )

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        for match in self.hash_pattern.finditer(source.masked):
            weak = self.weak_input.search(match.group("input"))
            if not weak:
                continue
            offset = match.start("input") + weak.start()
            finding = self.finding(source, offset)
            if finding:
                yield finding


class PackedEncodingCollisionRule(Rule):
    info = RuleInfo(
        rule_id="SOL007",
        severity=Severity.MEDIUM,
        title="Hash uses ambiguous packed encoding",
        description=(
            "abi.encodePacked combines multiple dynamic values without boundaries, so distinct "
            "inputs can produce the same byte sequence and hash."
        ),
        recommendation=(
            "Use abi.encode, include explicit lengths or separators, or hash each dynamic value "
            "before combining them."
        ),
        confidence="high",
    )

    def scan(self, source: SoliditySource) -> Iterable[Finding]:
        if not source.ast:
            return
        for node, parent in _walk_ast(source.ast):
            if node.get("nodeType") != "FunctionCall" or not parent:
                continue
            member = _called_member(node)
            if not member or member.get("memberName") != "encodePacked":
                continue
            owner = member.get("expression")
            if not isinstance(owner, dict) or owner.get("name") != "abi":
                continue
            if not _is_hash_call(parent):
                continue
            arguments = node.get("arguments", [])
            if not isinstance(arguments, list):
                continue
            dynamic_types = [
                type_name
                for argument in arguments
                if isinstance(argument, dict)
                and (type_name := _type_name(argument))
                and _is_dynamic_packed_type(type_name)
            ]
            if len(dynamic_types) < 2:
                continue
            source_range = source.ast_range(node)
            if not source_range:
                continue
            finding = self.finding(
                source,
                source_range[0],
                metadata={
                    "dynamic_argument_types": dynamic_types,
                    "evidence": "compiler-ast",
                },
            )
            if finding:
                yield finding


def _walk_ast(
    node: dict[str, object], parent: dict[str, object] | None = None
) -> Iterable[tuple[dict[str, object], dict[str, object] | None]]:
    yield node, parent
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            yield from _walk_ast(value, node)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, dict) and "nodeType" in child:
                    yield from _walk_ast(child, node)


def _called_member(node: dict[str, object]) -> dict[str, object] | None:
    expression = node.get("expression")
    while isinstance(expression, dict) and expression.get("nodeType") == "FunctionCallOptions":
        expression = expression.get("expression")
    if isinstance(expression, dict) and expression.get("nodeType") == "MemberAccess":
        return expression
    return None


def _is_hash_call(node: dict[str, object]) -> bool:
    if node.get("nodeType") != "FunctionCall":
        return False
    expression = node.get("expression")
    return isinstance(expression, dict) and expression.get("name") in {"keccak256", "sha256"}


def _type_name(node: dict[str, object]) -> str | None:
    descriptions = node.get("typeDescriptions")
    if not isinstance(descriptions, dict):
        return None
    value = descriptions.get("typeString")
    return value if isinstance(value, str) else None


def _is_dynamic_packed_type(type_name: str) -> bool:
    normalized = type_name.strip()
    return bool(
        re.match(r"^(?:string|bytes)(?:\s|$)", normalized)
        or re.search(r"\[\](?:\s|$)", normalized)
    )


DEFAULT_RULES: tuple[Rule, ...] = (
    TxOriginRule(),
    UncheckedLowLevelCallRule(),
    DelegateCallRule(),
    SelfDestructRule(),
    ReentrancyRule(),
    WeakRandomnessRule(),
    PackedEncodingCollisionRule(),
)
