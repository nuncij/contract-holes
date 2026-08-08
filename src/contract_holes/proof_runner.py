from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


class ProofRunnerError(RuntimeError):
    pass


def run_foundry_proofs(
    directory: Path | str,
    *,
    timeout_seconds: float = 60.0,
    allow_downloads: bool = False,
    forge_executable: str = "forge",
) -> dict[str, object]:
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ProofRunnerError(f"proof directory does not exist: {root}")
    if (
        isinstance(timeout_seconds, bool)
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ProofRunnerError("proof timeout must be a positive finite number")
    forge = shutil.which(forge_executable)
    if forge is None:
        raise ProofRunnerError(
            f"Foundry executable not found: {forge_executable}; install forge first"
        )

    manifests = sorted(root.glob("*.proof.json"), key=lambda path: path.name)
    if not manifests:
        raise ProofRunnerError(f"no .proof.json manifests found in {root}")

    results = [
        _run_manifest(
            root,
            manifest,
            forge=forge,
            timeout_seconds=timeout_seconds,
            allow_downloads=allow_downloads,
        )
        for manifest in manifests
    ]
    statuses = Counter(str(result["status"]) for result in results)
    return {
        "schema_version": "1.0",
        "runner_version": "1.0",
        "proof_directory": str(root),
        "settings": {
            "timeout_seconds": timeout_seconds,
            "allow_downloads": allow_downloads,
            "isolation": "temporary-foundry-project-per-artifact",
        },
        "summary": {
            "artifacts": len(results),
            "passed": statuses["passed"],
            "failed": statuses["failed"],
            "timed_out": statuses["timed_out"],
            "unsupported": statuses["unsupported"],
            "all_passed": statuses["passed"] == len(results),
        },
        "results": results,
    }


def proof_runner_exit_status(payload: dict[str, object]) -> int:
    summary = payload.get("summary")
    return 0 if isinstance(summary, dict) and summary.get("all_passed") else 1


def _run_manifest(
    root: Path,
    manifest_path: Path,
    *,
    forge: str,
    timeout_seconds: float,
    allow_downloads: bool,
) -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    source_name = manifest.get("proof_source")
    if not isinstance(source_name, str) or Path(source_name).name != source_name:
        raise ProofRunnerError(
            f"{manifest_path.name}: proof_source must be a local filename"
        )
    source_path = root / source_name
    if not source_path.is_file():
        raise ProofRunnerError(
            f"{manifest_path.name}: proof source does not exist: {source_name}"
        )
    expected_hash = manifest.get("proof_sha256")
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise ProofRunnerError(
            f"{manifest_path.name}: could not read proof source: {exc}"
        ) from exc
    actual_hash = hashlib.sha256(source_bytes).hexdigest()
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        raise ProofRunnerError(
            f"{manifest_path.name}: proof source hash does not match manifest"
        )

    finding = manifest.get("finding")
    profiles = manifest.get("profiles")
    generated = profiles.get("generated_tests") if isinstance(profiles, dict) else None
    base = {
        "manifest": manifest_path.name,
        "proof_source": source_name,
        "rule_id": finding.get("rule_id") if isinstance(finding, dict) else None,
        "fingerprint": (
            finding.get("fingerprint") if isinstance(finding, dict) else None
        ),
        "compiler": (
            generated.get("compiler") if isinstance(generated, dict) else None
        ),
    }
    unsupported = _unsupported_reason(generated)
    if unsupported is not None:
        return {
            **base,
            "status": "unsupported",
            "duration_seconds": 0.0,
            "exit_code": None,
            "diagnostic": unsupported,
            "stdout": "",
            "stderr": "",
        }

    compiler = generated["compiler"]
    solc_version = str(compiler["solc_version"])
    with tempfile.TemporaryDirectory(prefix="contract-holes-proof-") as temporary:
        isolated_root = Path(temporary)
        test_directory = isolated_root / "test"
        test_directory.mkdir()
        (isolated_root / "src").mkdir()
        shutil.copyfile(source_path, test_directory / source_name)
        (isolated_root / "foundry.toml").write_text(
            _foundry_configuration(solc_version), encoding="utf-8"
        )
        command = [forge, "test", "--root", str(isolated_root)]
        if not allow_downloads:
            command.append("--offline")
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=isolated_root,
                env=_runner_environment(),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = time.perf_counter() - started
            status = "passed" if completed.returncode == 0 else "failed"
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
            diagnostic = None if status == "passed" else "forge test failed"
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            status = "timed_out"
            stdout = _timeout_text(exc.stdout)
            stderr = _timeout_text(exc.stderr)
            exit_code = None
            diagnostic = f"forge test exceeded {timeout_seconds:g} seconds"
        marker = str(isolated_root)
        return {
            **base,
            "status": status,
            "duration_seconds": round(duration, 6),
            "exit_code": exit_code,
            "diagnostic": diagnostic,
            "stdout": stdout.replace(marker, "<isolated-project>"),
            "stderr": stderr.replace(marker, "<isolated-project>"),
        }


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProofRunnerError(
            f"could not read proof manifest {path.name}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ProofRunnerError(f"{path.name}: manifest root must be an object")
    if payload.get("schema_version") != "1.0":
        raise ProofRunnerError(f"{path.name}: unsupported proof manifest schema")
    return payload


def _unsupported_reason(generated: object) -> str | None:
    if not isinstance(generated, dict):
        return "manifest contains no generated_tests profile"
    if generated.get("status") != "runnable":
        return f"generated_tests status is {generated.get('status')!r}"
    compiler = generated.get("compiler")
    if not isinstance(compiler, dict) or not compiler.get("solc_version"):
        return "generated_tests profile contains no solc_version"
    chain = generated.get("chain")
    if not isinstance(chain, dict) or chain.get("mode") != "local":
        return "runner currently supports only local generated tests"
    return None


def _foundry_configuration(solc_version: str) -> str:
    return f'''[profile.default]
src = "src"
test = "test"
libs = []
solc_version = "{solc_version}"
'''


def _runner_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith(("FOUNDRY_", "DAPP_")) or key in {
            "ETH_RPC_URL",
            "ETHERSCAN_API_KEY",
        }:
            environment.pop(key, None)
    return environment


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
