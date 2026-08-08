from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


FUNCTION_RE = re.compile(
    r"\b(?P<kind>function|constructor|fallback|receive)\b"
    r"(?P<signature>[^;{}]*)\{",
    re.MULTILINE,
)
CONTRACT_RE = re.compile(
    r"\b(?:(?:abstract)\s+)?(?P<kind>contract|library)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)[^;{]*\{",
    re.MULTILINE,
)


def mask_comments_and_strings(text: str) -> str:
    """Replace comments and string contents with spaces while retaining offsets."""
    chars = list(text)
    i = 0
    state = "code"
    quote = ""
    while i < len(chars):
        char = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                i += 2
                state = "line_comment"
                continue
            if char == "/" and nxt == "*":
                chars[i] = chars[i + 1] = " "
                i += 2
                state = "block_comment"
                continue
            if char in {'"', "'"}:
                quote = char
                chars[i] = " "
                i += 1
                state = "string"
                continue
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                i += 2
                state = "code"
                continue
            if char != "\n":
                chars[i] = " "
        elif state == "string":
            if char == "\\":
                chars[i] = " "
                if i + 1 < len(chars):
                    if chars[i + 1] != "\n":
                        chars[i + 1] = " "
                    i += 2
                    continue
            if char == quote:
                chars[i] = " "
                state = "code"
            elif char != "\n":
                chars[i] = " "
        i += 1
    return "".join(chars)


