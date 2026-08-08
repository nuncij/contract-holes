from __future__ import annotations

from dataclasses import dataclass
import json

from .rules import DEFAULT_RULES


class CatalogError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuleGuidance:
    analysis_mode: str
    vulnerable_example: str
    safer_example: str
    manual_review: str
    references: tuple[tuple[str, str], ...]


SOLIDITY_SECURITY = (
    "Solidity security considerations",
    "https://docs.soliditylang.org/en/latest/security-considerations.html",
)


GUIDANCE: dict[str, RuleGuidance] = {
    "SOL001": RuleGuidance(
        "source",
        "require(tx.origin == owner);",
        "require(msg.sender == owner);",
        "Confirm the value is actually used as an authorization decision.",
        ((
            "Solidity: tx.origin",
            "https://docs.soliditylang.org/en/latest/"
            "security-considerations.html#tx-origin",
        ),),
    ),
    "SOL002": RuleGuidance(
        "compiler when available; source fallback",
        "(bool ok, ) = target.call(data);",
        '(bool ok, ) = target.call(data); require(ok, "call failed");',
        "Assigned success values and deliberate best-effort calls need review.",
        (SOLIDITY_SECURITY,),
    ),
    "SOL003": RuleGuidance(
        "source",
        "implementation.delegatecall(data);",
        "require(allowed[implementation]); implementation.delegatecall(data);",
        "Validate target trust, proxy standard, storage slots, and call reachability.",
        (("ERC-1967 proxy slots", "https://eips.ethereum.org/EIPS/eip-1967"),),
    ),
    "SOL004": RuleGuidance(
        "source",
        "selfdestruct(payable(owner));",
        "disabled = true; // preserve explicit lifecycle state",
        "Impact depends on the EVM revision, deployment pattern, and call path.",
        (("EIP-6780 SELFDESTRUCT", "https://eips.ethereum.org/EIPS/eip-6780"),),
    ),
    "SOL005": RuleGuidance(
        "compiler interprocedural flow; source fallback",
        "recipient.call{value: amount}(\"\"); balances[msg.sender] = 0;",
        "balances[msg.sender] = 0; recipient.call{value: amount}(\"\");",
        "Confirm callback reachability, shared state, guards, and economic impact.",
        ((
            "Solidity: reentrancy",
            "https://docs.soliditylang.org/en/latest/"
            "security-considerations.html#reentrancy",
        ),),
    ),
    "SOL006": RuleGuidance(
        "source",
        "uint256(keccak256(abi.encode(block.timestamp, block.prevrandao)));",
        "requestCommitRevealOrVerifiableRandomness();",
        "Trace the value to allocation, selection, or other value-bearing behavior.",
        (SOLIDITY_SECURITY,),
    ),
    "SOL007": RuleGuidance(
        "compiler AST plus primitive proof",
        "keccak256(abi.encodePacked(firstDynamic, secondDynamic));",
        "keccak256(abi.encode(firstDynamic, secondDynamic));",
        "Trace the digest to signatures, authorization, identifiers, or accounting.",
        ((
            "Solidity ABI packed mode",
            "https://docs.soliditylang.org/en/latest/"
            "abi-spec.html#non-standard-packed-mode",
        ),),
    ),
    "SOL008": RuleGuidance(
        "compiler interprocedural taint",
        "function callAny(address target, bytes calldata data) external "
        "{ target.call(data); }",
        "require(allowed[target]); target.call(data);",
        "Confirm validation dominance and mutable target provenance across "
        "transactions.",
        (SOLIDITY_SECURITY,),
    ),
    "SOL009": RuleGuidance(
        "compiler authorization reachability",
        "function setOwner(address next) external { owner = next; }",
        "function setOwner(address next) external onlyOwner { owner = next; }",
        "Custom authorization frameworks and protocol-specific privileged state "
        "need review.",
        ((
            "Solidity: restricting access",
            "https://docs.soliditylang.org/en/latest/"
            "common-patterns.html#restricting-access",
        ),),
    ),
    "SOL010": RuleGuidance(
        "compiler recovery-to-action flow",
        "address signer = ecrecover(digest, v, r, s); execute(action);",
        "consumeNonce(); require(block.timestamp <= deadline); verifyEIP712Domain();",
        "Review nonce invalidation, deadlines, domains, zero recovery, and "
        "malleability.",
        (("EIP-712 typed data", "https://eips.ethereum.org/EIPS/eip-712"),),
    ),
    "SOL011": RuleGuidance(
        "compiler initializer, proxy, and versioned-layout analysis",
        "function initialize(address owner_) external { owner = owner_; }",
        "function initialize(address owner_) external initializer { owner = owner_; }",
        "Perform byte-accurate storage review for structs, packing, diamonds, "
        "and custom slots.",
        (("ERC-1967 proxy slots", "https://eips.ethereum.org/EIPS/eip-1967"),),
    ),
    "SOL012": RuleGuidance(
        "compiler typed-call and amount-origin flow",
        "token.transfer(to, amount); credits[user] += amount;",
        "require(token.transfer(to, amount)); creditObservedBalanceDelta();",
        "Review wrappers, token allowlists, fee-on-transfer, rebasing, and recipients.",
        (("ERC-20 token standard", "https://eips.ethereum.org/EIPS/eip-20"),),
    ),
    "SOL013": RuleGuidance(
        "compiler market-integrity flow",
        "(, int256 price,,,) = feed.latestRoundData(); "
        "swap(amount, 0, block.timestamp);",
        "checkUpdatedAtAndHeartbeat(); useTwap(); swap(amount, minOut, deadline);",
        "Review round completeness, heartbeat, TWAP window/liquidity, and "
        "router semantics.",
        ((
            "Chainlink data feeds API",
            "https://docs.chain.link/data-feeds/api-reference",
        ),),
    ),
}


