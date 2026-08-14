# Four bounty targets, 157 candidates, zero vulnerabilities

A negative result, written up because negative results in security tooling
almost never get published.

I spent a week building a Solidity static analyzer and a disciplined workflow for
pointing it at live bug-bounty programs. I then pointed it at four of them. It
produced 157 things worth looking at. I reviewed all 157 by hand and rejected
all 157. Nothing was confirmed, nothing was reported, nothing was submitted.

Then I stopped, because the reason it found nothing is not bad luck.

This document is the part worth keeping. If you are considering building the same
thing, it should save you the week.

## The tool was not a toy

That matters for interpreting the result, so briefly: 13 detectors, 18.5k lines
of dependency-free Python, 9.2k lines of tests, 248 tests passing, frozen JSON
and SARIF output contracts, three signed releases, and live CI.

The analysis is compiler-backed, not regex. It loads solc ASTs, builds a
project-wide index, resolves inheritance through `linearizedBaseContracts`,
builds an internal call graph, and derives reusable data-flow facts (reads,
writes, user-controlled inputs, external interactions, transferred value,
authorization conditions) that the rules consume through a stable API. Detectors
cover reentrancy with interprocedural paths, user-controlled external and
`delegatecall` targets, authorization reachability, signature replay and domain
separation, proxy initialization and storage layout, ERC-20 return and
balance-delta assumptions, and oracle freshness and slippage.

The scan side was equally deliberate. Every target got an immutable pre-scan
freeze: an exact Git revision, a content-bound file manifest, reportable paths
hashed separately from compiler-only dependencies, an exact pinned solc release,
and fail-closed scope enforcement. Compilation ran offline in a fresh temporary
project with library discovery disabled, target configuration never loaded, and
RPC, wallet, and credential variables stripped from the subprocess environment.
Each target was then scanned twice in two independent private workspaces, and the
profile, source manifest, scan, and candidate ledger had to come out
byte-identical before the result counted.

So the null result is not "a weekend script found nothing."

## The four trials

| Target | Reportable files | Candidates | Confirmed |
| --- | ---: | ---: | ---: |
| OpenZeppelin Confidential Contracts `v0.4.0` | 22 | 51, all rejected | 0 |
| Silo Finance v2/v3 | 10 | 81, all rejected | 0 |
| Olas governance `v1.2.5` | 2 | 0 | 0 |
| EulerSwap v2 | 5 | 25, all rejected | 0 |
| **Total** | **39** | **157, all rejected** | **0** |

Exactly one candidate ever reached "investigating," in the first trial. Focused
trust-boundary analysis then rejected that one too: the external call could not
reach an untrusted callback, because the called contract was an immutable
interface-checked deployment setting and every external call in the reported
window's dependency closure targeted deployment-fixed predeploys, that immutable
target, or read-only views.

## Read those 157 carefully

They are not 157 independent observations, and I want to be precise about this
rather than let the headline number do work it cannot support.

They span more than one detector revision, because two precision passes ran
between trials. The 81 Silo candidates came from a source revision the project
itself later invalidated — the program pinned tag `4.26.0` while the deployed
in-scope assets were `3.5.0`, which I only caught during a completion review, at
which point I discarded the whole result and marked that trial unsatisfied. Two
of the four scopes were very small.

So this does not measure recall, and it absolutely does not show that these four
protocols are free of vulnerabilities.

What it does measure is operator utility, and that is the number that ended the
project: roughly one working day per target, 157 human review decisions, one
temporary lead, zero reports. The tool's output was review work. For a bounty
hunter, that is negative time value.

## Why zero — the structural argument

The detectors recognize *local primitives*: this call precedes that state write,
this target is user-controlled, this privileged write lacks a dominating
authorization check. Deciding whether such a pattern is a *vulnerability*
requires trust boundaries, deployment state, protocol semantics, and economic
invariants. The rule implementations say so in their own metadata — every rule
carries an explicit manual-review boundary.

Two precision passes proved the difference between volume and yield. They cut
Silo's candidates from 81 to 59 by teaching the analyzer that read-only view
calls do not form reentrancy paths, that freshly created clones are not
attacker-selected targets, and that timelock-style guards protect the write that
follows. Real improvements. The next untouched target still produced 25
candidates and 25 rejections, all of them landing inside boundaries the previous
pass had already documented as intentional. Tuning made the output smaller
without making it truer.

The clearest evidence was sitting in the project's own evaluation corpus, and I
had built it before I understood what it was telling me. It holds ten real
disclosed vulnerabilities from ten projects, with labels frozen before any
scanner result was measured, and a calibration/holdout split. Five cases are
labelled out-of-model:

| Out of model | Root cause |
| --- | --- |
| Enzyme 2021 | Integration priced shares from total net asset value |
| Nomad 2022 | Initialization pre-approved the zero root |
| Belt 2021 | Strategy balance accounting error |
| Beanstalk 2022 | Voting power acquired with flash-loaned assets |
| Euler 2023 | `donateToReserves` could make an account unhealthy |

