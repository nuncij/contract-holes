from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from . import __version__
from .benchmark import BenchmarkError, benchmark_exit_status, benchmark_paths
from .inspector import InspectionError, InspectionFilters, inspect_paths
from .models import Severity
from .proofs import ProofGenerationError, generate_foundry_proofs
from .reporters import json_report, sarif_report, text_report
from .scanner import ScanError, Scanner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes",
        description="Scan Solidity contracts for evidence of security vulnerabilities.",
        epilog=(
            "Use 'holes inspect PATH ...' for analysis JSON or "
            "'holes benchmark PATH ...' for repeatable metrics."
        ),
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument("paths", nargs="+", help="Solidity files or directories to scan")
    result.add_argument(
        "--format",
        choices=("text", "json", "sarif"),
        default="text",
        help="output format (default: text)",
    )
    result.add_argument(
        "--minimum-severity",
        metavar="LEVEL",
        default="info",
        choices=tuple(item.name.lower() for item in Severity),
        help="only report findings at or above this severity",
    )
    result.add_argument(
        "--fail-on",
        metavar="LEVEL",
        choices=tuple(item.name.lower() for item in Severity),
        help="exit with status 1 if a finding at or above this severity exists",
    )
    result.add_argument(
        "--include-dependencies",
        action="store_true",
        help="include lib, vendor, node_modules, and generated artifact directories",
    )
    result.add_argument(
        "--compile",
        action="store_true",
        help="compile with Foundry and enable type-aware AST rules",
    )
    result.add_argument(
        "--offline",
        action="store_true",
        help="prevent Foundry from downloading missing compiler versions (requires --compile)",
    )
    result.add_argument(
        "--generate-proofs",
        metavar="DIRECTORY",
        help="write runnable Foundry proof tests for supported findings (requires --compile)",
    )
    result.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    return result


def inspection_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes inspect",
        description="Compile and inspect deterministic Solidity analysis state as JSON.",
    )
    result.add_argument("paths", nargs="+", help="Solidity files or directories to inspect")
    result.add_argument(
        "--file",
        dest="file_filters",
        action="append",
        default=[],
        metavar="PATH",
        help="include source paths ending with PATH (repeatable)",
    )
    result.add_argument(
        "--contract",
        dest="contract_filters",
        action="append",
        default=[],
        metavar="NAME",
        help="include exactly named contracts (repeatable)",
    )
    result.add_argument(
        "--function",
        dest="function_filters",
        action="append",
        default=[],
        metavar="NAME",
        help="include NAME or Contract.NAME callables (repeatable)",
    )
    result.add_argument(
        "--include-dependencies",
        action="store_true",
        help="include dependency directories as explicit inspection targets",
    )
    result.add_argument(
        "--offline",
        action="store_true",
        help="prevent Foundry from downloading missing compiler versions",
    )
    return result


def benchmark_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes benchmark",
        description="Measure scanner correctness, duration, and Python peak memory as JSON.",
    )
    result.add_argument("paths", nargs="+", help="Solidity files or directories to benchmark")
    result.add_argument(
        "--expectations",
        metavar="FILE",
        help="finding-count expectations JSON (defaults to PROJECT/expectations.json)",
    )
    result.add_argument(
        "--baseline",
        metavar="FILE",
        help="compare performance with a prior benchmark JSON without failing on timing",
    )
    result.add_argument(
        "--include-dependencies",
        action="store_true",
        help="include dependency directories as explicit benchmark targets",
    )
    result.add_argument(
        "--offline",
        action="store_true",
        help="prevent Foundry from downloading missing compiler versions",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "inspect":
        return _inspect_main(arguments[1:])
    if arguments and arguments[0] == "benchmark":
        return _benchmark_main(arguments[1:])
    argument_parser = parser()
    args = argument_parser.parse_args(arguments)
    if args.offline and not args.compile:
        argument_parser.error("--offline requires --compile")
    if args.generate_proofs and not args.compile:
        argument_parser.error("--generate-proofs requires --compile")
    scanner = Scanner()
    try:
        findings, files_scanned = scanner.scan_paths(
            args.paths,
            minimum_severity=Severity.parse(args.minimum_severity),
            include_dependencies=args.include_dependencies,
            compile_sources=args.compile,
            compiler_offline=args.offline,
        )
    except ScanError as exc:
        print(f"holes: error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        output = json_report(findings, files_scanned)
    elif args.format == "sarif":
        output = sarif_report(findings, [rule.info for rule in scanner.rules])
    else:
        output = text_report(
            findings,
            files_scanned,
            color=sys.stdout.isatty() and not args.no_color,
        )
    print(output)

    if args.generate_proofs:
        try:
            proofs = generate_foundry_proofs(findings, Path(args.generate_proofs))
        except ProofGenerationError as exc:
            print(f"holes: error: {exc}", file=sys.stderr)
            return 2
        if proofs:
            print(
                f"holes: wrote {len(proofs)} Foundry proof test(s) and requirement "
                f"manifest(s) to {args.generate_proofs}",
                file=sys.stderr,
            )
        else:
            print("holes: no findings have an automatic proof generator", file=sys.stderr)

    if args.fail_on:
        threshold = Severity.parse(args.fail_on)
        if any(finding.severity >= threshold for finding in findings):
            return 1
    return 0


def _inspect_main(argv: Sequence[str]) -> int:
    argument_parser = inspection_parser()
    args = argument_parser.parse_args(argv)
    filters = InspectionFilters.create(
        files=args.file_filters,
        contracts=args.contract_filters,
        functions=args.function_filters,
    )
    try:
        payload = inspect_paths(
            args.paths,
            include_dependencies=args.include_dependencies,
            offline=args.offline,
            filters=filters,
        )
    except InspectionError as exc:
        print(f"holes inspect: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _benchmark_main(argv: Sequence[str]) -> int:
    argument_parser = benchmark_parser()
    args = argument_parser.parse_args(argv)
    try:
        payload = benchmark_paths(
            args.paths,
            include_dependencies=args.include_dependencies,
            offline=args.offline,
            expectations_path=args.expectations,
            baseline_path=args.baseline,
        )
    except BenchmarkError as exc:
        print(f"holes benchmark: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return benchmark_exit_status(payload)
