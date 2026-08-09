from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
import json
import os
from pathlib import Path
import sys

from . import __version__
from .address_source import AddressSourceError, fetch_and_write_verified_source
from .ai_triage import AITriageError, explain_report, prepare_evidence_bundle
from .benchmark import BenchmarkError, benchmark_exit_status, benchmark_paths
from .bounty_candidates import (
    BountyCandidateError,
    REVIEW_STATES,
    list_candidates,
    review_candidate,
    synchronize_candidates,
)
from .bounty_profile import (
    BountyProfileError,
    initialize_bounty_workspace,
    load_bounty_profile,
)
from .bounty_scope import BountyScopeError, identify_source, scan_bounty_workspace
from .baseline import (
    BaselineError,
    compare_baseline,
    load_baseline,
    write_baseline,
)
from .catalog import CatalogError, catalog_payload, json_catalog, text_catalog
from .compatibility import compatibility_payload
from .config import (
    ConfigError,
    HolesConfig,
    discover_config,
    load_config,
    selected_rules,
)
from .evaluation import (
    EvaluationError,
    evaluate_labelled_corpus,
    evaluation_exit_status,
)
from .inspector import InspectionError, InspectionFilters, inspect_paths
from .models import Severity
from .proofs import ProofGenerationError, generate_foundry_proofs
from .proof_runner import (
    ProofRunnerError,
    proof_runner_exit_status,
    run_foundry_proofs,
)
from .reporters import json_report, sarif_report, text_report
from .scanner import ScanError, Scanner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes",
        description="Scan Solidity contracts for evidence of security vulnerabilities.",
        epilog=(
            "Use 'holes inspect PATH ...' for analysis JSON or "
            "'holes benchmark PATH ...' for repeatable metrics. Run generated "
            "bundles with 'holes proofs DIRECTORY'. Fetch verified source with "
            "'holes fetch CHAIN_ID ADDRESS --output DIRECTORY', or annotate a "
            "JSON report with 'holes explain REPORT'. Run 'holes compatibility' "
            "to inspect supported and observed tool versions. Create an "
            "authorized local research workspace with 'holes bounty init'."
        ),
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    result.add_argument(
        "paths",
        nargs="*",
        help="Solidity files or directories (defaults to scan.paths in .holes.toml)",
    )
    config_group = result.add_mutually_exclusive_group()
    config_group.add_argument(
        "--config",
        metavar="FILE",
        help="use FILE instead of discovering .holes.toml",
    )
    config_group.add_argument(
        "--no-config",
        action="store_true",
        help="do not discover or load .holes.toml",
    )
    result.add_argument(
        "--format",
        choices=("text", "json", "sarif"),
        default="text",
        help="output format (default: text)",
    )
    result.add_argument(
        "--minimum-severity",
        metavar="LEVEL",
        default=None,
        choices=tuple(item.name.lower() for item in Severity),
        help="only report findings at or above this severity (overrides config)",
    )
    result.add_argument(
        "--fail-on",
        metavar="LEVEL",
        choices=tuple(item.name.lower() for item in Severity),
        help="exit with status 1 if a finding at or above this severity exists",
    )
    baseline_group = result.add_mutually_exclusive_group()
    baseline_group.add_argument(
        "--baseline",
        metavar="FILE",
        help="report and gate only findings absent from FILE",
    )
    baseline_group.add_argument(
        "--write-baseline",
        metavar="FILE",
        help="create a new fingerprint baseline and refuse to overwrite",
    )
    baseline_group.add_argument(
        "--update-baseline",
        metavar="FILE",
        help="replace FILE with fingerprints from the current scan",
    )
    dependency_group = result.add_mutually_exclusive_group()
    dependency_group.add_argument(
        "--include-dependencies",
        dest="include_dependencies",
        action="store_true",
        default=None,
        help="include lib, vendor, node_modules, and generated artifact directories",
    )
    dependency_group.add_argument(
        "--exclude-dependencies",
        dest="include_dependencies",
        action="store_false",
        help=(
            "exclude dependency and generated directories even if config "
            "includes them"
        ),
    )
    result.add_argument(
        "--exclude",
        dest="exclude_patterns",
        action="append",
        default=None,
        metavar="GLOB",
        help="exclude paths matching GLOB (repeatable; replaces config excludes)",
    )
    compile_group = result.add_mutually_exclusive_group()
    compile_group.add_argument(
        "--compile",
        dest="compile",
        action="store_true",
        default=None,
        help="compile with Foundry and enable type-aware AST rules",
    )
    compile_group.add_argument(
        "--no-compile",
        dest="compile",
        action="store_false",
        help="use source-only analysis even if config enables compilation",
    )
    network_group = result.add_mutually_exclusive_group()
    network_group.add_argument(
        "--offline",
        dest="offline",
        action="store_true",
        default=None,
        help="prevent Foundry from downloading missing compiler versions",
    )
    network_group.add_argument(
        "--online",
        dest="offline",
        action="store_false",
        help="allow Foundry compiler downloads even if config selects offline mode",
    )
    result.add_argument(
        "--generate-proofs",
        metavar="DIRECTORY",
        help="write runnable Foundry proof tests for supported findings (requires --compile)",
    )
    result.add_argument(
        "--max-files",
        type=int,
        metavar="COUNT",
        help="maximum Solidity source files (overrides config)",
    )
    result.add_argument(
        "--max-source-bytes",
        type=int,
        metavar="BYTES",
        help="maximum total Solidity source bytes (overrides config)",
    )
    result.add_argument(
        "--compiler-timeout",
        type=float,
        metavar="SECONDS",
        help="maximum Foundry compilation time (overrides config)",
    )
    result.add_argument(
        "--scan-timeout",
        type=float,
        metavar="SECONDS",
        help="maximum total scan time (overrides config)",
    )
    result.add_argument(
        "--max-memory-mb",
        type=int,
        metavar="MIB",
        help="maximum Python peak allocated memory (overrides config)",
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


def proof_runner_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes proofs",
        description="Run generated proof bundles in isolated Foundry projects.",
    )
    result.add_argument("directory", help="directory containing .proof.json bundles")
    result.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="maximum runtime per artifact (default: 60)",
    )
    result.add_argument(
        "--allow-downloads",
        action="store_true",
        help="allow Foundry to download a missing compiler (offline by default)",
    )
    return result


