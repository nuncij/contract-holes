from __future__ import annotations

from collections.abc import Iterable
import re

from .models import Finding, RuleInfo, Severity
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
                    },
                )
                if finding:
                    yield finding
                break

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


DEFAULT_RULES: tuple[Rule, ...] = (
    TxOriginRule(),
    UncheckedLowLevelCallRule(),
    DelegateCallRule(),
    SelfDestructRule(),
    ReentrancyRule(),
    WeakRandomnessRule(),
)
