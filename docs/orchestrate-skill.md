# Where the orchestrate skill's guidance comes from

The [orchestrate skill](../plugins/opus-orchestrator/skills/orchestrate/SKILL.md) holds only guidance that closes a gap the [baseline round](baseline-round.md) or the [skill round](skill-round.md) showed, or that the spec (issue #1) requires as a prose rule ([ADR 0001](adr/0001-free-method-explicit-interface-invariants-in-code.md)). This table traces each piece to its source, for issues #12 and #13. When either side ships a new model, the test cases are rerun and a piece whose gap no longer shows is pruned.

"Gap" means a numbered gap in the baseline round unless the skill round is named; "story" means a user story in the spec. The wrapper mechanics carried over from the minimal pointer are the interface to the wrapper, specified in the spec's Implementation Decisions.

| Skill section | Guidance | Source |
| --- | --- | --- |
| Opening | The Orchestrator keeps the user, decisions, task parts, integration, acceptance and commits | Stories 10, 11 and 30; [ADR 0002](adr/0002-delegates-contribute-volume-orchestrator-keeps-decisions.md) |
| Opening | A short plan before the first Delegation, without waiting | Story 5 |
| When delegation pays | Each Delegation's fixed price; it pays only when it replaces your own reading | Gap 1; ADR 0002 |
| When delegation pays | Decide before reading deeply; short or coupled work is yours | Gap 1; story 6 |
| When delegation pays | What is worth delegating | ADR 0002; stories 7–9 |
| When delegation pays | Don't do the Delegate's work while it runs | Gap 2 |
| Splitting the work | Split parallel parts by Write scope; you fix the interfaces | Gap 4; ADR 0002; stories 32 and 47 |
| Splitting the work | Concurrent Write scopes don't overlap; sequence dependent parts; edit a file every part touches yourself | ADR 0002 (a Write scope no concurrent Delegation shares); ADR 0004 |
| Writing the task part | The Delegate starts cold; the fixed part needn't be restated | Story 39; the spec's fixed Contract part |
| Writing the task part | The outline: goal, context, success criteria, Write scope and Checks, constraints, stop rules | The spec's fixed Contract part |
| Writing the task part | Hand over the outcome, not the solution | Gap 3 |
| Writing the task part | Write it once and completely | [Instruction-design research](research/instruction-design-for-frontier-models.md), section 7 |
| Running a Delegation | The `delegate` command, Write scope, Snapshot, network, Checks, concurrency, timeout, running in the background | The spec's wrapper; stories 21, 24, 26, 28, 32, 33 and 47; ADR 0004 |
| Choosing a model | Route with the Model notes and the live catalog | Story 41; [ADR 0003](adr/0003-cost-is-quota-concurrency-capped-astra-needs-permission.md). Gap 7 showed routing sound, so this stays short |
| Choosing a model | The Astra rule, as prose with its reasons | Stories 3 and 4; ADR 0003 |
| Judging a Result | Believe the evidence over the Result; Check reruns, out-of-scope paths, the diff | Stories 27 and 28; ADR 0004; gap 6 |
| Judging a Result | Review the diff, the tests as closely as the code | Story 15; [ADR 0005](adr/0005-second-opinions-are-evidence-not-gates.md); gap 6 |
| Judging a Result | Spot-check a read-only Result rather than answering again | Gap 2 |
| Judging a Result | A `blocked` question goes to the user only through you | Stories 11 and 34 |
| Judging a Result | `apply` with a three-way apply; rerun Checks once the working tree has moved on | Story 29; ADR 0004; gap 6 |
| When a Delegation fails | Failure kinds; stop and ask once on `quota_exhausted`; retry once or do it yourself | Stories 35 and 36; ADR 0003 |
| When a Delegation fails | Ask the user to sign Codex in again on `auth` | The spec's `auth` failure kind: only the user can sign in, so a retry or a cheaper model fails the same way. Carried over from the minimal pointer |
| Resuming or starting fresh | Resume once for a small correction, otherwise a fresh Contract | Story 40 |
| Second opinions | When to ask; Findings are hypotheses; never a gate; the evidence's direction | Stories 12–14; ADR 0005 |
| Composing with another workflow | Write the workflow's obligations into each task part | Story 45 |
| The final report | The `report` table, plus what it can't show | Stories 4, 36 and 44; gap 6 |
| Gotchas | The sandbox refuses loopback sockets without `--network` | Gap 5; issue #30 |
| Gotchas | A read-only home directory and Gradle's cache | Issue #30; item 15 of [the real-Codex check](real-codex-check.md) |
| Gotchas | `/tmp` and `$TMPDIR` are read-only to a writing Delegate | [Skill round](skill-round.md) gap 6; issue #13 |
| Gotchas | Delegated tests test your account, not the user's criteria | Skill round gap 2; issue #13 |
