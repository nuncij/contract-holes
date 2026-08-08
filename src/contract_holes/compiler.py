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
class CompiledSource:
    path: Path
    source_id: int
    compilation_id: str
    ast: dict[str, object]
    content: str | None = None


@dataclass(frozen=True, slots=True)
class CompilationResult:
    sources: tuple[CompiledSource, ...]
    compiler_versions: tuple[str, ...]
    diagnostics: tuple[CompilerDiagnostic, ...]

    @property
    def asts(self) -> dict[Path, dict[str, object]]:
        """Compatibility view for callers that only need one AST per path."""
        result: dict[Path, dict[str, object]] = {}
        for source in self.sources:
            result.setdefault(source.path, source.ast)
        return result

    @property
    def source_ids(self) -> dict[Path, int]:
        result: dict[Path, int] = {}
        for source in self.sources:
            result.setdefault(source.path, source.source_id)
        return result

    @property
    def source_contents(self) -> dict[Path, str]:
        result: dict[Path, str] = {}
        for source in self.sources:
            if source.content is not None:
                result.setdefault(source.path, source.content)
        return result


class ForgeCompiler:
    """Load solc ASTs through Foundry without writing into the target project."""

    def __init__(self, executable: str = "forge", timeout: float = 120.0):
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
            return CompilationResult((), (), ())

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
                    "resource limit exceeded [compiler-time]: Foundry compilation "
                    f"exceeded {self.timeout:g} seconds"
                ) from exc
            except OSError as exc:
                raise CompilerError(f"could not start Foundry: {exc}") from exc
            if process.returncode != 0:
                detail = _process_error(process.stdout, process.stderr)
                raise CompilerError(f"Foundry compilation failed:\n{detail}")
            return _load_build_info(temp / "build-info", root)


def find_project_root(files: list[Path]) -> Path:
    resolved = [path.resolve() for path in files]
    starting_point = Path(
        os.path.commonpath([str(path.parent) for path in resolved])
    )

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
    compiled_sources: list[CompiledSource] = []
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
        compilation_id = payload.get("id")
        if not isinstance(compilation_id, str) or not compilation_id:
            compilation_id = path.stem
        input_payload = payload.get("input", {})
        input_sources = (
            input_payload.get("sources", {}) if isinstance(input_payload, dict) else {}
        )
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
                    source_path = _source_path(source_name, root)
                    source_id = source_output.get("id")
                    if not isinstance(source_id, int):
                        source_id = _source_id_from_ast(ast)
                    if source_id is None:
                        raise CompilerError(
                            f"compiler source {source_name!r} has no numeric source ID"
                        )
                    content = _literal_source_content(input_sources, source_name)
                    compiled_sources.append(
                        CompiledSource(
                            path=source_path,
                            source_id=source_id,
                            compilation_id=compilation_id,
                            ast=ast,
                            content=content,
                        )
                    )
        errors = output.get("errors", [])
        if isinstance(errors, list):
            diagnostics.extend(_diagnostic(item) for item in errors if isinstance(item, dict))

    return CompilationResult(
        sources=tuple(
            sorted(
                compiled_sources,
                key=lambda item: (item.compilation_id, str(item.path), item.source_id),
            )
        ),
        compiler_versions=tuple(sorted(versions)),
        diagnostics=tuple(diagnostics),
    )


def _source_path(source_name: str, root: Path) -> Path:
    source_path = Path(source_name)
    if not source_path.is_absolute():
        source_path = root / source_path
    return source_path.resolve()


def _source_id_from_ast(ast: dict[str, object]) -> int | None:
    value = ast.get("src")
    if not isinstance(value, str):
        return None
    pieces = value.split(":", 2)
    if len(pieces) != 3:
        return None
    try:
        return int(pieces[2])
    except ValueError:
        return None


def _literal_source_content(input_sources: object, source_name: str) -> str | None:
    if not isinstance(input_sources, dict):
        return None
    source_input = input_sources.get(source_name)
    if not isinstance(source_input, dict):
        return None
    content = source_input.get("content")
    return content if isinstance(content, str) else None


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
