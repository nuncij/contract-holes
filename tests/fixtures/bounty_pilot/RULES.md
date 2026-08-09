# Contract Holes authorized pilot rules 1.0

This repository-owned fixture may be analyzed locally for the M7 end-to-end
pilot. The authorization covers only `target/src/AuthorizedPilotVault.sol` at
the content identity recorded in `manifest.json`.

Allowed activity:

- local source-only static analysis;
- private candidate review and local proof decisions;
- private report drafting, approval, and local export.

Prohibited activity:

- contacting any third-party target or bounty platform;
- mainnet or public-testnet execution;
- remote RPC, wallet, email, upload, disclosure, or submission actions;
- treating the fixture as a real bounty or payout opportunity.

The fixture intentionally contains one authorization flaw and one benign
best-effort call that should be rejected during human triage. Any submission is
outside this pilot and remains a separate manual decision.
