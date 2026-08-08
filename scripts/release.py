#!/usr/bin/env python3
from __future__ import annotations

import argparse
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
from importlib import metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r'^version = "([0-9]+\.[0-9]+\.[0-9]+)"$', re.MULTILINE)
INIT_VERSION_PATTERN = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)


class ReleaseError(RuntimeError):
    pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Build two byte-identical wheel/sdist pairs from the clean Git HEAD, "
            "validate them, smoke-test the wheel, and write checksums."
        )
    )
    result.add_argument(
        "--output",
        default="dist",
        help="new or empty artifact directory (default: dist)",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        payload = build_release(Path(args.output))
    except ReleaseError as exc:
        print(f"release: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_release(output_directory: Path) -> dict[str, object]:
    _require_clean_repository()
    version = _project_version(ROOT)
    commit, source_date_epoch = _source_revision()
    output = output_directory.resolve()
    _prepare_output(output)

    with tempfile.TemporaryDirectory(prefix="contract-holes-release-") as temporary:
        temporary_root = Path(temporary)
        archive = _git_archive()
        sources = [temporary_root / "source-a", temporary_root / "source-b"]
        builds = [temporary_root / "build-a", temporary_root / "build-b"]
        for source, build in zip(sources, builds):
            source.mkdir()
            build.mkdir()
            _extract_source_archive(archive, source)
            _build_distribution(source, build, source_date_epoch)
            _validate_artifacts(build, version)

        first_hashes = _artifact_hashes(builds[0])
        second_hashes = _artifact_hashes(builds[1])
        if first_hashes != second_hashes:
            raise ReleaseError(
                "independent builds were not byte-for-byte reproducible: "
                f"{first_hashes!r} != {second_hashes!r}"
            )

        for name in sorted(first_hashes):
            shutil.copyfile(builds[0] / name, output / name)
        wheel = output / f"contract_holes-{version}-py3-none-any.whl"
        _smoke_test_wheel(wheel, sources[0], version, temporary_root / "smoke")

    release_manifest = {
        "schema_version": "1.0",
        "package": "contract-holes",
        "version": version,
        "source": {
            "commit": commit,
            "source_date_epoch": source_date_epoch,
            "repository_state": "clean",
        },
        "build_environment": _build_environment(),
        "reproducibility": {
            "independent_builds": 2,
            "byte_for_byte_match": True,
            "wheel_smoke_test": "passed",
        },
        "artifacts": [
            {
                "filename": name,
                "sha256": digest,
                "bytes": (output / name).stat().st_size,
            }
            for name, digest in sorted(first_hashes.items())
        ],
    }
    manifest_path = output / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(release_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checksummed = {
        **first_hashes,
        manifest_path.name: _sha256(manifest_path),
    }
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{digest}  {name}\n" for name, digest in sorted(checksummed.items())
        ),
        encoding="ascii",
    )
    return release_manifest


def _project_version(root: Path) -> str:
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (root / "src/contract_holes/__init__.py").read_text(
        encoding="utf-8"
    )
    project_match = VERSION_PATTERN.search(pyproject)
    init_match = INIT_VERSION_PATTERN.search(package_init)
    if project_match is None or init_match is None:
        raise ReleaseError("could not read project/package versions")
    if project_match.group(1) != init_match.group(1):
        raise ReleaseError("pyproject.toml and package versions do not match")
    return project_match.group(1)


def _require_clean_repository() -> None:
    completed = _run_git("status", "--porcelain", "--untracked-files=all")
    if completed.stdout.strip():
        raise ReleaseError("repository must be clean before building a release")


def _source_revision() -> tuple[str, int]:
    completed = _run_git("show", "-s", "--format=%H%n%ct", "HEAD")
    lines = completed.stdout.splitlines()
    if len(lines) != 2 or not lines[0] or not lines[1].isdigit():
        raise ReleaseError("could not resolve source commit and timestamp")
    return lines[0], int(lines[1])


def _git_archive() -> bytes:
    completed = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode(errors="replace").strip()
        raise ReleaseError(f"git archive failed: {detail or 'unknown error'}")
    return completed.stdout


def _extract_source_archive(archive_bytes: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                raise ReleaseError(f"unsafe path in generated Git archive: {member.name}")
        if sys.version_info >= (3, 12):
            archive.extractall(
                destination,
                members=members,
                filter="fully_trusted",
            )
        else:  # pragma: no cover - filter was added after Python 3.10
            archive.extractall(destination, members=members)


def _build_distribution(source: Path, output: Path, epoch: int) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(epoch),
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(output),
        ],
        cwd=source,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        raise ReleaseError(f"package build failed:\n{detail[-8000:]}")


def _validate_artifacts(directory: Path, version: str) -> None:
    expected = {
        f"contract_holes-{version}-py3-none-any.whl",
        f"contract_holes-{version}.tar.gz",
    }
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != expected:
        raise ReleaseError(f"unexpected artifact set: {sorted(actual)!r}")
    _validate_wheel(directory / f"contract_holes-{version}-py3-none-any.whl", version)
    _validate_sdist(directory / f"contract_holes-{version}.tar.gz", version)


def _validate_wheel(path: Path, version: str) -> None:
    metadata_name = f"contract_holes-{version}.dist-info/METADATA"
    required = {
        "contract_holes/__init__.py",
        "contract_holes/cli.py",
        "contract_holes/schemas/report-1.0.schema.json",
        "contract_holes/schemas/sarif-2.1.0-profile.schema.json",
        metadata_name,
        f"contract_holes-{version}.dist-info/entry_points.txt",
    }
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise ReleaseError(f"wheel is missing required files: {sorted(missing)!r}")
        if any(name.endswith((".pyc", ".pyo")) or "__pycache__" in name for name in names):
            raise ReleaseError("wheel contains Python cache artifacts")
        parsed = BytesParser(policy=email_policy).parsebytes(archive.read(metadata_name))
    if parsed.get("Name") != "contract-holes" or parsed.get("Version") != version:
        raise ReleaseError("wheel metadata name/version does not match release")
    requires_python = str(parsed.get("Requires-Python", "")).replace(" ", "")
    if set(requires_python.split(",")) != {">=3.10", "<3.15"}:
        raise ReleaseError("wheel Requires-Python does not match compatibility policy")


def _validate_sdist(path: Path, version: str) -> None:
    prefix = f"contract_holes-{version}/"
    required = {
        f"{prefix}CONTRIBUTING.md",
        f"{prefix}LICENSE",
        f"{prefix}README.md",
        f"{prefix}SECURITY.md",
        f"{prefix}docs/INSTALLATION.md",
        f"{prefix}pyproject.toml",
        f"{prefix}src/contract_holes/schemas/report-1.0.schema.json",
        f"{prefix}tests/test_scanner.py",
    }
    with tarfile.open(path, mode="r:gz") as archive:
        names = set(archive.getnames())
    missing = required - names
    if missing:
        raise ReleaseError(f"sdist is missing required files: {sorted(missing)!r}")
    if any(name.endswith((".pyc", ".pyo")) or "__pycache__" in name for name in names):
        raise ReleaseError("sdist contains Python cache artifacts")


def _smoke_test_wheel(wheel: Path, source: Path, version: str, root: Path) -> None:
    venv.EnvBuilder(with_pip=True, clear=True).create(root)
    scripts = root / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    holes = scripts / ("holes.exe" if os.name == "nt" else "holes")
    _run_checked(
        [str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
        cwd=root,
        label="wheel installation",
    )
    version_output = _run_checked(
        [str(holes), "--version"], cwd=root, label="installed CLI version"
    ).stdout.strip()
    if version_output != f"holes {version}":
        raise ReleaseError(f"installed CLI reported unexpected version {version_output!r}")
    scan = _run_checked(
        [
            str(holes),
            str(source / "tests/fixtures/SafeVault.sol"),
            "--format",
            "json",
        ],
        cwd=root,
        label="installed wheel smoke scan",
    )
    try:
        payload = json.loads(scan.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseError("installed wheel emitted invalid JSON") from exc
    if payload.get("finding_count") != 0 or payload.get("schema_version") != "1.0":
        raise ReleaseError("installed wheel smoke scan returned unexpected results")


def _run_checked(command: list[str], *, cwd: Path, label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        raise ReleaseError(f"{label} failed:\n{detail[-4000:]}")
    return completed


def _artifact_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: _sha256(path)
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file()
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_environment() -> dict[str, object]:
    versions: dict[str, str] = {}
    for package in ("build", "packaging", "pyproject-hooks", "setuptools", "wheel"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "unavailable"
    return {
        "python": ".".join(str(part) for part in sys.version_info[:3]),
        "packages": versions,
        "source_date_epoch": True,
        "pythonhashseed": "0",
    }


def _prepare_output(output: Path) -> None:
    if output.exists() and not output.is_dir():
        raise ReleaseError(f"output path is not a directory: {output}")
    if output.is_dir() and any(output.iterdir()):
        raise ReleaseError(f"refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)


def _run_git(*arguments: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown error"
        raise ReleaseError(f"git {' '.join(arguments)} failed: {detail}")
    return completed


if __name__ == "__main__":
    raise SystemExit(main())
