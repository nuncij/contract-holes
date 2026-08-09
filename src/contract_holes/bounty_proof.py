from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Mapping

from .bounty_candidates import (
    BountyCandidateError,
    CandidateContext,
    load_candidate_context,
)
from .bounty_io import (
    BountyWorkspaceError,
    load_private_json,
    payload_sha256,
    redact_sensitive_text,
    write_private_json_new_or_identical,
)
from .bounty_scope import BountyScopeError, validate_profile_source
from .models import Finding, Severity
from .proof_runner import ProofRunnerError, run_foundry_proofs
from .proofs import ProofGenerationError, generate_foundry_proofs


class BountyProofError(RuntimeError):
    pass


PROOF_SCHEMA_VERSION = "1.0"
PROOF_RESULT_SCHEMA_VERSION = "1.0"
PROOF_ROOT = "proofs"
PROOF_MANIFEST_FILENAME = "bounty-proof-manifest.json"
PROOF_RESULT_FILENAME = "proof-result.json"
ALLOWED_REQUIREMENTS = frozenset(
    {
        "actors",
        "balances",
        "calldata",
        "constructor",
        "deployment",
        "invariant",
        "oracle",
        "timing",
    }
)


@dataclass(frozen=True, slots=True)
class BountyProofResult:
    directory: Path
    manifest: dict[str, object]
    execution: dict[str, object] | None


def create_bounty_proof(
    workspace: Path | str,
    candidate_id: str,
    *,
    requirements: Mapping[str, str] | None = None,
    impact_assertion: str | None = None,
    run: bool = False,
    timeout_seconds: float = 60.0,
) -> BountyProofResult:
    try:
        context = load_candidate_context(workspace, candidate_id)
        identity = validate_profile_source(context.profile)
    except (BountyCandidateError, BountyScopeError) as exc:
        raise BountyProofError(str(exc)) from exc
    if not context.candidate.get("active"):
        raise BountyProofError("cannot create a proof for an inactive candidate")
    if identity.source_set_sha256 != context.source_manifest.get("source_set_sha256"):
        raise BountyProofError("current source identity does not match source manifest")
    normalized_requirements = _requirements(requirements or {})
    normalized_impact = _safe_optional_text(impact_assertion, "impact assertion")
    finding = _finding(context)

    with tempfile.TemporaryDirectory(prefix="contract-holes-bounty-proof-build-") as raw:
        staging = Path(raw)
        try:
            generated = generate_foundry_proofs([finding], staging)
        except ProofGenerationError as exc:
            raise BountyProofError(str(exc)) from exc
        generated_files = _generated_file_entries(staging)
        generator_status = "generated" if generated else "unsupported"
        manifest = _proof_manifest(
            context,
            finding,
            generator_status=generator_status,
            generated_files=generated_files,
            requirements=normalized_requirements,
            impact_assertion=normalized_impact,
        )
        proof_sha256 = str(manifest["proof_sha256"])
        destination = (
            context.profile.workspace / PROOF_ROOT / candidate_id / proof_sha256
        )
        _install_proof_directory(staging, destination, manifest)

    execution: dict[str, object] | None = None
    if run:
        execution = run_bounty_proof(
            workspace,
            candidate_id,
            proof_sha256,
            timeout_seconds=timeout_seconds,
        )
    return BountyProofResult(
        directory=destination,
        manifest=manifest,
        execution=execution,
    )


def run_bounty_proof(
    workspace: Path | str,
    candidate_id: str,
    proof_sha256: str,
    *,
    timeout_seconds: float = 60.0,
) -> dict[str, object]:
    context = _context(workspace, candidate_id)
    directory, manifest = load_bounty_proof(context, proof_sha256)
    generator = manifest.get("generator")
    status = generator.get("status") if isinstance(generator, dict) else None
    if status != "generated":
        execution: dict[str, object] = {
            "schema_version": PROOF_RESULT_SCHEMA_VERSION,
            "proof_sha256": proof_sha256,
            "status": "unsupported",
            "diagnostic": "candidate has no automatic Contract Holes proof generator",
            "summary": {"all_passed": False, "artifacts": 0, "unsupported": 1},
            "results": [],
        }
    else:
        try:
            raw = run_foundry_proofs(
                directory,
                timeout_seconds=timeout_seconds,
                allow_downloads=False,
            )
        except ProofRunnerError as exc:
            raise BountyProofError(str(exc)) from exc
        execution = _normalized_execution(raw, context, proof_sha256)
    execution["result_sha256"] = payload_sha256(execution)
    try:
        write_private_json_new_or_identical(
            directory / PROOF_RESULT_FILENAME, execution
        )
    except BountyWorkspaceError as exc:
        raise BountyProofError(str(exc)) from exc
    return execution


