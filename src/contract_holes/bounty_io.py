from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


class BountyWorkspaceError(RuntimeError):
    pass


MAX_PRIVATE_RECORD_BYTES = 32 * 1024 * 1024
_CREDENTIAL_URL = re.compile(r"(?P<scheme>https?://)[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?P<name>api[_-]?key|auth[_-]?token|access[_-]?token|private[_-]?key|mnemonic|password|secret)"
    r"(?P<separator>\s*[:=]\s*)(?P<value>[^\s,;]+)"
)


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def payload_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def rendered_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def write_private_json_new_or_identical(path: Path, payload: object) -> bool:
    """Atomically create a private JSON record or accept identical existing bytes."""
    if path.is_symlink():
        raise BountyWorkspaceError(f"refusing symlink private record: {path}")
    destination = path.resolve()
    if destination.parent != path.parent.resolve():
        raise BountyWorkspaceError(f"record path is not normalized: {path}")
    content = rendered_json_bytes(payload)
    if len(content) > MAX_PRIVATE_RECORD_BYTES:
        raise BountyWorkspaceError(
            f"private record exceeds {MAX_PRIVATE_RECORD_BYTES} bytes: {path.name}"
        )
    if destination.exists() or destination.is_symlink():
        _require_identical_regular_file(destination, content)
        return False
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            _require_identical_regular_file(destination, content)
            return False
        return True
    except OSError as exc:
        raise BountyWorkspaceError(
            f"could not write private record {destination}: {exc}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def replace_managed_private_json(
    path: Path,
    payload: object,
    *,
    expected_existing_sha256: str | None,
) -> None:
    """Atomically replace a tool-managed record after optimistic integrity check."""
    if path.is_symlink():
        raise BountyWorkspaceError(f"refusing symlink private record: {path}")
    destination = path.resolve()
    content = rendered_json_bytes(payload)
    if len(content) > MAX_PRIVATE_RECORD_BYTES:
        raise BountyWorkspaceError(
            f"private record exceeds {MAX_PRIVATE_RECORD_BYTES} bytes: {path.name}"
        )
    if destination.exists():
        try:
            existing = destination.read_bytes()
        except OSError as exc:
            raise BountyWorkspaceError(
                f"could not inspect managed record {destination}: {exc}"
            ) from exc
        existing_digest = hashlib.sha256(existing).hexdigest()
        if expected_existing_sha256 is None or existing_digest != expected_existing_sha256:
            raise BountyWorkspaceError(
                f"managed record changed concurrently or outside the workflow: {destination}"
            )
    elif expected_existing_sha256 is not None:
        raise BountyWorkspaceError(f"managed record disappeared: {destination}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError as exc:
        raise BountyWorkspaceError(
            f"could not replace managed record {destination}: {exc}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def load_private_json(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise BountyWorkspaceError(f"private record is not a regular file: {path}")
    source = path.resolve()
    if not source.is_file():
        raise BountyWorkspaceError(f"private record is not a regular file: {source}")
    try:
        size = source.stat().st_size
        if size > MAX_PRIVATE_RECORD_BYTES:
            raise BountyWorkspaceError(
                f"private record exceeds {MAX_PRIVATE_RECORD_BYTES} bytes: {source.name}"
            )
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BountyWorkspaceError(
            f"could not read private record {source.name}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise BountyWorkspaceError(f"private record root must be an object: {source.name}")
    return payload


def redact_sensitive_text(
    value: str, *, private_paths: tuple[Path | str, ...] = ()
) -> str:
    redacted = _CREDENTIAL_URL.sub(r"\g<scheme><redacted>@", value)
    redacted = _SECRET_ASSIGNMENT.sub(
        lambda match: (
            f"{match.group('name')}{match.group('separator')}<redacted>"
        ),
        redacted,
    )
    normalized_paths = sorted(
        {str(Path(path).resolve()) for path in private_paths},
        key=len,
        reverse=True,
    )
    for private_path in normalized_paths:
        redacted = redacted.replace(private_path, "<private-path>")
    return redacted


def _require_identical_regular_file(path: Path, expected: bytes) -> None:
    if path.is_symlink() or not path.is_file():
        raise BountyWorkspaceError(f"refusing non-regular private record: {path}")
    try:
        existing = path.read_bytes()
    except OSError as exc:
        raise BountyWorkspaceError(f"could not inspect private record {path}: {exc}") from exc
    if existing != expected:
        raise BountyWorkspaceError(f"refusing to overwrite changed private record: {path}")