def catalog_payload(rule_id: str | None = None) -> dict[str, object]:
    entries = [_entry(rule) for rule in DEFAULT_RULES]
    if rule_id is not None:
        normalized = rule_id.upper()
        entries = [entry for entry in entries if entry["rule_id"] == normalized]
        if not entries:
            raise CatalogError(f"unknown rule ID: {rule_id}")
    return {
        "schema_version": "1.0",
        "catalog_version": "1.0",
        "rule_count": len(entries),
        "rules": entries,
    }


def text_catalog(payload: dict[str, object]) -> str:
    blocks: list[str] = []
    for entry in payload["rules"]:
        references = "\n".join(
            f"  - {reference['title']}: {reference['url']}"
            for reference in entry["references"]
        )
        blocks.append(
            "\n".join(
                [
                    f"{entry['rule_id']} "
                    f"[{str(entry['severity']).upper()}] — {entry['title']}",
                    f"  Confidence: {entry['confidence']}",
                    f"  Analysis: {entry['analysis_mode']}",
                    f"  Signal: {entry['description']}",
                    f"  Vulnerable: {entry['vulnerable_example']}",
                    f"  Safer: {entry['safer_example']}",
                    f"  Remediation: {entry['recommendation']}",
                    f"  Manual review: {entry['manual_review']}",
                    "  References:",
                    references,
                ]
            )
        )
    return "\n\n".join(blocks)


def json_catalog(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _entry(rule) -> dict[str, object]:
    info = rule.info
    guidance = GUIDANCE.get(info.rule_id)
    if guidance is None:
        raise CatalogError(f"catalog guidance is missing for {info.rule_id}")
    return {
        "rule_id": info.rule_id,
        "severity": str(info.severity),
        "confidence": info.confidence,
        "title": info.title,
        "description": info.description,
        "recommendation": info.recommendation,
        "analysis_mode": guidance.analysis_mode,
        "vulnerable_example": guidance.vulnerable_example,
        "safer_example": guidance.safer_example,
        "manual_review": guidance.manual_review,
        "references": [
            {"title": title, "url": url} for title, url in guidance.references
        ],
    }
