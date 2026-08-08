from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


class CompilerError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CompilerDiagnostic:
    severity: str
    message: str
    error_code: str | None = None
    source_location: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CompilationResult:
    asts: dict[Path, dict[str, object]]
    compiler_versions: tuple[str, ...]
    diagnostics: tuple[CompilerDiagnostic, ...]


class ForgeCompiler:
    """Load solc ASTs through Foundry without writing into the target project."""

    def __init__(self, executable: str = "forge", timeout: int = 120):
        self.executable = executable
        self.timeout = timeout

    def compile(
        self,
        files: list[Path],
        *,
        project_root: Path | None = None,
        offline: bool = False,
    ) -> CompilationResult:
        executable = shutil.which(self.executable)
        if executable is None:
            raise CompilerError(
                "Foundry is required for --compile, but 'forge' was not found on PATH"
            )
        if not files:
            return CompilationResult({}, (), ())

        root = (project_root or find_project_root(files)).resolve()
        targets = [_target_argument(path.resolve(), root) for path in files]
        with tempfile.TemporaryDirectory(prefix="contract-holes-") as temporary:
            temp = Path(temporary)
            command = [
                executable,
                "build",
                *targets,
                "--root",
                str(root),
                "--out",
                str(temp / "out"),
                "--cache-path",
                str(temp / "cache"),
                "--build-info",
                "--build-info-path",
                str(temp / "build-info"),
                "--ast",
                "--use-literal-content",
                "--color",
                "never",
            ]
            if offline:
                command.append("--offline")
            try:
                process = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise CompilerError(
                    f"Foundry compilation exceeded the {self.timeout}-second timeout"
                ) from exc
            except OSError as exc:
                raise CompilerError(f"could not start Foundry: {exc}") from exc
            if process.returncode != 0:
                detail = _process_error(process.stdout, process.stderr)
                raise CompilerError(f"Foundry compilation failed:\n{detail}")
            return _load_build_info(temp / "build-info", root)


def find_project_root(files: list[Path]) -> Path:
    resolved = [path.resolve() for path in files]
    cwd = Path.cwd().resolve()
    if all(_is_relative_to(path, cwd) for path in resolved):
        starting_point = cwd
    else:
        common = Path(os.path.commonpath([str(path.parent) for path in resolved]))
        starting_point = common

    for candidate in (starting_point, *starting_point.parents):
        if (candidate / "foundry.toml").is_file() or (candidate / ".git").exists():
            return candidate
    return starting_point


def _target_argument(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_build_info(directory: Path, root: Path) -> CompilationResult:
    asts: dict[Path, dict[str, object]] = {}
    versions: set[str] = set()
    diagnostics: list[CompilerDiagnostic] = []
    build_info_files = sorted(directory.glob("*.json"))
    if not build_info_files:
        raise CompilerError("Foundry succeeded but produced no compiler build-info")

    for path in build_info_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CompilerError(f"could not read compiler build-info {path.name}: {exc}") from exc
        version = payload.get("solcLongVersion") or payload.get("solcVersion")
        if isinstance(version, str):
            versions.add(version)
        output = payload.get("output", {})
        if not isinstance(output, dict):
            continue
        sources = output.get("sources", {})
        if isinstance(sources, dict):
            for source_name, source_output in sources.items():
                if not isinstance(source_name, str) or not isinstance(source_output, dict):
                    continue
                ast = source_output.get("ast")
                if isinstance(ast, dict):
                    source_path = Path(source_name)
                    if not source_path.is_absolute():
                        source_path = root / source_path
                    asts[source_path.resolve()] = ast
        errors = output.get("errors", [])
        if isinstance(errors, list):
            diagnostics.extend(_diagnostic(item) for item in errors if isinstance(item, dict))

    return CompilationResult(
        asts=asts,
        compiler_versions=tuple(sorted(versions)),
        diagnostics=tuple(diagnostics),
    )


def _diagnostic(payload: dict[str, object]) -> CompilerDiagnostic:
    code = payload.get("errorCode")
    location = payload.get("sourceLocation")
    return CompilerDiagnostic(
        severity=str(payload.get("severity", "unknown")),
        message=str(payload.get("message") or payload.get("formattedMessage") or "compiler diagnostic"),
        error_code=str(code) if code is not None else None,
        source_location=location if isinstance(location, dict) else None,
    )


def _process_error(stdout: str, stderr: str) -> str:
    detail = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not detail:
        return "unknown compiler error"
    lines = detail.splitlines()
    return "\n".join(lines[-40:])


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False

