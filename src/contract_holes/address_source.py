from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


ETHERSCAN_V2_ENDPOINT = "https://api.etherscan.io/v2/api"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
ADDRESS_PATTERN = re.compile(r"0x[0-9a-fA-F]{40}\Z")


class AddressSourceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VerifiedSource:
    chain_id: str
    address: str
    sources: tuple[tuple[str, str], ...]
    metadata: dict[str, object]
    retrieved_at: str
    compiler_input: dict[str, object] | None = None


def fetch_verified_source(
    chain_id: int | str,
    address: str,
    api_key: str,
    *,
    timeout_seconds: float = 30.0,
    opener: Callable[..., object] | None = None,
    now: Callable[[], datetime] | None = None,
) -> VerifiedSource:
    normalized_chain = _chain_id(chain_id)
    normalized_address = _address(address)
    if not isinstance(api_key, str) or not api_key.strip():
        raise AddressSourceError("Etherscan API key is empty")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise AddressSourceError("fetch timeout must be a positive finite number")

    query = urlencode(
        {
            "chainid": normalized_chain,
            "module": "contract",
            "action": "getsourcecode",
            "address": normalized_address,
            "apikey": api_key,
        }
    )
    request_url = f"{ETHERSCAN_V2_ENDPOINT}?{query}"
    open_request = opener or urlopen
    try:
        with open_request(request_url, timeout=timeout_seconds) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise AddressSourceError(
            f"Etherscan returned HTTP {exc.code} while fetching verified source"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        detail = str(reason) if reason else exc.__class__.__name__
        raise AddressSourceError(
            f"could not fetch verified source from Etherscan: {detail}"
        ) from exc
    if not isinstance(body, bytes):
        raise AddressSourceError("Etherscan response was not bytes")
    if len(body) > MAX_RESPONSE_BYTES:
        raise AddressSourceError(
            f"Etherscan response exceeded {MAX_RESPONSE_BYTES} bytes"
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AddressSourceError("Etherscan returned invalid JSON") from exc
    result = _api_result(payload)
    sources, compiler_input = _source_files(result)
    timestamp = (now or _utc_now)()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    retrieved_at = timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return VerifiedSource(
        chain_id=normalized_chain,
        address=normalized_address,
        sources=sources,
        metadata=_metadata(result),
        retrieved_at=retrieved_at,
        compiler_input=compiler_input,
    )


def write_verified_source(
    verified: VerifiedSource, output_directory: Path | str
) -> dict[str, object]:
    destination = Path(output_directory).resolve()
    if destination.exists():
        raise AddressSourceError(
            f"refusing to overwrite verified-source directory {destination}"
        )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
        )
        source_entries: list[dict[str, object]] = []
        written_paths: set[str] = set()
        for relative_name, content in verified.sources:
            safe_name = _safe_source_path(relative_name)
            if safe_name in written_paths:
                raise AddressSourceError(
                    f"verified source contains duplicate path {safe_name!r}"
                )
            written_paths.add(safe_name)
            target = staging.joinpath(*PurePosixPath(safe_name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            encoded = content.encode("utf-8")
            target.write_bytes(encoded)
            source_entries.append(
                {
                    "path": safe_name,
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                    "bytes": len(encoded),
                }
            )
        compiler_input_entry: dict[str, object] | None = None
        if verified.compiler_input is not None:
            rendered_input = (
                json.dumps(verified.compiler_input, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            (staging / "compiler-input.json").write_bytes(rendered_input)
            compiler_input_entry = {
                "path": "compiler-input.json",
                "sha256": hashlib.sha256(rendered_input).hexdigest(),
                "bytes": len(rendered_input),
            }
        source_set = hashlib.sha256()
        for entry in source_entries:
            source_set.update(str(entry["path"]).encode("utf-8"))
            source_set.update(b"\0")
            source_set.update(str(entry["sha256"]).encode("ascii"))
            source_set.update(b"\n")
        provenance: dict[str, object] = {
            "schema_version": "1.0",
            "provider": {
                "name": "etherscan",
                "api_version": "v2",
                "endpoint": ETHERSCAN_V2_ENDPOINT,
            },
            "chain_id": verified.chain_id,
            "address": verified.address,
            "retrieved_at": verified.retrieved_at,
            "contract": verified.metadata,
            "sources": source_entries,
            "source_set_sha256": source_set.hexdigest(),
        }
        if compiler_input_entry is not None:
            provenance["compiler_input"] = compiler_input_entry
        (staging / "provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(destination)
    except AddressSourceError:
        if "staging" in locals() and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    except (OSError, UnicodeError) as exc:
        if "staging" in locals() and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise AddressSourceError(
            f"could not write verified source to {destination}: {exc}"
        ) from exc
    return provenance


def fetch_and_write_verified_source(
    chain_id: int | str,
    address: str,
    api_key: str,
    output_directory: Path | str,
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    verified = fetch_verified_source(
        chain_id,
        address,
        api_key,
        timeout_seconds=timeout_seconds,
    )
    return write_verified_source(verified, output_directory)


def _api_result(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise AddressSourceError("Etherscan response root must be an object")
    if payload.get("status") != "1":
        detail = payload.get("result") or payload.get("message") or "request failed"
        if not isinstance(detail, str):
            detail = "request failed"
        raise AddressSourceError(f"Etherscan rejected the request: {detail}")
    result = payload.get("result")
    if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
        raise AddressSourceError("Etherscan returned an unexpected source result")
    return result[0]


def _source_files(
    result: dict[str, object],
) -> tuple[tuple[tuple[str, str], ...], dict[str, object] | None]:
    compiler_type = result.get("CompilerType")
    if isinstance(compiler_type, str) and compiler_type and compiler_type.lower() != "solc":
        raise AddressSourceError(
            f"verified source uses unsupported compiler type {compiler_type!r}; "
            "only Solidity is supported"
        )
    raw_source = result.get("SourceCode")
    if not isinstance(raw_source, str) or not raw_source.strip():
        raise AddressSourceError("contract source is not verified or is empty")
    standard_json = raw_source.strip()
    if standard_json.startswith("{{") and standard_json.endswith("}}"):
        standard_json = standard_json[1:-1]
    parsed: object | None = None
    if standard_json.startswith("{"):
        try:
            parsed = json.loads(standard_json)
        except json.JSONDecodeError:
            parsed = None
    files: list[tuple[str, str]] = []
    if isinstance(parsed, dict) and isinstance(parsed.get("sources"), dict):
        for raw_name, entry in parsed["sources"].items():
            if not isinstance(raw_name, str):
                raise AddressSourceError("verified source contains a non-string path")
            content = entry.get("content") if isinstance(entry, dict) else entry
            if not isinstance(content, str):
                raise AddressSourceError(
                    f"verified source {raw_name!r} has no string content"
                )
            files.append((_safe_source_path(raw_name), content))
    else:
        raw_name = result.get("ContractFileName")
        if not isinstance(raw_name, str) or not raw_name.strip():
            contract_name = result.get("ContractName")
            if not isinstance(contract_name, str) or not contract_name.strip():
                contract_name = "VerifiedContract"
            raw_name = f"{_safe_filename(contract_name)}.sol"
        files.append((_safe_source_path(raw_name), raw_source))
    files.sort(key=lambda item: item[0])
    paths = [path for path, _ in files]
    if len(paths) != len(set(paths)):
        raise AddressSourceError("verified source contains duplicate normalized paths")
    if not any(path.lower().endswith(".sol") for path in paths):
        raise AddressSourceError("verified source contains no .sol files")
    compiler_input = parsed if isinstance(parsed, dict) else None
    return tuple(files), compiler_input


def _safe_source_path(raw_name: str) -> str:
    name = raw_name.replace("\\", "/").strip()
    path = PurePosixPath(name)
    if (
        not name
        or "\0" in name
        or path.is_absolute()
        or ".." in path.parts
        or (path.parts and path.parts[0].endswith(":"))
    ):
        raise AddressSourceError(f"unsafe verified-source path: {raw_name!r}")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise AddressSourceError(f"unsafe verified-source path: {raw_name!r}")
    return normalized


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._")
    return safe or "VerifiedContract"


def _metadata(result: dict[str, object]) -> dict[str, object]:
    fields = {
        "name": "ContractName",
        "compiler_type": "CompilerType",
        "compiler_version": "CompilerVersion",
        "contract_file_name": "ContractFileName",
        "optimization_used": "OptimizationUsed",
        "optimization_runs": "Runs",
        "evm_version": "EVMVersion",
        "license": "LicenseType",
        "constructor_arguments": "ConstructorArguments",
        "libraries": "Library",
        "proxy": "Proxy",
        "implementation": "Implementation",
        "similar_match": "SimilarMatch",
        "swarm_source": "SwarmSource",
    }
    return {
        output_name: result.get(api_name, "")
        for output_name, api_name in fields.items()
        if isinstance(result.get(api_name, ""), (str, int, bool))
    }


def _chain_id(value: int | str) -> str:
    if isinstance(value, bool):
        raise AddressSourceError("chain ID must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AddressSourceError("chain ID must be a positive integer") from exc
    if parsed <= 0 or str(value).strip() not in {str(parsed), f"+{parsed}"}:
        raise AddressSourceError("chain ID must be a positive integer")
    return str(parsed)


def _address(value: str) -> str:
    if not isinstance(value, str) or not ADDRESS_PATTERN.fullmatch(value):
        raise AddressSourceError("address must be 0x followed by 40 hexadecimal digits")
    return value.lower()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