def matching_brace(masked: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


@dataclass(frozen=True, slots=True)
class ContractRegion:
    name: str
    kind: str
    start: int
    body_start: int
    body_end: int
    state_variables: frozenset[str]


@dataclass(frozen=True, slots=True)
class FunctionRegion:
    name: str
    start: int
    body_start: int
    body_end: int
    header: str
    contract: ContractRegion | None


class SoliditySource:
    def __init__(self, path: Path, text: str, ast: dict[str, object] | None = None):
        self.path = path
        self.text = text
        self.masked = mask_comments_and_strings(text)
        self.ast = ast
        self._line_starts = [0]
        self._line_starts.extend(index + 1 for index, char in enumerate(text) if char == "\n")
        self._byte_boundaries = _byte_boundaries(text) if ast else ()
        if ast:
            self.contracts = self._find_ast_contracts(ast)
            self.functions = self._find_ast_functions(ast)
        else:
            self.contracts = self._find_contracts()
            self.functions = self._find_functions()

    @classmethod
    def from_path(
        cls, path: Path, ast: dict[str, object] | None = None
    ) -> "SoliditySource":
        return cls(path, path.read_text(encoding="utf-8"), ast=ast)

    def location(self, offset: int) -> tuple[int, int]:
        import bisect

        line_index = bisect.bisect_right(self._line_starts, offset) - 1
        return line_index + 1, offset - self._line_starts[line_index] + 1

    def line_text(self, line: int) -> str:
        return self.text.splitlines()[line - 1].strip() if self.text else ""

    def is_suppressed(self, rule_id: str, offset: int) -> bool:
        line, _ = self.location(offset)
        lines = self.text.splitlines()
        candidates = lines[max(0, line - 2) : line]
        for candidate in candidates:
            marker = re.search(r"holes-ignore(?:-next-line)?\s+([^\n]+)", candidate)
            if not marker:
                continue
            rule_ids = re.split(r"[\s,]+", marker.group(1).strip())
            if rule_id in rule_ids or "all" in {item.lower() for item in rule_ids}:
                return True
        return False

    def function_at(self, offset: int) -> FunctionRegion | None:
        return next(
            (function for function in self.functions if function.body_start <= offset <= function.body_end),
            None,
        )

    def ast_range(self, node: dict[str, object]) -> tuple[int, int] | None:
        if not self._byte_boundaries:
            return None
        value = node.get("src")
        if not isinstance(value, str):
            return None
        pieces = value.split(":", 2)
        if len(pieces) < 2:
            return None
        try:
            byte_start, byte_length = int(pieces[0]), int(pieces[1])
        except ValueError:
            return None
        return (
            _byte_to_character(self._byte_boundaries, byte_start),
            _byte_to_character(self._byte_boundaries, byte_start + byte_length),
        )

    def _find_ast_contracts(self, ast: dict[str, object]) -> tuple[ContractRegion, ...]:
        contracts: list[ContractRegion] = []
        nodes = ast.get("nodes", [])
        if not isinstance(nodes, list):
            return self._find_contracts()
        for node in nodes:
            if not isinstance(node, dict) or node.get("nodeType") != "ContractDefinition":
                continue
            source_range = self.ast_range(node)
            if not source_range:
                continue
            start, end = source_range
            opening = self.masked.find("{", start, end)
            closing = matching_brace(self.masked, opening) if opening >= 0 else None
            if closing is None:
                continue
            child_nodes = node.get("nodes", [])
            state_variables = {
                str(child.get("name"))
                for child in child_nodes
                if isinstance(child, dict)
                and child.get("nodeType") == "VariableDeclaration"
                and child.get("stateVariable") is True
                and child.get("name")
            }
            contracts.append(
                ContractRegion(
                    name=str(node.get("name", "<anonymous>")),
                    kind=str(node.get("contractKind", "contract")),
                    start=start,
                    body_start=opening + 1,
                    body_end=closing,
                    state_variables=frozenset(state_variables),
                )
            )
        return tuple(contracts) or self._find_contracts()

    def _find_ast_functions(self, ast: dict[str, object]) -> tuple[FunctionRegion, ...]:
        functions: list[FunctionRegion] = []
        nodes = ast.get("nodes", [])
        if not isinstance(nodes, list):
            return self._find_functions()
        for contract_node in nodes:
            if not isinstance(contract_node, dict) or contract_node.get("nodeType") != "ContractDefinition":
                continue
            contract_range = self.ast_range(contract_node)
            contract = next(
                (
                    item
                    for item in self.contracts
                    if contract_range and item.start == contract_range[0]
                ),
                None,
            )
            child_nodes = contract_node.get("nodes", [])
            if not isinstance(child_nodes, list):
                continue
            for node in child_nodes:
                if not isinstance(node, dict) or node.get("nodeType") != "FunctionDefinition":
                    continue
                body = node.get("body")
                source_range = self.ast_range(node)
                body_range = self.ast_range(body) if isinstance(body, dict) else None
                if not source_range or not body_range:
                    continue
                start, _ = source_range
                body_ast_start, body_ast_end = body_range
                opening = self.masked.find("{", body_ast_start, body_ast_end)
                closing = matching_brace(self.masked, opening) if opening >= 0 else None
                if closing is None:
                    continue
                kind = str(node.get("kind", "function"))
                name = str(node.get("name") or kind)
                functions.append(
                    FunctionRegion(
                        name=name,
                        start=start,
                        body_start=opening + 1,
                        body_end=closing,
                        header=self.masked[start:opening],
                        contract=contract,
                    )
                )
        return tuple(functions) or self._find_functions()

    def _find_contracts(self) -> tuple[ContractRegion, ...]:
        contracts: list[ContractRegion] = []
        for match in CONTRACT_RE.finditer(self.masked):
            opening = self.masked.find("{", match.start(), match.end())
            closing = matching_brace(self.masked, opening)
            if closing is None:
                continue
            variables = _state_variables(self.masked, opening + 1, closing)
            contracts.append(
                ContractRegion(
                    name=match.group("name"),
                    kind=match.group("kind"),
                    start=match.start(),
                    body_start=opening + 1,
                    body_end=closing,
                    state_variables=frozenset(variables),
                )
            )
        return tuple(contracts)

    def _find_functions(self) -> tuple[FunctionRegion, ...]:
        functions: list[FunctionRegion] = []
        for match in FUNCTION_RE.finditer(self.masked):
            opening = self.masked.find("{", match.start(), match.end())
            closing = matching_brace(self.masked, opening)
            if closing is None:
                continue
            kind = match.group("kind")
            signature = match.group("signature")
            if kind == "function":
                name_match = re.match(r"\s*([A-Za-z_$][\w$]*)", signature)
                name = name_match.group(1) if name_match else "<anonymous>"
            else:
                name = kind
            contract = next(
                (
                    item
                    for item in self.contracts
                    if item.body_start <= match.start() <= item.body_end
                ),
                None,
            )
            functions.append(
                FunctionRegion(
                    name=name,
                    start=match.start(),
                    body_start=opening + 1,
                    body_end=closing,
                    header=self.masked[match.start() : opening],
                    contract=contract,
                )
            )
        return tuple(functions)


def _state_variables(masked: str, start: int, end: int) -> set[str]:
    """Extract likely contract-level variable names without requiring solc."""
    variables: set[str] = set()
    depth = 0
    statement_start = start
    ignored_prefixes = (
        "event ",
        "error ",
        "using ",
        "function ",
        "constructor",
        "modifier ",
        "struct ",
        "enum ",
        "type ",
    )
    for index in range(start, end):
        char = masked[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
            if depth == 0:
                statement_start = index + 1
        elif char == ";" and depth == 0:
            statement = masked[statement_start:index].strip()
            statement_start = index + 1
            if not statement or statement.startswith(ignored_prefixes):
                continue
            # Do not mistake the arrow in mapping(address => uint256) for an
            # initializer. A standalone assignment is the declaration boundary.
            declaration = re.split(r"=(?!=|>)", statement, maxsplit=1)[0].rstrip()
            names = re.findall(r"[A-Za-z_$][\w$]*", declaration)
            if names:
                candidate = names[-1]
                if candidate not in {"public", "private", "internal", "constant", "immutable"}:
                    variables.add(candidate)
    return variables


def _byte_boundaries(text: str) -> tuple[int, ...]:
    """Map UTF-8 byte offsets used by solc back to Python character offsets."""
    boundaries = [0]
    for character_index, character in enumerate(text):
        width = len(character.encode("utf-8"))
        boundaries.extend([character_index] * (width - 1))
        boundaries.append(character_index + 1)
    return tuple(boundaries)


def _byte_to_character(boundaries: tuple[int, ...], byte_offset: int) -> int:
    if byte_offset <= 0:
        return 0
    if byte_offset >= len(boundaries):
        return boundaries[-1]
    return boundaries[byte_offset]
