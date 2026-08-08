from __future__ import annotations

import json
from pathlib import Path
import re

from .models import Finding


class ProofGenerationError(RuntimeError):
    pass


SUPPORTED_PROOF_RULES = frozenset({"SOL005", "SOL007"})
PROOF_MANIFEST_SCHEMA_VERSION = "1.0"
TESTED_SOLC_VERSION = "0.8.25"


def generate_foundry_proofs(
    findings: list[Finding], output_directory: Path
) -> list[Path]:
    supported = [finding for finding in findings if _supports_proof(finding)]
    if not supported:
        return []
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ProofGenerationError(
            f"could not create proof directory {output_directory}: {exc}"
        ) from exc
    if not output_directory.is_dir():
        raise ProofGenerationError(
            f"proof output is not a directory: {output_directory}"
        )

    generated: list[Path] = []
    artifacts: dict[Path, str] = {}
    for finding in supported:
        filename = _proof_filename(finding)
        destination = output_directory / filename
        manifest_destination = output_directory / _manifest_filename(filename)
        artifacts[destination] = _proof_content(finding)
        artifacts[manifest_destination] = _proof_manifest(finding, filename)
        if destination not in generated:
            generated.append(destination)

    for destination, content in artifacts.items():
        if destination.exists():
            try:
                existing = destination.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ProofGenerationError(
                    f"could not inspect existing proof {destination}: {exc}"
                ) from exc
            if existing != content:
                raise ProofGenerationError(
                    f"refusing to overwrite modified proof: {destination}"
                )
    for destination, content in artifacts.items():
        if not destination.exists():
            try:
                with destination.open("x", encoding="utf-8") as handle:
                    handle.write(content)
            except OSError as exc:
                raise ProofGenerationError(
                    f"could not write proof {destination}: {exc}"
                ) from exc
    return generated


def _proof_filename(finding: Finding) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", finding.path.stem).strip("_") or "Contract"
    return f"{stem}_{finding.rule_id}_{finding.line}_{finding.fingerprint}.t.sol"


def _manifest_filename(proof_filename: str) -> str:
    stem = proof_filename.removesuffix(".t.sol")
    return f"{stem}.proof.json"


