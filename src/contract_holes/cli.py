from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from . import __version__
from .models import Severity
from .reporters import json_report, sarif_report, text_report
from .scanner import ScanError, Scanner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes",
        description="Scan Solidity contracts for evidence of security vulnerabilities.",
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
    result.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    scanner = Scanner()
    try:
        findings, files_scanned = scanner.scan_paths(
            args.paths,
            minimum_severity=Severity.parse(args.minimum_severity),
            include_dependencies=args.include_dependencies,
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

    if args.fail_on:
        threshold = Severity.parse(args.fail_on)
        if any(finding.severity >= threshold for finding in findings):
            return 1
    return 0

