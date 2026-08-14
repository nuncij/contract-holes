# Documentation

## Start here

- [Installation](INSTALLATION.md)
- [CLI reference](CLI_REFERENCE.md)
- [Configuration](CONFIGURATION.md)
- [Rule catalog](RULE_CATALOG.md)
- [Secure-use guide](SECURE_USE.md)

## Team workflow

- [Finding baselines](BASELINES.md)
- [CI and SARIF](CI.md)
- [Resource limits](RESOURCE_LIMITS.md)
- [Output compatibility](OUTPUT_COMPATIBILITY.md)
- [Toolchain compatibility](COMPATIBILITY.md)
- [Release process](RELEASING.md)
- [Release checklist contract](RELEASE_CHECKLIST.md)
- [GitHub operations](GITHUB_OPERATIONS.md)

## Evidence and verification

- [Compiler analysis and proof requirements](PROOF_REQUIREMENTS.md)
- [Precision and recall evaluation](EVALUATION.md)
- [Verified-source ingestion](VERIFIED_SOURCE.md)
- [Evidence-bound AI triage](AI_TRIAGE.md)
- [Bounty workspace and profile](BOUNTY_PROFILE.md)
- [Bounty candidate triage](BOUNTY_TRIAGE.md)
- [Bounty proofs, reports, approval, and export](BOUNTY_PROOFS_REPORTS.md)
- [Historical bounty evaluation](BOUNTY_HISTORY.md)
- [Authorized end-to-end bounty pilot](BOUNTY_PILOT.md)
- [M7 Bounty Hunter Mode plan](BOUNTY_HUNTER_PLAN.md)
- [M8 external target selection](research/M8_TARGET_SELECTION.md)
- [M8 OpenZeppelin trial evaluation](research/M8_OPENZEPPELIN_TRIAL.md)
- [PILOT-007 independent target selection](research/PILOT_007_TARGET_SELECTION.md)
- [PILOT-007 evaluation](research/PILOT_007_EVALUATION.md)
- [PILOT-007 development and completion-repair plan](PILOT_007_PLAN.md) —
  `REPAIR-007` completed the scanner reproduction, regressions, and status text
- [PILOT-008 development plan](PILOT_008_PLAN.md) — independent target trial
  completed with an exact deployed-source mapping
- [PILOT-008 target selection](research/PILOT_008_TARGET_SELECTION.md) — Olas
  governance subset and pre-acquisition evidence
- [PILOT-008 evaluation](research/PILOT_008_EVALUATION.md) — reproducible Olas
  scan result and compiler-pin follow-up
- [COMP-004 development plan](COMP_004_PLAN.md) — exact compiler version in
  bounty profiles (complete, including the private pinned Olas replay)
- [COMP-005 development plan](COMP_005_PLAN.md) — deterministic direct-library
  remapping repair at the isolated compiler boundary and the completed frozen
  PILOT-009 replay

## Project governance

- [Development plan](DEVELOPMENT_PLAN.md)
- [PRECISION-001 development plan](PRECISION_001_PLAN.md)
- [PRECISION-002 development plan](PRECISION_002_PLAN.md) — complete at commit
  `2574b6e`. GitHub CI run `31720097982` passed
- [PILOT-009 development plan](PILOT_009_PLAN.md) — completed validation of
  commit `2574b6e` on the EulerSwap v2 Ethereum subset after the generic
  `COMP-005` direct-library remapping repair
- [PILOT-009 target selection](research/PILOT_009_TARGET_SELECTION.md) —
  public pre-acquisition mapping record for the selected EulerSwap v2 subset
- [PILOT-009 evaluation](research/PILOT_009_EVALUATION.md) — completed trial:
  repaired compiler replays the frozen closure twice with matching identities
  and all candidates are reviewed privately
- [Next-session starter prompt](NEXT_SESSION_PROMPT.md) — coordinator handoff
  for OpenCode with `opencode-go/deepseek-v4-flash`, followed by independent
  verification
- [Threat model](THREAT_MODEL.md)
- [Security policy](../SECURITY.md)
- [Contributing](../CONTRIBUTING.md)
- [Task tracker](../TASKS.md)
- [Changelog](../CHANGELOG.md)

Command help from the installed version is canonical when it differs from prose:

```bash
holes --help
holes COMMAND --help
```