The five in-model cases collapse to about three families: Parity 2017, Wormhole
2022, and Harvest 2021 are all uninitialized implementation or proxy
initialization; Cream 2021 is reentrancy; and the Aurora 2022 case is a
supported *signal* only, since the scanner flags a hardcoded `delegatecall`
address without discovering the inflation mechanism.

Look at the split. What this class of tool reaches is uninitialized proxies and
reentrancy: textbook classes from 2017–2022, already covered by free tooling with
far more detectors, and squeezed out of audited code long before it sits behind a
bounty. What it does not reach is accounting, pricing, verification logic, and
governance economics — which is where current programs concentrate their value.

That gap is the whole result. My corpus predicted the outcome of my trials and I
did not read it that way until after the fourth one.

## Where this sits against free tooling

Slither ships 101 detectors with a mature IR, CFG/SSA, and taint APIs. Aderyn
covers the same headline classes with more breadth, speed, and adoption. My
13 detectors overlap their standard sets almost entirely.

Against lighter tooling — Semgrep, whose Solidity support is still experimental,
and contest-oriented report generators — this project is ahead on semantic depth
and deterministic evidence. That is not a moat while Slither and Aderyn exist.

Against LLM-assisted review, it is ahead on reproducibility, privacy, and
deterministic traces, and behind on specifications, cross-component intent,
economic invariants, and hypothesis generation. Which is to say: behind on
exactly the out-of-model half of the table above.

## What I would keep

Not the analyzer. Maintaining a private Solidity IR makes little sense when
Slither exposes one; the detector *ideas* would be better ported onto Slither or
Aderyn than reimplemented.

The transferable part is the discipline, and I would use it again on any research
project where I might fool myself:

**Freeze before you measure.** Pin an exact revision, hash the file set, pin the
exact compiler, and record the scope before the first run. This turns "the tool
found something" into a claim someone else can check.

**Make replay a gate, not a hope.** Two independent workspaces had to produce
byte-identical manifests, scans, and candidate ledgers. When the EulerSwap scan
failed, it failed identically twice, which is what let me treat the failure as a
fact about the tool rather than noise.

**Fail closed on scope.** Findings could originate only from approved reportable
paths. Compiler-only dependencies were separately hashed and could never produce
a candidate. Undeclared imports stopped the compile rather than quietly widening
what got analysed.

**Separate observation from judgment.** Scanner output was immutable. Human
review states lived in a separate ledger with a tested transition table, and no
scanner result, ranking, or AI explanation could promote a candidate to
confirmed. Rejections required a reason; confirmations required reviewer
reasoning and an impact statement.

**Freeze evaluation labels before you look at results, and keep the labels that
hurt.** Out-of-model cases stayed in the corpus and dragged the headline number
down. That is the only reason the corpus was able to tell me the truth. Also
worth writing down, in the contributing guide, that a perfect score on
checked-in fixtures is a regression result and not an accuracy claim — and then
believing it when it becomes inconvenient.

**Record failures as results.** Two trials produced blockers rather than
findings: the Silo version mismatch and a compile failure on EulerSwap. Both are
in the repository as UNSATISFIED verdicts with evidence. The temptation to move a
goalpost is strongest exactly when a result is embarrassing, and a project that
never records a failure is not measuring anything.

## The experiment that would settle it

This design is not mine. Before closing the project I put the measurements to an
independent second reviewer, OpenAI Codex, without showing it my own conclusion.
It reached the same verdict, corrected my framing of the headline number, and
proposed a sharper test than the one I had. Mine was "if any candidate had ever
survived review to confirmed, keep going." Its version is better because it does
not depend on my luck with four targets:

Take complete, exact historical vulnerable repositories with matched clean
revisions. Have the root causes labelled independently and withheld. Score
against Slither, Aderyn, and an LLM-assisted reviewer on actionable root-cause
discovery and on review time.

Recovering the actual root causes would mean a small-sample problem and the work
should continue. Better out-of-sample precision without root causes would mean a
tuning problem. Generic signals without root causes would confirm the ceiling.

## If you are about to build this

Don't add detectors. The marginal detector lands in the half of the table that
free tools already cover.

If you want to find the bugs that pay, change the target class rather than the
rule count: pick one protocol vertical such as lending or vault accounting,
derive economic invariants manually or with a model, and verify them with
Foundry stateful and differential tests. Reuse a freeze-and-replay harness like
the one above so your results stay checkable. That is a different project, and
it is the one I would start if I started again.

And keep an honest corpus. Mine told me the answer before the trials did.

---

*Scope and conduct: all four trials ran locally and offline against public
pinned source. No RPC, fork, chain action, transaction, deployment, proof
execution against a live system, report, export, disclosure, submission,
bounty-platform write, or target contact occurred at any point, and target
build, test, and deployment scripts were never executed. No vulnerability was
found, so nothing is disclosed here; the programs' rules restrict public
disclosure of bugs, of which there are none. Target source, file manifests,
scans, candidate identities, and review records stayed outside this repository
throughout. The full decision record is in
[the closeout](PROJECT_CLOSEOUT.md).*
