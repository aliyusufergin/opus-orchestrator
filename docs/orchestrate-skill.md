# Where the orchestrate skill's guidance comes from

The [orchestrate skill](../plugins/opus-orchestrator/skills/orchestrate/SKILL.md) holds only guidance that closes a gap the [baseline round](baseline-round.md) or the [skill round](skill-round.md) showed, or that the spec (issue #1) requires as a prose rule ([ADR 0001](adr/0001-free-method-explicit-interface-invariants-in-code.md)). This table traces each piece to its source, for issues #12, #13 and #36. When either side ships a new model, the test cases are rerun and a piece whose gap no longer shows is pruned.

"Gap" means a numbered gap in the baseline round unless the skill round is named; "story" means a user story in the spec. The wrapper mechanics carried over from the minimal pointer are the interface to the wrapper, specified in the spec's Implementation Decisions.

| Skill section | Guidance | Source |
| --- | --- | --- |
| Opening | The Orchestrator keeps the user, decisions, task parts, integration, acceptance and commits | Stories 10, 11 and 30; [ADR 0002](adr/0002-delegates-contribute-volume-orchestrator-keeps-decisions.md) |
| Opening | A short plan before the first Delegation, without waiting | Story 5 |
| When delegation pays | Each Delegation's fixed price; it pays only when it replaces your own reading | Gap 1; ADR 0002 |
| When delegation pays | Decide whether to delegate before reading deeply; that rule times the decision and doesn't limit the reading for work you keep | Gap 1; story 6; skill round gap 1 |
| When delegation pays | Work settled by reading one or two files, a fix or a question, is yours; so is coupled work | Gap 1; skill round gap 3 |
| When delegation pays | What is worth delegating, investigation only across more code than that | ADR 0002; stories 7–9; skill round gap 3 |
| When delegation pays | Don't do the Delegate's work while it runs | Gap 2 |
| Splitting the work | Split parallel parts by Write scope | Gap 4; ADR 0002; stories 32 and 47 |
| Splitting the work | Balance the parts; your own work before and after the Delegations is on the critical path | Skill round gap 4 |
| Splitting the work | You fix the interfaces; an interface is a signature and its contract, and before the Delegations you write only what other parts compile against | ADR 0002; skill round gap 1; the [revision round](revision-round.md)'s first attempt |
| Splitting the work | A behaviour change and its tests go together, to one Delegation or to you | Skill round gaps 1 and 2; the [revision round](revision-round.md)'s first attempt |
| Splitting the work | Concurrent Write scopes don't overlap; sequence dependent parts; edit a file every part touches yourself | ADR 0002 (a Write scope no concurrent Delegation shares); ADR 0004 |
| Writing the task part | The Delegate starts cold; the fixed part needn't be restated | Story 39; the spec's fixed Contract part |
| Writing the task part | The outline: goal, context, success criteria, Write scope and Checks, constraints, stop rules | The spec's fixed Contract part |
| Writing the task part | Give the user's criteria as they stand, not your account; tests against those | Skill round gap 2. A Gotcha after issue #13, moved here because it is about writing a task part, not about the environment |
| Writing the task part | Hand over the outcome, not the solution | Gap 3 |
| Writing the task part | Write it once and completely | [Instruction-design research](research/instruction-design-for-frontier-models.md), section 7 |
| Running a Delegation | The `delegate` command, Write scope, Snapshot, network, Checks, concurrency, timeout, running in the background | The spec's wrapper; stories 21, 24, 26, 28, 32, 33 and 47; ADR 0004 |
| Choosing a model | Route with the Model notes and the live catalog | Story 41; [ADR 0003](adr/0003-cost-is-quota-concurrency-capped-astra-needs-permission.md). Gap 7 showed routing sound, so this stays short |
| Choosing a model | The Astra rule, as prose with its reasons | Stories 3 and 4; ADR 0003 |
| Judging a Result | Believe the evidence over the Result; Check reruns, out-of-scope paths, the diff | Stories 27 and 28; ADR 0004; gap 6 |
| Judging a Result | Review the diff, the tests as closely as the code, and tests that cover only your account | Story 15; [ADR 0005](adr/0005-second-opinions-are-evidence-not-gates.md); gap 6; skill round gap 2 |
| Judging a Result | Spot-check a read-only Result rather than answering again | Gap 2 |
| Judging a Result | A `blocked` question goes to the user only through you | Stories 11 and 34 |
| Judging a Result | `apply` with a three-way apply; rerun Checks once the working tree has moved on | Story 29; ADR 0004; gap 6 |
| When a Delegation fails | Failure kinds; stop and ask once on `quota_exhausted`; retry once or do it yourself | Stories 35 and 36; ADR 0003 |
| When a Delegation fails | Resume a `stopped` Delegation rather than start again | The wrapper's `stopped` failure kind, added for the [revision round](revision-round.md)'s stopped Delegations; issue #36 |
| When a Delegation fails | Ask the user to sign Codex in again on `auth` | The spec's `auth` failure kind: only the user can sign in, so a retry or a cheaper model fails the same way. Carried over from the minimal pointer |
| Resuming or starting fresh | Resume once for a small correction, otherwise a fresh Contract | Story 40 |
| Second opinions | When to ask; Findings are hypotheses; never a gate; the evidence's direction | Stories 12–14; ADR 0005 |
| Composing with another workflow | Write the workflow's obligations into each task part | Story 45 |
| The final report | The `report` table, plus what it can't show | Stories 4, 36 and 44; gap 6 |
| The final report | No `report` without a Delegation, just a line saying so | Skill round gap 5 |
| Gotchas | The sandbox refuses loopback sockets without `--network` | Gap 5; issue #30 |
| Gotchas | A read-only home directory and Gradle's cache | Issue #30; item 15 of [the real-Codex check](real-codex-check.md) |
| Gotchas | `/tmp` and `$TMPDIR` are read-only to a writing Delegate | [Skill round](skill-round.md) gap 6; issue #13 |
| Gotchas | A background `delegate` call needs a Bash timeout longer than the Delegation | [Revision round](revision-round.md); issue #36 |

## Revised from the skill round (issue #36)

Each gap of the [skill round](skill-round.md) has revised guidance. The [revision round](revision-round.md) measured gap 3 closed. Gaps 1 and 2 were closed only while the skill named the failing case; worded generically, Opus followed the new rules and the case was still missed by a medium-effort Delegation. Gap 4 was not closed, and gap 5 is within run-to-run noise. The guidance for gaps 4 and 5 stays, because it is still true and costs a few lines.

1. **Production code written after a short read, as "the interface".** "When delegation pays" now says the reading rule times the delegation decision and doesn't limit the reading for work Opus keeps. "Splitting the work" defines an interface as a signature and its contract, and limits what Opus writes before the Delegations to what other parts compile against. The first wording, which allowed the behaviour to be "worked out properly" by Opus, didn't change what Opus did: the [revision round](revision-round.md)'s first `parallel-feature` run repeated the failure line for line. So "Splitting the work" now also keeps a behaviour change and its tests together, the way the passing `pointer` run had them.
2. **Delegated tests that test the Orchestrator's account.** Moved from Gotchas to "Writing the task part" and widened: every task part gives the user's criteria as they stand, and a test Delegation's tests are asked for against them. Gotchas keep only what the environment does.
3. **A small investigation still delegated.** The size cue the bug fix followed, one or two files of a few hundred lines, now covers a question as well as a fix, and investigation is worth delegating only across more code than that.
4. **A split that didn't shorten the Run.** "Splitting the work" says to balance the parts, and that the Orchestrator's own work before and after the Delegations adds to the longest one.
5. **The skill's own cost without a Delegation.** No `report` call when there were no Delegations, which was one of the three turns `bug-fix` took beyond `alone`. The skill is also cut back: the body the revision round measured had 2,495 words against 2,547 before, although it gained the guidance above. The Gotcha that round added, the `stopped` failure kind and wording fixes bring it to 2,586. The skill wasn't split into a short core and a file read on the first Delegation: a Run that delegates would pay an extra turn for it, and the task-part guidance and Gotchas have to be in view when the first task part is written.

Pruned, for gap 5, because the wrapper enforces or prints it ([ADR 0001](adr/0001-free-method-explicit-interface-invariants-in-code.md)'s third layer): the list of what the fixed Contract part says, the refusal of `ultra`, Codex's web search being off, `wait_seconds`, the definitions of the failure kinds, the `resumes` field, the report's columns and its Astra and network marks.

Also cut for gap 5, as restatements: "The user can interrupt if they disagree" (the plan is shown without waiting either way), "architecture" beside "interfaces" in the Orchestrator's list, and the baseline figures behind "Splitting the work", "While a Delegate runs" and the review of tests, whose rules stay. "A Delegation takes minutes" was cut from the line on running in the background too, and the revision round suspects that cut of losing the cue for a long Bash timeout; the Gotcha it added says so explicitly instead.

No guidance was pruned as no longer needed: neither round showed a gap closing on its own, without its guidance.