def _proof_manifest(finding: Finding, proof_filename: str) -> str:
    generated_tests = (
        [
            "test_SOL005_reentrancyPrimitive",
            "testFuzz_SOL005_transactionSequence",
            "test_SOL005_invariantReportsViolation",
        ]
        if finding.rule_id == "SOL005"
        else ["test_SOL007_packedEncodingCollision"]
    )
    contract_name = str(finding.metadata.get("entry_function") or "").split(
        ".", 1
    )[0] or None
    if finding.rule_id == "SOL005":
        project_profile: dict[str, object] = {
            "status": "configuration-required",
            "compiler": {
                "solc_version": None,
                "evm_version": None,
                "reason": "target compiler settings are not retained in the finding",
            },
            "chain": {
                "mode": None,
                "chain_id": None,
                "fork_url": None,
                "fork_block": None,
                "reason": "choose local deployment or a pinned authorized fork",
            },
            "constructor": {
                "contract": contract_name,
                "arguments": None,
                "reason": "constructor arguments cannot be inferred safely",
            },
            "setup": [
                {
                    "id": "deploy-target",
                    "required": True,
                    "value": None,
                },
                {
                    "id": "initialize-state",
                    "required": True,
                    "value": None,
                },
                {
                    "id": "fund-target-and-probe",
                    "required": True,
                    "value": None,
                },
                {
                    "id": "configure-actors-and-authorization",
                    "required": True,
                    "value": None,
                },
                {
                    "id": "encode-entry-and-reentry-calldata",
                    "required": True,
                    "value": None,
                },
                {
                    "id": "implement-protocol-invariant",
                    "required": True,
                    "value": None,
                },
            ],
        }
        artifact_kind = "reentrancy-probe-sequence-invariant"
    else:
        project_profile = {
            "status": "not-applicable",
            "reason": (
                "the generated proof demonstrates a standalone encoding primitive"
            ),
        }
        artifact_kind = "packed-encoding-primitive"

    payload = {
        "schema_version": PROOF_MANIFEST_SCHEMA_VERSION,
        "artifact_version": "1.0",
        "artifact_kind": artifact_kind,
        "proof_source": proof_filename,
        "finding": {
            "rule_id": finding.rule_id,
            "fingerprint": finding.fingerprint,
            "confidence": finding.confidence,
            "evidence": finding.metadata.get("evidence"),
            "source_path": str(finding.path),
            "line": finding.line,
            "column": finding.column,
        },
        "profiles": {
            "generated_tests": {
                "status": "runnable",
                "compiler": {
                    "solc_version": TESTED_SOLC_VERSION,
                    "pragma": "^0.8.20",
                    "offline": True,
                },
                "chain": {
                    "mode": "local",
                    "chain_id": None,
                    "fork_url": None,
                    "fork_block": None,
                },
                "constructor": {
                    "required": False,
                    "arguments": [],
                },
                "setup": [],
                "tests": generated_tests,
            },
            "project_probe": project_profile,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _supports_proof(finding: Finding) -> bool:
    if finding.rule_id == "SOL007":
        return True
    return bool(
        finding.rule_id == "SOL005"
        and finding.metadata.get("evidence")
        == "compiler-interprocedural-data-flow"
        and finding.metadata.get("entry_function")
        and finding.metadata.get("trace")
    )


def _proof_content(finding: Finding) -> str:
    if finding.rule_id == "SOL005":
        return _reentrancy_probe(finding)
    return _packed_encoding_proof(finding)


def _packed_encoding_proof(finding: Finding) -> str:
    contract_name = f"Holes_{finding.rule_id}_{finding.fingerprint}"
    source = str(finding.path).replace("\n", " ").replace("\r", " ")
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Generated by contract-holes from {source}:{finding.line}.
// This proves the encoding ambiguity. Protocol impact still depends on how the
// scanned contract uses the resulting hash.
contract {contract_name} {{
    function test_{finding.rule_id}_packedEncodingCollision() external pure {{
        bytes32 first = keccak256(abi.encodePacked("a", "bc"));
        bytes32 second = keccak256(abi.encodePacked("ab", "c"));

        require(first == second, "expected packed encoding collision");
        require(
            keccak256(abi.encode("a", "bc")) != keccak256(abi.encode("ab", "c")),
            "abi.encode should preserve value boundaries"
        );
    }}
}}
"""


def _reentrancy_probe(finding: Finding) -> str:
    contract_name = f"Holes_{finding.rule_id}_{finding.fingerprint}"
    source = _comment_text(finding.path)
    entry = _comment_text(finding.metadata.get("entry_function", "<unknown>"))
    interaction = _comment_text(
        finding.metadata.get("interaction_function", "<unknown>")
    )
    state_write = _comment_text(
        finding.metadata.get("state_write_function", "<unknown>")
    )
    state_variable = _comment_text(
        finding.metadata.get("state_variable", "<unknown>")
    )
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Generated by contract-holes from {source}:{finding.line}.
// Compiler evidence: entry {entry}; interaction {interaction};
// later write {state_write}.{state_variable}.
//
// The model test below proves only the reentrancy primitive. To probe the
// scanned protocol, deploy and configure {contract_name}_Probe.run with the
// target address, entry calldata, reentry calldata, and call values after
// reproducing the protocol's constructor, funding, authorization, and state.
// A successful callback or reentry is not by itself proof of protocol impact.
contract {contract_name}_Probe {{
    address public target;
    bytes public reentryCalldata;
    uint256 public reentryValue;

    bool public active;
    bool public attempted;
    bool public firstCallSucceeded;
    bool public reentrySucceeded;
    bytes public firstReturnData;
    bytes public reentryReturnData;

    function run(
        address target_,
        bytes calldata entryCalldata_,
        bytes calldata reentryCalldata_,
        uint256 entryValue_,
        uint256 reentryValue_
    ) external payable returns (bool, bytes memory) {{
        require(target_.code.length != 0, "target has no code");
        require(
            msg.value == entryValue_ + reentryValue_,
            "supply entry and reentry value"
        );

        target = target_;
        reentryCalldata = reentryCalldata_;
        reentryValue = reentryValue_;
        attempted = false;
        reentrySucceeded = false;
        delete reentryReturnData;
        active = true;

        (firstCallSucceeded, firstReturnData) = target_.call{{value: entryValue_}}(
            entryCalldata_
        );
        active = false;
        return (firstCallSucceeded, firstReturnData);
    }}

    receive() external payable {{
        _attemptReentry();
    }}

    fallback() external payable {{
        _attemptReentry();
    }}

    function _attemptReentry() internal {{
        if (!active || attempted) return;
        attempted = true;
        (reentrySucceeded, reentryReturnData) = target.call{{value: reentryValue}}(
            reentryCalldata
        );
    }}
}}

interface {contract_name}_Invariant {{
    function check(address target_)
        external
        view
        returns (bytes32 invariantId, bool holds, bytes memory details);
}}

// Generic sequence driver for project-specific Foundry tests. Every target call
// originates from this executor. Use a project adapter when distinct actors,
// time/blocks, token funding, or protocol-specific setup must be modelled.
contract {contract_name}_SequenceExecutor {{
    struct SequenceResult {{
        uint256 executed;
        uint256 succeeded;
        bytes32 digest;
        bool invariantHolds;
    }}

    error HolesInvariantViolation(
        bytes32 invariantId,
        uint256 afterStep,
        bytes32 detailsHash
    );

    event HolesInvariantAssertion(
        bytes32 indexed invariantId,
        uint256 indexed afterStep,
        bool holds,
        bytes32 detailsHash
    );

    uint256 public constant MAX_SEQUENCE_STEPS = 32;

    uint256 public lastExecuted;
    uint256 public lastSucceeded;
    bytes32 public lastResultDigest;
    bytes32 public lastInvariantId;
    bool public lastInvariantHolds = true;
    uint256 public lastInvariantStep;
    bytes32 public lastInvariantDetailsHash;

    function runSequence(
        address target_,
        bytes[] calldata calls_,
        uint256[] calldata values_,
        bool stopOnRevert_
    ) external payable returns (uint256 executed, uint256 succeeded, bytes32 digest) {{
        SequenceResult memory result = _runSequence(
            target_, calls_, values_, stopOnRevert_, address(0)
        );
        return (result.executed, result.succeeded, result.digest);
    }}

    function runSequenceWithInvariant(
        address target_,
        bytes[] calldata calls_,
        uint256[] calldata values_,
        bool stopOnRevert_,
        address invariant_
    )
        external
        payable
        returns (
            uint256 executed,
            uint256 succeeded,
            bytes32 digest,
            bool invariantHolds
        )
    {{
        require(invariant_.code.length != 0, "invariant has no code");
        SequenceResult memory result = _runSequence(
            target_, calls_, values_, stopOnRevert_, invariant_
        );
        return (
            result.executed,
            result.succeeded,
            result.digest,
            result.invariantHolds
        );
    }}

    function assertLastInvariant() external view {{
        if (!lastInvariantHolds) {{
            revert HolesInvariantViolation(
                lastInvariantId,
                lastInvariantStep,
                lastInvariantDetailsHash
            );
        }}
    }}

    function _runSequence(
        address target_,
        bytes[] calldata calls_,
        uint256[] calldata values_,
        bool stopOnRevert_,
        address invariant_
    )
        internal
        returns (SequenceResult memory result)
    {{
        require(target_.code.length != 0, "target has no code");
        require(calls_.length == values_.length, "sequence length mismatch");
        require(calls_.length <= MAX_SEQUENCE_STEPS, "sequence too long");

        uint256 requiredValue;
        for (uint256 index; index < values_.length; ++index) {{
            requiredValue += values_[index];
        }}
        require(msg.value == requiredValue, "supply exact sequence value");

        result.invariantHolds = true;
        lastInvariantId = bytes32(0);
        lastInvariantHolds = true;
        lastInvariantStep = 0;
        lastInvariantDetailsHash = bytes32(0);
        if (invariant_ != address(0)) {{
            result.invariantHolds = _checkInvariant(invariant_, target_, 0);
            if (!result.invariantHolds) {{
                lastExecuted = 0;
                lastSucceeded = 0;
                lastResultDigest = bytes32(0);
                return result;
            }}
        }}

        result.digest = keccak256(abi.encode(target_, calls_.length));
        for (uint256 index; index < calls_.length; ++index) {{
            (bool success, bytes32 nextDigest) = _executeStep(
                target_, calls_[index], values_[index], result.digest, index
            );
            result.digest = nextDigest;
            ++result.executed;
            if (success) ++result.succeeded;
            if (invariant_ != address(0)) {{
                result.invariantHolds = _checkInvariant(
                    invariant_, target_, index + 1
                );
                if (!result.invariantHolds) break;
            }}
            if (!success && stopOnRevert_) break;
        }}

        lastExecuted = result.executed;
        lastSucceeded = result.succeeded;
        lastResultDigest = result.digest;
    }}

    function _executeStep(
        address target_,
        bytes calldata call_,
        uint256 value_,
        bytes32 previousDigest_,
        uint256 index_
    ) internal returns (bool success, bytes32 digest) {{
        bytes memory returnData;
        (success, returnData) = target_.call{{value: value_}}(call_);
        digest = keccak256(
            abi.encode(
                previousDigest_, index_, success, keccak256(returnData)
            )
        );
    }}

    function _checkInvariant(
        address invariant_,
        address target_,
        uint256 afterStep_
    ) internal returns (bool holds) {{
        bytes32 invariantId;
        bytes32 detailsHash;
        try {contract_name}_Invariant(invariant_).check(target_) returns (
            bytes32 returnedId,
            bool returnedHolds,
            bytes memory details
        ) {{
            invariantId = returnedId;
            holds = returnedHolds;
            detailsHash = keccak256(details);
        }} catch (bytes memory reason) {{
            invariantId = keccak256("HOLES_INVARIANT_ADAPTER_REVERT");
            holds = false;
            detailsHash = keccak256(reason);
        }}

        lastInvariantId = invariantId;
        lastInvariantHolds = holds;
        lastInvariantStep = afterStep_;
        lastInvariantDetailsHash = detailsHash;
        emit HolesInvariantAssertion(
            invariantId, afterStep_, holds, detailsHash
        );
    }}

    receive() external payable {{}}
}}

contract {contract_name}_VulnerableModel {{
    uint256 public credit = 1;
    uint256 public withdrawals;

    function withdraw() external {{
        require(credit != 0, "no credit");
        withdrawals += 1;
        (bool callbackSucceeded, ) = msg.sender.call("");
        require(callbackSucceeded, "callback failed");
        credit = 0;
    }}

    function reset(uint256 nextCredit) external {{
        credit = nextCredit;
    }}
}}

contract {contract_name}_CreditBoundInvariant is {contract_name}_Invariant {{
    bytes32 public constant INVARIANT_ID = keccak256("MODEL_CREDIT_BOUND");
    uint256 public immutable maximumCredit;

    constructor(uint256 maximumCredit_) {{
        maximumCredit = maximumCredit_;
    }}

    function check(address target_)
        external
        view
        returns (bytes32 invariantId, bool holds, bytes memory details)
    {{
        uint256 credit = {contract_name}_VulnerableModel(target_).credit();
        return (
            INVARIANT_ID,
            credit <= maximumCredit,
            abi.encode(credit, maximumCredit)
        );
    }}
}}

contract {contract_name} {{
    function test_SOL005_reentrancyPrimitive() external {{
        {contract_name}_Probe probe = new {contract_name}_Probe();
        {contract_name}_VulnerableModel model =
            new {contract_name}_VulnerableModel();
        bytes memory payload = abi.encodeWithSignature("withdraw()");

        probe.run(address(model), payload, payload, 0, 0);

        require(probe.firstCallSucceeded(), "entry call should succeed");
        require(probe.attempted(), "target should invoke the probe");
        require(probe.reentrySucceeded(), "reentrant call should succeed");
        require(model.withdrawals() == 2, "expected two nested executions");
    }}

    function testFuzz_SOL005_transactionSequence(bytes calldata commands) external {{
        {contract_name}_SequenceExecutor executor =
            new {contract_name}_SequenceExecutor();
        {contract_name}_VulnerableModel model =
            new {contract_name}_VulnerableModel();
        {contract_name}_CreditBoundInvariant invariant =
            new {contract_name}_CreditBoundInvariant(type(uint8).max);
        uint256 steps = commands.length;
        if (steps > executor.MAX_SEQUENCE_STEPS()) {{
            steps = executor.MAX_SEQUENCE_STEPS();
        }}
        bytes[] memory calls = new bytes[](steps);
        uint256[] memory values = new uint256[](steps);

        for (uint256 index; index < steps; ++index) {{
            uint8 command = uint8(commands[index]);
            calls[index] = command % 2 == 0
                ? abi.encodeWithSignature("reset(uint256)", uint256(command) + 1)
                : abi.encodeWithSignature("withdraw()");
        }}

        (uint256 executed, , , bool invariantHolds) =
            executor.runSequenceWithInvariant(
                address(model), calls, values, false, address(invariant)
            );
        require(invariantHolds, "model credit bound should hold");
        executor.assertLastInvariant();
        require(executed == steps, "executor should process every command");
    }}

    function test_SOL005_invariantReportsViolation() external {{
        {contract_name}_SequenceExecutor executor =
            new {contract_name}_SequenceExecutor();
        {contract_name}_VulnerableModel model =
            new {contract_name}_VulnerableModel();
        {contract_name}_CreditBoundInvariant invariant =
            new {contract_name}_CreditBoundInvariant(1);
        bytes[] memory calls = new bytes[](1);
        calls[0] = abi.encodeWithSignature("reset(uint256)", 2);
        uint256[] memory values = new uint256[](1);

        (, , , bool invariantHolds) = executor.runSequenceWithInvariant(
            address(model), calls, values, false, address(invariant)
        );
        require(!invariantHolds, "credit bound should fail");
        require(executor.lastInvariantStep() == 1, "expected failing step");
        require(
            executor.lastInvariantId() == invariant.INVARIANT_ID(),
            "expected stable invariant id"
        );

        bool assertionReverted;
        try executor.assertLastInvariant() {{}}
        catch {{
            assertionReverted = true;
        }}
        require(assertionReverted, "assertion should expose the violation");
    }}
}}
"""


def _comment_text(value: object) -> str:
    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("*/", "* /")
    )
