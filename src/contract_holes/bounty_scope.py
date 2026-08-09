from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
from typing import Iterable, Sequence
import re

from . import __version__
from .bounty_io import (
    BountyWorkspaceError,
    payload_sha256,
    write_private_json_new_or_identical,
)
from .bounty_profile import BountyProfile, BountyProfileError, load_bounty_profile
from .compiler import CompilationResult, CompiledSource, CompilerError, ForgeCompiler
from .limits import ScanLimits
from .models import Finding
from .process_environment import sanitized_subprocess_environment
from .reporters import json_report
from .scanner import ScanError, Scanner


class BountyScopeError(RuntimeError):
    pass


SOURCE_MANIFEST_FILENAME = "source-manifest.json"
SCAN_RECORD_FILENAME = "scan.json"
SOURCE_MANIFEST_SCHEMA_VERSION = "1.0"
SCAN_RECORD_SCHEMA_VERSION = "1.0"
_GIT_ENVIRONMENT = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
}
BOUNTY_ENVIRONMENT_REMOVE_PREFIXES = (
    "AWS_",
    "AZURE_",
    "CI_",
    "DAPP_",
    "ETH_",
    "FOUNDRY_",
    "GITHUB_",
    "GITLAB_",
    "GOOGLE_",
    "WEB3_",
)
_IMPORT_PATTERN = re.compile(
    r"\bimport\s+(?:[^;\"']*?\s+from\s+)?[\"'](?P<path>[^\"']+)[\"']\s*;",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class SourceEntry:
    relative_path: str
    path: Path
    sha256: str
    bytes: int

    def payload(self) -> dict[str, object]:
        return {
            "path": self.relative_path,
            "sha256": self.sha256,
            "bytes": self.bytes,
        }


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    root: Path
    scope_paths: tuple[str, ...]
    files: tuple[SourceEntry, ...]
    source_set_sha256: str
    remappings: tuple[str, ...]
    remappings_sha256: str | None

    def public_payload(self) -> dict[str, object]:
        return {
            "schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
            "scope_paths": list(self.scope_paths),
            "files": [entry.payload() for entry in self.files],
            "source_set_sha256": self.source_set_sha256,
            "remappings_sha256": self.remappings_sha256,
        }


@dataclass(frozen=True, slots=True)
class BountyScanResult:
    profile: BountyProfile
    source_identity: SourceIdentity
    source_manifest: dict[str, object]
    scan_record: dict[str, object]
    findings: tuple[Finding, ...]


def identify_source(
    source_root: Path | str,
    scope_paths: Sequence[str],
    *,
    limits: ScanLimits = ScanLimits(),
) -> SourceIdentity:
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise BountyScopeError(f"source root is not a directory: {root}")
    normalized_scope = tuple(_normalized_scope_path(value) for value in scope_paths)
    if not normalized_scope:
        raise BountyScopeError("at least one scope path is required")
    if len(normalized_scope) != len(set(normalized_scope)):
        raise BountyScopeError("scope paths must not contain duplicates")
    files = _discover_scoped_sources(root, normalized_scope, limits=limits)
    remappings, remappings_digest = _load_safe_remappings(root)
    source_set = hashlib.sha256()
    for entry in files:
        source_set.update(entry.relative_path.encode("utf-8"))
        source_set.update(b"\0")
        source_set.update(entry.sha256.encode("ascii"))
        source_set.update(b"\n")
    if remappings_digest is not None:
        source_set.update(b"config\0remappings.txt\0")
        source_set.update(remappings_digest.encode("ascii"))
        source_set.update(b"\n")
    return SourceIdentity(
        root=root,
        scope_paths=normalized_scope,
        files=files,
        source_set_sha256=source_set.hexdigest(),
        remappings=remappings,
        remappings_sha256=remappings_digest,
    )


def validate_profile_source(profile: BountyProfile) -> SourceIdentity:
    if profile.source_kind == "git":
        _validate_git_source(profile)
    identity = identify_source(profile.source_root, profile.scope_paths)
    if (
        profile.source_kind == "directory"
        and identity.source_set_sha256 != profile.source_content_sha256
    ):
        raise BountyScopeError(
            "directory source identity does not match source.content_sha256"
        )
    return identity


def scan_bounty_workspace(workspace: Path | str) -> BountyScanResult:
    try:
        profile = load_bounty_profile(workspace)
    except BountyProfileError as exc:
        raise BountyScopeError(str(exc)) from exc
    identity = validate_profile_source(profile)
    source_manifest = _source_manifest(profile, identity)
    try:
        write_private_json_new_or_identical(
            profile.workspace / SOURCE_MANIFEST_FILENAME, source_manifest
        )
    except BountyWorkspaceError as exc:
        raise BountyScopeError(str(exc)) from exc

    scoped_compiler: ScopedForgeCompiler | None = None
    if profile.compiler_enabled:
        scoped_compiler = ScopedForgeCompiler(profile, identity)
    scanner = Scanner(compiler=scoped_compiler) if scoped_compiler else Scanner()
    try:
        for entry in identity.files:
            _verify_entry(entry)
        findings, files_scanned = scanner.scan_paths(
            [entry.path for entry in identity.files],
            include_dependencies=True,
            compile_sources=profile.compiler_enabled,
            compiler_offline=True,
        )
        for entry in identity.files:
            _verify_entry(entry)
    except ScanError as exc:
        raise BountyScopeError(str(exc)) from exc
    relative_findings = tuple(
        replace(finding, path=Path(_relative_to_root(finding.path, profile.source_root)))
        for finding in findings
    )
    report = json.loads(json_report(list(relative_findings), files_scanned))
    scan_record: dict[str, object] = {
        "schema_version": SCAN_RECORD_SCHEMA_VERSION,
        "command": "bounty.scan",
        "status": "completed",
        "scanner_version": __version__,
        "profile_sha256": profile.digest,
        "source_manifest_sha256": str(source_manifest["manifest_sha256"]),
        "compiler": {
            "enabled": profile.compiler_enabled,
            "offline": True,
            "isolation": "staged-approved-sources",
            "versions": list(
                scoped_compiler.compiler_versions if scoped_compiler else ()
            ),
        },
        "report": report,
    }
    scan_record["scan_sha256"] = payload_sha256(scan_record)
    try:
        write_private_json_new_or_identical(
            profile.workspace / SCAN_RECORD_FILENAME, scan_record
        )
    except BountyWorkspaceError as exc:
        raise BountyScopeError(str(exc)) from exc
    return BountyScanResult(
        profile=profile,
        source_identity=identity,
        source_manifest=source_manifest,
        scan_record=scan_record,
        findings=relative_findings,
    )


class ScopedForgeCompiler:
    """Compile only approved bytes in a fresh project with safe configuration."""

    def __init__(
        self,
        profile: BountyProfile,
        identity: SourceIdentity,
        *,
        delegate: ForgeCompiler | None = None,
    ):
        self.profile = profile
        self.identity = identity
        self.delegate = delegate or ForgeCompiler(
            environment_remove_prefixes=BOUNTY_ENVIRONMENT_REMOVE_PREFIXES
        )
        self.compiler_versions: tuple[str, ...] = ()

    def compile(
        self,
        files: list[Path],
        *,
        project_root: Path | None = None,
        offline: bool = False,
    ) -> CompilationResult:
        if not offline:
            raise CompilerError("bounty compiler execution must remain offline")
        approved = {entry.path.resolve(): entry for entry in self.identity.files}
        requested = [path.resolve() for path in files]
        unapproved = [path for path in requested if path not in approved]
        if unapproved:
            raise CompilerError(
                "bounty compiler received out-of-scope source: " + str(unapproved[0])
            )
        with tempfile.TemporaryDirectory(prefix="contract-holes-bounty-compile-") as raw:
            staged_root = Path(raw)
            staged_to_original: dict[Path, SourceEntry] = {}
            staged_files: list[Path] = []
            for entry in self.identity.files:
                _verify_entry(entry)
                _validate_import_paths(entry)
                staged = staged_root.joinpath(*PurePosixPath(entry.relative_path).parts)
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(entry.path, staged)
                staged = staged.resolve()
                staged_to_original[staged] = entry
                if entry.path.resolve() in requested:
                    staged_files.append(staged)
            (staged_root / "foundry.toml").write_text(
                "[profile.default]\n"
                'src = "."\n'
                'test = "__holes_no_tests__"\n'
                'script = "__holes_no_scripts__"\n'
                "libs = []\n"
                "auto_detect_solc = true\n"
                "ffi = false\n",
                encoding="utf-8",
            )
            if self.identity.remappings:
                (staged_root / "remappings.txt").write_text(
                    "\n".join(self.identity.remappings) + "\n",
                    encoding="utf-8",
                )
            result = self.delegate.compile(
                staged_files,
                project_root=staged_root,
                offline=True,
            )
            remapped_sources: list[CompiledSource] = []
            for compiled in result.sources:
                staged_path = compiled.path.resolve()
                entry = staged_to_original.get(staged_path)
                if entry is None:
                    raise CompilerError(
                        "compiler consumed an out-of-scope source unit: "
                        + _redacted_stage_path(staged_path, staged_root)
                    )
                if compiled.content is None:
                    raise CompilerError(
                        "compiler build-info omitted literal content for approved source: "
                        + entry.relative_path
                    )
                compiled_hash = hashlib.sha256(
                    compiled.content.encode("utf-8")
                ).hexdigest()
                if compiled_hash != entry.sha256:
                    raise CompilerError(
                        "compiler literal content differs from approved source: "
                        + entry.relative_path
                    )
                remapped_sources.append(replace(compiled, path=entry.path))
            self.compiler_versions = result.compiler_versions
            return replace(result, sources=tuple(remapped_sources))


def _source_manifest(
    profile: BountyProfile, identity: SourceIdentity
) -> dict[str, object]:
    source: dict[str, object] = {"kind": profile.source_kind}
    if profile.source_revision is not None:
        source["revision"] = profile.source_revision
    if profile.source_content_sha256 is not None:
        source["content_sha256"] = profile.source_content_sha256
    payload: dict[str, object] = {
        "schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        "scanner_version": __version__,
        "profile_sha256": profile.digest,
        "source": source,
        "scope_paths": list(identity.scope_paths),
        "files": [entry.payload() for entry in identity.files],
        "source_set_sha256": identity.source_set_sha256,
        "compiler": {
            "enabled": profile.compiler_enabled,
            "offline": True,
            "isolation": "staged-approved-sources",
            "target_configuration_loaded": False,
            "remappings_sha256": identity.remappings_sha256,
        },
    }
    payload["manifest_sha256"] = payload_sha256(payload)
    return payload


def _discover_scoped_sources(
    root: Path,
    scope_paths: Sequence[str],
    *,
    limits: ScanLimits,
) -> tuple[SourceEntry, ...]:
    discovered: dict[str, Path] = {}
    for scope_path in scope_paths:
        candidate = root.joinpath(*PurePosixPath(scope_path).parts)
        _require_contained_no_symlink(root, candidate, must_exist=True)
        if candidate.is_file():
            if candidate.suffix.lower() != ".sol":
                raise BountyScopeError(f"scoped file is not Solidity source: {scope_path}")
            discovered[_relative_to_root(candidate, root)] = candidate
            continue
        if not candidate.is_dir():
            raise BountyScopeError(f"scope path is not a regular file or directory: {scope_path}")
        for directory, directory_names, filenames in os.walk(candidate, followlinks=False):
            current = Path(directory)
            safe_directories: list[str] = []
            for name in sorted(directory_names):
                child = current / name
                if child.is_symlink():
                    raise BountyScopeError(f"scope contains a symlink directory: {_relative_to_root(child, root)}")
                if name == ".git":
                    continue
                safe_directories.append(name)
            directory_names[:] = safe_directories
            for name in sorted(filenames):
                child = current / name
                if child.suffix.lower() != ".sol":
                    continue
                _require_contained_no_symlink(root, child, must_exist=True)
                discovered[_relative_to_root(child, root)] = child
                if len(discovered) > limits.max_files:
                    raise BountyScopeError(
                        f"scope contains more than {limits.max_files} Solidity files"
                    )
    if not discovered:
        raise BountyScopeError("approved scope contains no Solidity source files")
    entries: list[SourceEntry] = []
    total_bytes = 0
    for relative_path, path in sorted(discovered.items()):
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise BountyScopeError(f"could not read scoped source {relative_path}: {exc}") from exc
        total_bytes += len(data)
        if total_bytes > limits.max_source_bytes:
            raise BountyScopeError(
                f"scoped Solidity source exceeds {limits.max_source_bytes} bytes"
            )
        entries.append(
            SourceEntry(
                relative_path=relative_path,
                path=path.resolve(),
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
            )
        )
    return tuple(entries)


def _validate_git_source(profile: BountyProfile) -> None:
    git = shutil.which("git")
    if git is None:
        raise BountyScopeError("Git is required to validate a Git bounty source")
    root = _git_output(git, profile.source_root, "rev-parse", "--show-toplevel")
    if Path(root).resolve() != profile.source_root:
        raise BountyScopeError("source.root must be the root of its Git worktree")
    object_type = _git_output(
        git, profile.source_root, "cat-file", "-t", str(profile.source_revision)
    )
    if object_type != "commit":
        raise BountyScopeError("source.revision does not identify a Git commit")
    head = _git_output(git, profile.source_root, "rev-parse", "HEAD")
    if head != profile.source_revision:
        raise BountyScopeError(
            f"Git HEAD {head} does not match approved revision {profile.source_revision}"
        )
    status_output = _git_output(
        git,
        profile.source_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status_output:
        raise BountyScopeError("Git source worktree is not clean")


def _git_output(git: str, root: Path, *arguments: str) -> str:
    command = [
        git,
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-C",
        str(root),
        *arguments,
    ]
    environment = sanitized_subprocess_environment(remove_prefixes=("GIT_",))
    environment.update(_GIT_ENVIRONMENT)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BountyScopeError(f"could not validate Git source: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        diagnostic = detail[-1] if detail else "Git command failed"
        raise BountyScopeError(f"could not validate Git source: {diagnostic}")
    return completed.stdout.strip()


def _load_safe_remappings(root: Path) -> tuple[tuple[str, ...], str | None]:
    path = root / "remappings.txt"
    if not path.exists():
        return (), None
    _require_contained_no_symlink(root, path, must_exist=True)
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise BountyScopeError(f"could not read remappings.txt: {exc}") from exc
    remappings: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line or any(character.isspace() for character in line):
            raise BountyScopeError(f"invalid remapping at remappings.txt:{line_number}")
        prefix, target_value = line.rsplit("=", 1)
        if not prefix or not target_value:
            raise BountyScopeError(f"invalid remapping at remappings.txt:{line_number}")
        target = Path(target_value)
        if target.is_absolute() or ".." in PurePosixPath(target_value).parts:
            raise BountyScopeError(
                f"remapping escapes source root at remappings.txt:{line_number}"
            )
        resolved_target = (root / target).resolve()
        if not _is_relative_to(resolved_target, root):
            raise BountyScopeError(
                f"remapping escapes source root at remappings.txt:{line_number}"
            )
        if resolved_target.exists():
            _require_contained_no_symlink(root, root / target, must_exist=True)
        remappings.append(line)
    return tuple(remappings), hashlib.sha256(data).hexdigest()


def _verify_entry(entry: SourceEntry) -> None:
    try:
        data = entry.path.read_bytes()
    except OSError as exc:
        raise CompilerError(f"could not re-read approved source {entry.relative_path}: {exc}") from exc
    if len(data) != entry.bytes or hashlib.sha256(data).hexdigest() != entry.sha256:
        raise CompilerError(f"approved source changed during scan: {entry.relative_path}")


def _validate_import_paths(entry: SourceEntry) -> None:
    try:
        text = entry.path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CompilerError(f"could not inspect imports in {entry.relative_path}: {exc}") from exc
    without_comments = _remove_solidity_comments(text)
    for match in _IMPORT_PATTERN.finditer(without_comments):
        import_value = match.group("path")
        candidate = PurePosixPath(import_value)
        if (
            not import_value
            or "\\" in import_value
            or candidate.is_absolute()
            or ".." in candidate.parts
            or "://" in import_value
        ):
            raise CompilerError(
                f"unsafe import path in approved source {entry.relative_path}: {import_value}"
            )


def _remove_solidity_comments(text: str) -> str:
    characters = list(text)
    index = 0
    state = "code"
    quote = ""
    while index < len(characters):
        character = characters[index]
        following = characters[index + 1] if index + 1 < len(characters) else ""
        if state == "code":
            if character == "/" and following == "/":
                characters[index] = characters[index + 1] = " "
                index += 2
                state = "line"
                continue
            if character == "/" and following == "*":
                characters[index] = characters[index + 1] = " "
                index += 2
                state = "block"
                continue
            if character in {"\"", "'"}:
                quote = character
                state = "string"
        elif state == "line":
            if character == "\n":
                state = "code"
            else:
                characters[index] = " "
        elif state == "block":
            if character == "*" and following == "/":
                characters[index] = characters[index + 1] = " "
                index += 2
                state = "code"
                continue
            if character != "\n":
                characters[index] = " "
        elif state == "string":
            if character == "\\":
                index += 2
                continue
            if character == quote:
                state = "code"
        index += 1
    return "".join(characters)


def _require_contained_no_symlink(
    root: Path, candidate: Path, *, must_exist: bool
) -> None:
    root = root.resolve()
    lexical = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise BountyScopeError(f"path escapes source root: {candidate}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if must_exist:
                raise BountyScopeError(
                    f"scoped path does not exist: {_relative_to_root(current, root)}"
                )
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise BountyScopeError(
                f"scope path contains a symlink: {_relative_to_root(current, root)}"
            )
    resolved = lexical.resolve()
    if not _is_relative_to(resolved, root):
        raise BountyScopeError(f"path escapes source root: {candidate}")


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise BountyScopeError(f"path escapes source root: {path}") from exc


def _normalized_scope_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BountyScopeError("scope paths must be non-empty POSIX paths")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BountyScopeError(f"scope path must be relative and contained: {value}")
    normalized = candidate.as_posix()
    if normalized != value or normalized.startswith("./"):
        raise BountyScopeError(f"scope path must be normalized: {value}")
    return normalized


def _redacted_stage_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return "<outside-isolated-project>"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