def rules_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes rules",
        description="Show detector examples, remediation, and references.",
    )
    result.add_argument(
        "rule_id",
        nargs="?",
        help="show one rule such as SOL005 (default: all rules)",
    )
    result.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="catalog output format (default: text)",
    )
    return result


def fetch_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes fetch",
        description="Fetch verified Solidity source from Etherscan V2 with provenance.",
    )
    result.add_argument("chain_id", help="positive EVM chain ID, such as 1 or 8453")
    result.add_argument("address", help="deployed 0x-prefixed contract address")
    result.add_argument(
        "--output",
        required=True,
        metavar="DIRECTORY",
        help="new directory for source files and provenance.json",
    )
    result.add_argument(
        "--api-key-env",
        default="ETHERSCAN_API_KEY",
        metavar="NAME",
        help="environment variable containing the API key (default: ETHERSCAN_API_KEY)",
    )
    result.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="HTTP request timeout (default: 30)",
    )
    return result


def explain_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes explain",
        description=(
            "Correlate scanner findings deterministically and optionally add "
            "evidence-bound OpenAI explanations."
        ),
    )
    result.add_argument("report", help="Contract Holes JSON report")
    result.add_argument(
        "--prepare",
        action="store_true",
        help="emit the deterministic evidence bundle without an API request",
    )
    result.add_argument(
        "--model",
        default="gpt-5.6-luna",
        help="OpenAI Responses API model (default: gpt-5.6-luna)",
    )
    result.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        metavar="NAME",
        help="environment variable containing the API key (default: OPENAI_API_KEY)",
    )
    result.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="OpenAI request timeout (default: 60)",
    )
    return result


def evaluation_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes evaluate",
        description="Measure per-rule precision and recall on a labelled corpus.",
    )
    result.add_argument("manifest", help="versioned evaluation manifest JSON")
    result.add_argument(
        "--allow-downloads",
        action="store_true",
        help="allow Foundry to download the pinned compiler (offline by default)",
    )
    return result


def compatibility_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="holes compatibility",
        description="Report supported and locally observed toolchain versions as JSON.",
    )