def load_bounty_proof(
    context: CandidateContext,
    proof_sha256: str,
) -> tuple[Path, dict[str, object]]:
    if not isinstance(proof_sha256, str) or len(proof_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in proof_sha256
    ):
        raise BountyProofError("proof SHA-256 is invalid")
    directory = (
        context.profile.workspace / PROOF_ROOT / str(context.candidate["candidate_id"]) / proof_sha256
    )
    if directory.is_symlink() or not directory.is_dir():
        raise BountyProofError(f"proof directory does not exist: {proof_sha256}")
    try:
        manifest = load_private_json(directory / PROOF_MANIFEST_FILENAME)
    except BountyWorkspaceError as exc:
        raise BountyProofError(str(exc)) from exc
    _validate_proof_manifest(context, manifest, proof_sha256)
    for entry in manifest.get("generated_files", []):
        if not isinstance(entry, dict):
            raise BountyProofError("proof generated_files entry is invalid")
        name = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(name, str) or Path(name).name != name or not isinstance(digest, str):
            raise BountyProofError("proof generated file identity is invalid")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise BountyProofError(f"proof generated file is missing: {name}")
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise BountyProofError(f"could not read proof generated file {name}: {exc}") from exc
        if actual != digest:
            raise BountyProofError(f"proof generated file hash changed: {name}")
    return directory, manifest


def load_bounty_proof_result(
    context: CandidateContext, proof_sha256: str
) -> dict[str, object] | None:
    directory, _ = load_bounty_proof(context, proof_sha256)
    path = directory / PROOF_RESULT_FILENAME
    if not path.exists():
        return None
    try:
        result = load_private_json(path)
    except BountyWorkspaceError as exc:
        raise BountyProofError(str(exc)) from exc
    _validate_self_digest(result, "result_sha256", "proof result")
    if result.get("proof_sha256") != proof_sha256:
        raise BountyProofError("proof result does not match proof manifest")
    return result


