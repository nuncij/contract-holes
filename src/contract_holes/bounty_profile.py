from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10
    tomllib = None

from .config import ConfigError, _parse_toml_subset


class BountyProfileError(RuntimeError):
    pass


PROFILE_FILENAME = "bounty.toml"
PROFILE_SCHEMA_VERSION = 1
PROFILE_NORMALIZED_SCHEMA_VERSION = "1.0"
GIT_REVISION_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class BountyProfile:
    path: Path
    program_name: str
    platform: str
    rules_url: str
    reviewed_on: str
    authorization_note: str
    source_kind: str
    source_root_value: str
    source_root: Path
    source_revision: str | None
    source_content_sha256: str | None
    scope_paths: tuple[str, ...]
    impacts: tuple[str, ...]
    restrictions: tuple[str, ...]
    compiler_enabled: bool
    compiler_offline: bool

    @property
    def workspace(self) -> Path:
        return self.path.parent

    @property
    def digest(self) -> str:
        material = json.dumps(
            self.normalized_payload(include_digest=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def normalized_payload(self, *, include_digest: bool = True) -> dict[str, object]:
        source: dict[str, object] = {
            "kind": self.source_kind,
            "root": self.source_root_value,
        }
        if self.source_revision is not None:
            source["revision"] = self.source_revision
        if self.source_content_sha256 is not None:
            source["content_sha256"] = self.source_content_sha256
        payload: dict[str, object] = {
            "schema_version": PROFILE_NORMALIZED_SCHEMA_VERSION,
            "program": {
                "name": self.program_name,
                "platform": self.platform,
                "rules_url": self.rules_url,
                "reviewed_on": self.reviewed_on,
                "authorization_acknowledged": True,
                "authorization_note": self.authorization_note,
            },
            "source": source,
            "scope": {
                "paths": list(self.scope_paths),
                "impacts": list(self.impacts),
                "restrictions": list(self.restrictions),
            },
            "compiler": {
                "enabled": self.compiler_enabled,
                "offline": self.compiler_offline,
            },
        }
        if include_digest:
            payload["profile_sha256"] = self.digest
        return payload


def initialize_bounty_workspace(
    workspace: Path | str,
    *,
    program_name: str,
    platform: str,
    rules_url: str,
    reviewed_on: str,
    authorization_acknowledged: bool,
    authorization_note: str,
    source_root: Path | str,
    source_revision: str | None,
    source_content_sha256: str | None,
    scope_paths: list[str] | tuple[str, ...],
    impacts: list[str] | tuple[str, ...],
    restrictions: list[str] | tuple[str, ...] = (),
    compiler_enabled: bool = True,
) -> BountyProfile:
    destination = Path(workspace).resolve()
    source = Path(source_root).resolve()
    if not source.is_dir():
        raise BountyProfileError(f"source root is not a directory: {source}")
    if destination.exists():
        raise BountyProfileError(f"workspace already exists: {destination}")
    if _is_relative_to(destination, source):
        raise BountyProfileError("bounty workspace must be outside the target source tree")

    source_value = Path(os.path.relpath(source, destination)).as_posix()
    payload: dict[str, object] = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "program": {
            "name": program_name,
            "platform": platform,
            "rules_url": rules_url,
            "reviewed_on": reviewed_on,
            "authorization_acknowledged": authorization_acknowledged,
            "authorization_note": authorization_note,
        },
        "source": {
            "kind": "git" if source_revision is not None else "directory",
            "root": source_value,
            **(
                {"revision": source_revision}
                if source_revision is not None
                else {"content_sha256": source_content_sha256}
            ),
        },
        "scope": {
            "paths": list(scope_paths),
            "impacts": list(impacts),
            "restrictions": list(restrictions),
        },
        "compiler": {
            "enabled": compiler_enabled,
            "offline": True,
        },
    }
    _validate_payload(payload, destination / PROFILE_FILENAME, require_source=False)

    try:
        destination.mkdir(mode=0o700, parents=True)
        _write_exclusive(
            destination / PROFILE_FILENAME,
            _render_profile(payload),
            mode=0o600,
        )
        _write_exclusive(
            destination / ".gitignore",
            "# Bounty workspaces are private by default.\n*\n!.gitignore\n",
            mode=0o600,
        )
    except OSError as exc:
        if destination.is_dir():
            shutil.rmtree(destination)
        raise BountyProfileError(
            f"could not initialize bounty workspace {destination}: {exc}"
        ) from exc
    return load_bounty_profile(destination)


def load_bounty_profile(path: Path | str) -> BountyProfile:
    supplied = Path(path).resolve()
    source = supplied / PROFILE_FILENAME if supplied.is_dir() else supplied
    if not source.is_file():
        raise BountyProfileError(f"bounty profile does not exist: {source}")
    try:
        raw = source.read_bytes()
        text = raw.decode("utf-8")
        payload = (
            tomllib.loads(text)
            if tomllib is not None
            else _parse_toml_subset(text, source)
        )
    except (OSError, UnicodeError) as exc:
        raise BountyProfileError(f"could not read bounty profile {source}: {exc}") from exc
    except Exception as exc:
        if tomllib is not None and isinstance(exc, tomllib.TOMLDecodeError):
            raise BountyProfileError(f"invalid TOML in {source}: {exc}") from exc
        if isinstance(exc, ConfigError):
            raise BountyProfileError(str(exc)) from exc
        raise
    return _validate_payload(payload, source, require_source=True)


def _validate_payload(
    payload: object, source: Path, *, require_source: bool
) -> BountyProfile:
    root = _table(payload, "profile root")
    _unknown_keys(
        root,
        {"schema_version", "program", "source", "scope", "compiler"},
        "root",
    )
    if root.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise BountyProfileError(f"schema_version must be {PROFILE_SCHEMA_VERSION}")

    program = _table(root.get("program"), "[program]")
    source_table = _table(root.get("source"), "[source]")
    scope = _table(root.get("scope"), "[scope]")
    compiler = _table(root.get("compiler"), "[compiler]")
    _unknown_keys(
        program,
        {
            "name",
            "platform",
            "rules_url",
            "reviewed_on",
            "authorization_acknowledged",
            "authorization_note",
        },
        "[program]",
    )
    _unknown_keys(
        source_table,
        {"kind", "root", "revision", "content_sha256"},
        "[source]",
    )
    _unknown_keys(scope, {"paths", "impacts", "restrictions"}, "[scope]")
    _unknown_keys(compiler, {"enabled", "offline"}, "[compiler]")

    program_name = _nonempty_string(program.get("name"), "program.name")
    platform = _nonempty_string(program.get("platform"), "program.platform")
    rules_url = _nonempty_string(program.get("rules_url"), "program.rules_url")
    if not rules_url.startswith("https://") or any(
        character.isspace() for character in rules_url
    ):
        raise BountyProfileError("program.rules_url must be an HTTPS URL")
    reviewed_on = _nonempty_string(program.get("reviewed_on"), "program.reviewed_on")
    try:
        date.fromisoformat(reviewed_on)
    except ValueError as exc:
        raise BountyProfileError("program.reviewed_on must be YYYY-MM-DD") from exc
    if program.get("authorization_acknowledged") is not True:
        raise BountyProfileError(
            "program.authorization_acknowledged must be true before scanning"
        )
    authorization_note = _nonempty_string(
        program.get("authorization_note"), "program.authorization_note"
    )

    source_kind = _nonempty_string(source_table.get("kind"), "source.kind")
    if source_kind not in {"git", "directory"}:
        raise BountyProfileError("source.kind must be 'git' or 'directory'")
    source_root_value = _nonempty_string(source_table.get("root"), "source.root")
    if "\x00" in source_root_value:
        raise BountyProfileError("source.root contains a null byte")
    source_root_path = Path(source_root_value)
    if source_root_path.is_absolute():
        raise BountyProfileError("source.root must be relative to the bounty workspace")
    source_root = (source.parent / source_root_path).resolve()
    if _is_relative_to(source.parent, source_root):
        raise BountyProfileError("bounty workspace must be outside the target source tree")
    if require_source and not source_root.is_dir():
        raise BountyProfileError(f"source root is not a directory: {source_root}")

    revision = source_table.get("revision")
    content_sha256 = source_table.get("content_sha256")
    if source_kind == "git":
        if not isinstance(revision, str) or not GIT_REVISION_PATTERN.fullmatch(revision):
            raise BountyProfileError(
                "source.revision must be an exact lowercase 40- or 64-hex Git revision"
            )
        if content_sha256 is not None:
            raise BountyProfileError("Git sources must not set source.content_sha256")
        normalized_revision = revision
        normalized_content = None
    else:
        if revision is not None:
            raise BountyProfileError("directory sources must not set source.revision")
        if not isinstance(content_sha256, str) or not SHA256_PATTERN.fullmatch(
            content_sha256
        ):
            raise BountyProfileError(
                "source.content_sha256 must be a lowercase SHA-256 digest"
            )
        normalized_revision = None
        normalized_content = content_sha256

    scope_paths = tuple(_string_list(scope.get("paths"), "scope.paths", nonempty=True))
    normalized_paths = tuple(_scope_path(value) for value in scope_paths)
    if len(normalized_paths) != len(set(normalized_paths)):
        raise BountyProfileError("scope.paths must not contain duplicates")
    impacts = tuple(_string_list(scope.get("impacts"), "scope.impacts", nonempty=True))
    restrictions = tuple(
        _string_list(scope.get("restrictions", []), "scope.restrictions")
    )
    compiler_enabled = _boolean(compiler.get("enabled"), "compiler.enabled")
    compiler_offline = _boolean(compiler.get("offline"), "compiler.offline")
    if not compiler_offline:
        raise BountyProfileError("compiler.offline must be true in bounty profiles")

    return BountyProfile(
        path=source,
        program_name=program_name,
        platform=platform,
        rules_url=rules_url,
        reviewed_on=reviewed_on,
        authorization_note=authorization_note,
        source_kind=source_kind,
        source_root_value=source_root_value,
        source_root=source_root,
        source_revision=normalized_revision,
        source_content_sha256=normalized_content,
        scope_paths=normalized_paths,
        impacts=impacts,
        restrictions=restrictions,
        compiler_enabled=compiler_enabled,
        compiler_offline=compiler_offline,
    )


def _render_profile(payload: dict[str, object]) -> str:
    program = payload["program"]
    source = payload["source"]
    scope = payload["scope"]
    compiler = payload["compiler"]
    assert isinstance(program, dict)
    assert isinstance(source, dict)
    assert isinstance(scope, dict)
    assert isinstance(compiler, dict)
    lines = [
        f"schema_version = {PROFILE_SCHEMA_VERSION}",
        "",
        "[program]",
        f"name = {_toml_string(str(program['name']))}",
        f"platform = {_toml_string(str(program['platform']))}",
        f"rules_url = {_toml_string(str(program['rules_url']))}",
        f"reviewed_on = {_toml_string(str(program['reviewed_on']))}",
        "authorization_acknowledged = true",
        f"authorization_note = {_toml_string(str(program['authorization_note']))}",
        "",
        "[source]",
        f"kind = {_toml_string(str(source['kind']))}",
        f"root = {_toml_string(str(source['root']))}",
    ]
    if "revision" in source:
        lines.append(f"revision = {_toml_string(str(source['revision']))}")
    else:
        lines.append(
            f"content_sha256 = {_toml_string(str(source['content_sha256']))}"
        )
    lines.extend(
        [
            "",
            "[scope]",
            f"paths = {_toml_array(scope['paths'])}",
            f"impacts = {_toml_array(scope['impacts'])}",
            f"restrictions = {_toml_array(scope['restrictions'])}",
            "",
            "[compiler]",
            f"enabled = {'true' if compiler['enabled'] else 'false'}",
            "offline = true",
            "",
        ]
    )
    return "\n".join(lines)


def _toml_array(value: object) -> str:
    assert isinstance(value, list)
    return "[" + ", ".join(_toml_string(str(item)) for item in value) + "]"


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _write_exclusive(path: Path, content: str, *, mode: int) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _table(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BountyProfileError(f"{label} must be a table")
    return value


def _unknown_keys(table: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(table) - allowed
    if unknown:
        raise BountyProfileError(f"unknown {label} setting: {', '.join(sorted(unknown))}")


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BountyProfileError(f"{label} must be a non-empty string")
    return value


def _string_list(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() or "\x00" in item
        for item in value
    ):
        raise BountyProfileError(f"{label} must be an array of non-empty strings")
    if nonempty and not value:
        raise BountyProfileError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise BountyProfileError(f"{label} must not contain duplicates")
    return list(value)


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise BountyProfileError(f"{label} must be true or false")
    return value


def _scope_path(value: str) -> str:
    if "\\" in value:
        raise BountyProfileError("scope paths must use forward slashes")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in {"", ".."} for part in candidate.parts):
        raise BountyProfileError(f"scope path must be relative and contained: {value}")
    normalized = candidate.as_posix()
    if normalized != value or normalized.startswith("./"):
        raise BountyProfileError(f"scope path must be normalized: {value}")
    return normalized


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