def bounty_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="holes bounty",
        description=(
            "Manage a private, human-approved bounty research workspace. "
            "Commands never submit reports or send transactions."
        ),
    )
    commands = result.add_subparsers(dest="bounty_command", required=True)
    initialize = commands.add_parser(
        "init",
        help="create a new private bounty workspace",
        description="Create a new private bounty workspace outside the target tree.",
    )
    initialize.add_argument("workspace", help="new workspace directory")
    initialize.add_argument("--program", required=True, help="program/project name")
    initialize.add_argument("--platform", required=True, help="bounty platform name")
    initialize.add_argument(
        "--rules-url", required=True, help="HTTPS URL for the reviewed program rules"
    )
    initialize.add_argument(
        "--reviewed-on", required=True, metavar="YYYY-MM-DD", help="rules review date"
    )
    initialize.add_argument(
        "--authorized",
        action="store_true",
        help="acknowledge authorization and the selected program rules",
    )
    initialize.add_argument(
        "--authorization-note",
        required=True,
        help="short record of why local analysis is authorized",
    )
    initialize.add_argument(
        "--source", required=True, help="local target source directory"
    )
    identity = initialize.add_mutually_exclusive_group(required=True)
    identity.add_argument(
        "--revision",
        help="exact lowercase 40- or 64-hex Git commit",
    )
    identity.add_argument(
        "--content-sha256",
        help="lowercase SHA-256 identity for a non-Git directory manifest",
    )
    initialize.add_argument(
        "--scope",
        action="append",
        required=True,
        metavar="PATH",
        help="approved relative source path (repeatable)",
    )
    initialize.add_argument(
        "--impact",
        action="append",
        required=True,
        metavar="TEXT",
        help="in-scope impact description (repeatable)",
    )
    initialize.add_argument(
        "--restriction",
        action="append",
        default=[],
        metavar="TEXT",
        help="program restriction (repeatable)",
    )
    initialize.add_argument(
        "--source-only",
        action="store_true",
        help="disable compiler analysis; bounty compiler mode is offline by default",
    )

    validate = commands.add_parser(
        "validate",
        help="validate an existing bounty profile",
        description="Validate bounty.toml and emit its normalized identity as JSON.",
    )
    validate.add_argument("workspace", help="workspace directory or bounty.toml")
    identify = commands.add_parser(
        "identify",
        help="compute a deterministic local source-set identity",
        description=(
            "Hash approved local Solidity paths and safe remappings without "
            "scanning or using the network."
        ),
    )
    identify.add_argument("source", help="local source root")
    identify.add_argument(
        "--scope",
        action="append",
        required=True,
        metavar="PATH",
        help="approved relative source path (repeatable)",
    )
    scan = commands.add_parser(
        "scan",
        help="validate scope and scan approved local source",
        description=(
            "Validate immutable source identity, stage only approved sources, "
            "and run an offline scan."
        ),
    )
    scan.add_argument("workspace", help="bounty workspace directory")
    candidates = commands.add_parser(
        "candidates",
        help="list ranked candidates and human review state",
        description=(
            "List immutable scan candidates with transparent review-priority "
            "components and separate human review state."
        ),
    )
    candidates.add_argument("workspace", help="bounty workspace directory")
    candidates.add_argument(
        "--state",
        action="append",
        choices=tuple(sorted(REVIEW_STATES)),
        default=[],
        help="include only a review state (repeatable)",
    )
    review = commands.add_parser(
        "review",
        help="record an explicit human candidate decision",
        description=(
            "Record an auditable human state transition. Approval is handled "
            "separately by the report workflow."
        ),
    )
    review.add_argument("workspace", help="bounty workspace directory")
    review.add_argument("candidate_id", help="stable BNT- candidate ID")
    review.add_argument(
        "--state",
        required=True,
        choices=("investigating", "rejected", "confirmed"),
        help="new human review state",
    )
    review.add_argument("--reason", required=True, help="review reasoning")
    review.add_argument("--reviewer", required=True, help="reviewer identity label")
    review.add_argument(
        "--impact",
        help="confirmed in-scope impact (required for confirmed)",
    )
    review.add_argument(
        "--at",
        dest="occurred_at",
        metavar="RFC3339",
        help="event time (defaults to current UTC time)",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "inspect":
        return _inspect_main(arguments[1:])
    if arguments and arguments[0] == "benchmark":
        return _benchmark_main(arguments[1:])
    if arguments and arguments[0] == "proofs":
        return _proof_runner_main(arguments[1:])
    if arguments and arguments[0] == "rules":
        return _rules_main(arguments[1:])
    if arguments and arguments[0] == "fetch":
        return _fetch_main(arguments[1:])
    if arguments and arguments[0] == "explain":
        return _explain_main(arguments[1:])
    if arguments and arguments[0] == "evaluate":
        return _evaluate_main(arguments[1:])
    if arguments and arguments[0] == "compatibility":
        return _compatibility_main(arguments[1:])
    if arguments and arguments[0] == "bounty":
        return _bounty_main(arguments[1:])
    argument_parser = parser()
    args = argument_parser.parse_args(arguments)
    try:
        configuration = _scan_configuration(args)
    except ConfigError as exc:
        print(f"holes: error: {exc}", file=sys.stderr)
        return 2
    scan_paths = list(args.paths) or list(configuration.paths)
    if not scan_paths:
        print(
            "holes: error: no scan paths; pass PATH or configure scan.paths",
            file=sys.stderr,
        )
        return 2
    minimum_severity = (
        Severity.parse(args.minimum_severity)
        if args.minimum_severity is not None
        else configuration.minimum_severity
    )
    include_dependencies = (
        args.include_dependencies
        if args.include_dependencies is not None
        else configuration.include_dependencies
    )
    exclude_patterns = (
        tuple(args.exclude_patterns)
        if args.exclude_patterns is not None
        else configuration.exclude
    )
    compile_sources = (
        args.compile if args.compile is not None else configuration.compiler_enabled
    )
    compiler_offline = (
        args.offline if args.offline is not None else configuration.compiler_offline
    )
    if args.compile is False and args.offline is None:
        compiler_offline = False
    if compiler_offline and not compile_sources:
        argument_parser.error("--offline requires --compile")
    if args.generate_proofs and not compile_sources:
        argument_parser.error("--generate-proofs requires --compile")
    limit_changes: dict[str, int | float] = {}
    if args.max_files is not None:
        limit_changes["max_files"] = args.max_files
    if args.max_source_bytes is not None:
        limit_changes["max_source_bytes"] = args.max_source_bytes
    if args.compiler_timeout is not None:
        limit_changes["compiler_timeout_seconds"] = args.compiler_timeout
    if args.scan_timeout is not None:
        limit_changes["scan_timeout_seconds"] = args.scan_timeout
    if args.max_memory_mb is not None:
        limit_changes["max_python_memory_bytes"] = args.max_memory_mb * 1024 * 1024
    try:
        limits = replace(configuration.limits, **limit_changes)
    except ValueError as exc:
        print(f"holes: error: {exc}", file=sys.stderr)
        return 2
    scanner = Scanner(
        rules=selected_rules(configuration),
        severity_overrides=configuration.severity_overrides,
        limits=limits,
    )
    try:
        findings, files_scanned = scanner.scan_paths(
            scan_paths,
            minimum_severity=minimum_severity,
            include_dependencies=include_dependencies,
            exclude_patterns=exclude_patterns,
            compile_sources=compile_sources,
            compiler_offline=compiler_offline,
        )
    except ScanError as exc:
        print(f"holes: error: {exc}", file=sys.stderr)
        return 2

    baseline_summary: dict[str, object] | None = None
    try:
        if args.baseline:
            baseline = load_baseline(args.baseline)
            comparison = compare_baseline(findings, baseline, args.baseline)
            findings = list(comparison.new_findings)
            summary = comparison.summary()
            baseline_summary = {"path": str(Path(args.baseline)), **summary}
            print(
                "holes: baseline comparison: "
                f"{summary['new']} new, {summary['existing']} existing, "
                f"{summary['resolved']} resolved",
                file=sys.stderr,
            )
        elif args.write_baseline or args.update_baseline:
            baseline_path = args.write_baseline or args.update_baseline
            payload = write_baseline(
                findings,
                baseline_path,
                overwrite=bool(args.update_baseline),
            )
            print(
                f"holes: wrote {len(payload['findings'])} fingerprint(s) to "
                f"{baseline_path}",
                file=sys.stderr,
            )
    except BaselineError as exc:
        print(f"holes: error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        output = json_report(
            findings,
            files_scanned,
            baseline=baseline_summary,
        )
    elif args.format == "sarif":
        output = sarif_report(findings, scanner.rule_infos)
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


def _scan_configuration(args: argparse.Namespace) -> HolesConfig:
    if args.no_config:
        return HolesConfig()
    path = Path(args.config).resolve() if args.config else discover_config()
    if path is None and args.paths:
        candidates = {
            candidate
            for raw_path in args.paths
            if (candidate := discover_config(Path(raw_path))) is not None
        }
        if len(candidates) > 1:
            raise ConfigError(
                "scan paths belong to multiple .holes.toml projects; use --config"
            )
        path = next(iter(candidates), None)
    return load_config(path) if path is not None else HolesConfig()


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


def _proof_runner_main(argv: Sequence[str]) -> int:
    argument_parser = proof_runner_parser()
    args = argument_parser.parse_args(argv)
    try:
        payload = run_foundry_proofs(
            args.directory,
            timeout_seconds=args.timeout,
            allow_downloads=args.allow_downloads,
        )
    except ProofRunnerError as exc:
        print(f"holes proofs: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return proof_runner_exit_status(payload)


def _rules_main(argv: Sequence[str]) -> int:
    argument_parser = rules_parser()
    args = argument_parser.parse_args(argv)
    try:
        payload = catalog_payload(args.rule_id)
    except CatalogError as exc:
        print(f"holes rules: error: {exc}", file=sys.stderr)
        return 2
    print(json_catalog(payload) if args.format == "json" else text_catalog(payload))
    return 0


def _fetch_main(argv: Sequence[str]) -> int:
    argument_parser = fetch_parser()
    args = argument_parser.parse_args(argv)
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        print(
            f"holes fetch: error: environment variable {args.api_key_env} is not set",
            file=sys.stderr,
        )
        return 2
    try:
        payload = fetch_and_write_verified_source(
            args.chain_id,
            args.address,
            api_key,
            args.output,
            timeout_seconds=args.timeout,
        )
    except AddressSourceError as exc:
        print(f"holes fetch: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _explain_main(argv: Sequence[str]) -> int:
    argument_parser = explain_parser()
    args = argument_parser.parse_args(argv)
    try:
        if args.prepare:
            payload = prepare_evidence_bundle(args.report)
        else:
            api_key = os.environ.get(args.api_key_env, "")
            if not api_key:
                print(
                    "holes explain: error: environment variable "
                    f"{args.api_key_env} is not set",
                    file=sys.stderr,
                )
                return 2
            payload = explain_report(
                args.report,
                api_key,
                model=args.model,
                timeout_seconds=args.timeout,
            )
    except AITriageError as exc:
        print(f"holes explain: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _evaluate_main(argv: Sequence[str]) -> int:
    argument_parser = evaluation_parser()
    args = argument_parser.parse_args(argv)
    try:
        payload = evaluate_labelled_corpus(
            args.manifest,
            offline=not args.allow_downloads,
        )
    except EvaluationError as exc:
        print(f"holes evaluate: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return evaluation_exit_status(payload)


def _compatibility_main(argv: Sequence[str]) -> int:
    argument_parser = compatibility_parser()
    argument_parser.parse_args(argv)
    print(json.dumps(compatibility_payload(), indent=2, sort_keys=True))
    return 0


def _bounty_main(argv: Sequence[str]) -> int:
    argument_parser = bounty_parser()
    args = argument_parser.parse_args(argv)
    try:
        if args.bounty_command == "init":
            profile = initialize_bounty_workspace(
                args.workspace,
                program_name=args.program,
                platform=args.platform,
                rules_url=args.rules_url,
                reviewed_on=args.reviewed_on,
                authorization_acknowledged=args.authorized,
                authorization_note=args.authorization_note,
                source_root=args.source,
                source_revision=args.revision,
                source_content_sha256=args.content_sha256,
                scope_paths=args.scope,
                impacts=args.impact,
                restrictions=args.restriction,
                compiler_enabled=not args.source_only,
            )
            command = "bounty.init"
            status = "created"
            payload: dict[str, object] = {
                "schema_version": "1.0",
                "command": command,
                "status": status,
                "workspace": str(profile.workspace),
                "profile": profile.normalized_payload(),
            }
        elif args.bounty_command == "validate":
            profile = load_bounty_profile(args.workspace)
            command = "bounty.validate"
            status = "valid"
            payload = {
                "schema_version": "1.0",
                "command": command,
                "status": status,
                "workspace": str(profile.workspace),
                "profile": profile.normalized_payload(),
            }
        elif args.bounty_command == "identify":
            identity = identify_source(args.source, args.scope)
            payload = {
                "schema_version": "1.0",
                "command": "bounty.identify",
                "status": "identified",
                "source": identity.public_payload(),
            }
        else:
            if args.bounty_command == "scan":
                result = scan_bounty_workspace(args.workspace)
                synchronize_candidates(args.workspace)
                payload = result.scan_record
            elif args.bounty_command == "candidates":
                payload = list_candidates(args.workspace, states=args.state)
            else:
                review = review_candidate(
                    args.workspace,
                    args.candidate_id,
                    state=args.state,
                    reason=args.reason,
                    reviewer=args.reviewer,
                    impact=args.impact,
                    occurred_at=args.occurred_at,
                )
                payload = {
                    "schema_version": "1.0",
                    "command": "bounty.review",
                    "status": "recorded",
                    "review": review,
                }
    except (BountyProfileError, BountyScopeError, BountyCandidateError) as exc:
        print(f"holes bounty: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