def parse_requirements(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        name, separator, content = value.partition("=")
        if not separator or not name or name in result:
            raise BountyProofError(
                "requirements must be unique NAME=VALUE entries"
            )
        result[name] = content
    return _requirements(result)


def _proof_manifest(
    context: CandidateContext,
    finding: Finding,
    *,
    generator_status: str,
    generated_files: list[dict[str, object]],
    requirements: dict[str, str],
    impact_assertion: str | None,
) -> dict[str, object]:
    candidates_digest = context.candidates_record.get("candidates_sha256")
    observation = context.candidate.get("observation")
    observation_digest = (
        observation.get("observation_sha256") if isinstance(observation, dict) else None
    )
    payload: dict[str, object] = {
        "schema_version": PROOF_SCHEMA_VERSION,
        "candidate_id": context.candidate["candidate_id"],
        "profile_sha256": context.profile.digest,
        "source_manifest_sha256": context.source_manifest["manifest_sha256"],
        "candidates_sha256": candidates_digest,
        "observation_sha256": observation_digest,
        "finding": {
            "rule_id": finding.rule_id,
            "fingerprint": finding.fingerprint,
            "path": str(finding.path),
            "line": finding.line,
            "confidence": finding.confidence,
        },
        "execution_policy": {
            "chain_mode": "local",
            "offline": True,
            "remote_rpc": None,
            "wallet": None,
            "isolation": "temporary-foundry-project-per-artifact",
        },
        "compiler": {
            "offline": True,
            "configuration": "generated-proof-manifest-bound",
            "requirement_manifests": sorted(
                str(entry["path"])
                for entry in generated_files
                if str(entry["path"]).endswith(".proof.json")
            ),
        },
        "generator": {
            "status": generator_status,
            "meaning": (
                "generated tests demonstrate only a vulnerability primitive; "
                "protocol impact requires a separate reviewed assertion"
            ),
        },
        "requirements": {
            name: {
                "status": "supplied" if name in requirements else "unknown",
                "value": requirements.get(name),
            }
            for name in sorted(ALLOWED_REQUIREMENTS)
        },
        "impact_assertion": {
            "status": "supplied" if impact_assertion is not None else "unknown",
            "value": impact_assertion,
        },
        "generated_files": generated_files,
    }
    payload["proof_sha256"] = payload_sha256(payload)
    return payload


def _finding(context: CandidateContext) -> Finding:
    observation = context.candidate.get("observation")
    finding = observation.get("finding") if isinstance(observation, dict) else None
    if not isinstance(finding, dict):
        raise BountyProofError("candidate contains no finding observation")
    try:
        return Finding(
            rule_id=str(finding["rule_id"]),
            severity=Severity.parse(str(finding["severity"])),
            title=str(finding["title"]),
            message=str(finding["message"]),
            path=Path(str(finding["path"])),
            line=int(finding["line"]),
            column=int(finding["column"]),
            excerpt=str(finding["excerpt"]),
            recommendation=str(finding["recommendation"]),
            confidence=str(finding["confidence"]),
            end_line=(int(finding["end_line"]) if finding.get("end_line") is not None else None),
            metadata=(dict(finding["metadata"]) if isinstance(finding.get("metadata"), dict) else {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise BountyProofError(f"candidate finding is invalid: {exc}") from exc


def _requirements(values: Mapping[str, str]) -> dict[str, str]:
    unknown = set(values) - ALLOWED_REQUIREMENTS
    if unknown:
        raise BountyProofError(
            "unknown proof requirement: " + ", ".join(sorted(unknown))
        )
    result: dict[str, str] = {}
    for name, value in values.items():
        safe = _safe_optional_text(value, f"requirement {name}")
        if safe is None:
            raise BountyProofError(f"proof requirement {name} must not be empty")
        result[name] = safe
    return result


def _safe_optional_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyProofError(f"{label} must be a non-empty string")
    if len(value) > 20_000:
        raise BountyProofError(f"{label} is too long")
    if redact_sensitive_text(value) != value:
        raise BountyProofError(f"{label} appears to contain a credential or secret")
    return value


def _generated_file_entries(directory: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            raise BountyProofError(f"unexpected generated proof path: {path.name}")
        data = path.read_bytes()
        entries.append(
            {"path": path.name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        )
    return entries


def _install_proof_directory(
    staging: Path,
    destination: Path,
    manifest: dict[str, object],
) -> None:
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        parent.chmod(0o700)
    if destination.exists():
        context = _context_from_manifest_path(destination, manifest)
        _, existing = load_bounty_proof(context, str(manifest["proof_sha256"]))
        if existing != manifest:
            raise BountyProofError("existing proof manifest differs from requested proof")
        return
    temporary = Path(tempfile.mkdtemp(prefix=".proof-", dir=parent))
    try:
        if os.name == "posix":
            temporary.chmod(0o700)
        for entry in manifest["generated_files"]:
            assert isinstance(entry, dict)
            name = str(entry["path"])
            target = temporary / name
            shutil.copyfile(staging / name, target)
            if os.name == "posix":
                target.chmod(0o600)
        write_private_json_new_or_identical(
            temporary / PROOF_MANIFEST_FILENAME, manifest
        )
        temporary.rename(destination)
    except (OSError, BountyWorkspaceError) as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        raise BountyProofError(f"could not install bounty proof: {exc}") from exc


def _context_from_manifest_path(
    destination: Path, manifest: dict[str, object]
) -> CandidateContext:
    workspace = destination.parents[2]
    return _context(workspace, str(manifest["candidate_id"]))


def _context(workspace: Path | str, candidate_id: str) -> CandidateContext:
    try:
        return load_candidate_context(workspace, candidate_id)
    except BountyCandidateError as exc:
        raise BountyProofError(str(exc)) from exc


def _validate_proof_manifest(
    context: CandidateContext,
    manifest: dict[str, object],
    proof_sha256: str,
) -> None:
    _validate_self_digest(manifest, "proof_sha256", "proof manifest")
    if manifest.get("schema_version") != PROOF_SCHEMA_VERSION:
        raise BountyProofError("unsupported bounty proof schema")
    expected = {
        "candidate_id": context.candidate["candidate_id"],
        "profile_sha256": context.profile.digest,
        "source_manifest_sha256": context.source_manifest["manifest_sha256"],
        "candidates_sha256": context.candidates_record["candidates_sha256"],
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise BountyProofError(f"proof manifest {field} is stale or mismatched")
    if manifest.get("proof_sha256") != proof_sha256:
        raise BountyProofError("proof directory name does not match proof manifest")


def _validate_self_digest(payload: dict[str, object], field: str, label: str) -> None:
    supplied = payload.get(field)
    material = dict(payload)
    material.pop(field, None)
    if not isinstance(supplied, str) or supplied != payload_sha256(material):
        raise BountyProofError(f"{label} integrity digest does not match")


def _normalized_execution(
    raw: dict[str, object], context: CandidateContext, proof_sha256: str
) -> dict[str, object]:
    normalized_results: list[dict[str, object]] = []
    for raw_result in raw.get("results", []):
        if not isinstance(raw_result, dict):
            continue
        normalized_results.append(
            {
                key: redact_sensitive_text(
                    str(value),
                    private_paths=(context.profile.workspace, context.profile.source_root),
                )
                if key in {"stdout", "stderr", "diagnostic"} and value is not None
                else value
                for key, value in raw_result.items()
                if key != "duration_seconds"
            }
        )
    summary = raw.get("summary")
    all_passed = isinstance(summary, dict) and summary.get("all_passed") is True
    return {
        "schema_version": PROOF_RESULT_SCHEMA_VERSION,
        "proof_sha256": proof_sha256,
        "status": "passed" if all_passed else "failed",
        "runner_version": raw.get("runner_version"),
        "settings": {
            "offline": True,
            "allow_downloads": False,
            "isolation": "temporary-foundry-project-per-artifact",
        },
        "summary": summary,
        "results": normalized_results,
    }
