# Next-session starter prompt

There is no next session. **The project is closed as of 2026-08-14** at the
signed `1.1.1` release, with no queued task and none planned.

If you are an agent or a future reader looking for work to continue here: there
is none. Do not select a task, do not start a trial, and do not add detectors.
Read [the closeout record](PROJECT_CLOSEOUT.md) first. It states the decision,
the measured evidence behind it, which components are worth reusing, which are
sunk, and the only two conditions under which reopening the repository would be
justified.

The standing boundaries still apply to the archived repository:

- Only scan contracts you own or are explicitly authorized to assess.
- No target source, manifest, scan, candidate, review, path, excerpt, or hash
  from any private trial may enter this repository.
- The four trial targets were never contacted and no finding was ever disclosed.
  Nothing in this repository authorizes changing that.

## Final public state

- Release `1.1.1`; three signed tag objects (`v1.0.0`, `v1.1.0`, `v1.1.1`), the
  latter two published as verified private GitHub releases.
- Suite: 248 tests. Frozen audit: 33 positive and 31 safe labels at 1.0.
- Historical gate: 0.933333 candidate precision, 1.0 supported-class recall, 1.0
  evidence completeness, result hash
  `9bf60837d252bac17ba579c91a04a8d33fc5f0c9fcb5c8df59402be0397bdf90`, decision
  `go` — measured on locally authored reductions, not production deployments.
- Four authorized real-world trials: 39 reportable files, 157 candidates, 157
  rejections, 0 confirmed, 0 reports, 0 submissions, 0 disclosures.
- `PILOT-007` (Silo) remains **UNSATISFIED** and will not be resumed.

Reproduce the public gates from a clean checkout with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes bounty history \
  tests/fixtures/bounty_history/manifest.json
git diff --check
```
