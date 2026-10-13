# Skill round

Test cases 1, 3 and 5 (`bug-fix`, `investigation`, `parallel-feature`), each run once in the `skill` configuration: Opus with the wrapper and the plugin's own [orchestrate skill](../plugins/opus-orchestrator/skills/orchestrate/SKILL.md), for issue #13. The runs are the three `skill` lines of [results.jsonl](../plugins/opus-orchestrator/test-cases/results.jsonl), recorded on 2026-10-13, and they are compared with the [baseline round](baseline-round.md)'s `alone` and `pointer` runs.

**Verdict: the round fails.** The skill passed two of the three tasks, and both baselines passed all three. It used 34% less Claude Quota than Opus alone, so it met the Quota condition but not the pass-rate condition. The gaps below are what the skill is revised from.

## Setup

As in the baseline round, with these differences:

- **Effort:** `medium`, set with the runner's new `--effort` option. The baseline ran at the user's setting, which was `medium` then (its transcripts record it) and has since moved to `high`. The runner now records the effort in each results line.
- **Concurrency:** the two `n8n-custom-ytdlp` runs ran at the same time, then `parallel-feature` ran on its own. Nothing else ran on the machine.
- **Skill:** the plugin's skill as merged for issue #12 (commit `40a48cf`), with its two Gotchas from issue #30.

## Results

Claude's cost is Claude Code's list-price `costUSD`, as in the baseline round: a proxy for Claude Quota. All runs used only `claude-opus-5-5`, with no Subagents.

| Task | Config | Passed | Wall time | Claude turns | Claude output tokens | Claude cache reads | Claude cost | Delegations | Codex tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bug-fix | alone | yes | 39 s | 6 | 2,133 | 143K | $0.33 | — | — |
| bug-fix | pointer | yes | 89 s | 4 | 3,922 | 331K | $0.46 | 1 | 71,457 in (54,272 cached), 771 out |
| bug-fix | skill | yes | 53 s | 9 | 3,080 | 255K | $0.42 | none | — |
| investigation | alone | yes¹ | 37 s | 5 | 2,961 | 134K | $0.35 | — | — |
| investigation | pointer | yes¹ | 292 s | 3 | 4,819 | 329K | $0.51 | 1 | 286,512 in (226,432 cached), 8,030 out |
| investigation | skill | yes¹ | 270 s | 5 | 4,134 | 267K | $0.43 | 1: gpt-6.1-sol medium, read-only, `done`, 219 s | 292,050 in (230,400 cached), 6,549 out |
| parallel-feature | alone | yes | 669 s | 58 | 47,931 | 5,593K | $3.21 | — | — |
| parallel-feature | pointer | yes | 1,087 s | 9 | 12,108 | 971K | $1.02 | 1 | 3,518,417 in (3,373,696 cached), 28,390 out |
| parallel-feature | skill | **no** | 1,094 s | 13 | 21,498 | 2,261K | $1.69 | 2 at once: gpt-6.1-sol medium, core tests, `partial`, 385 s; gpt-6.1-sol xhigh, Android, `done`, 707 s; both `NETWORK` | 3,408,829 in (3,180,416 cached), 28,471 out |

| Config | Passed | Claude cost | Wall time | Codex input tokens |
| --- | --- | --- | --- | --- |
| alone | 3 of 3 | $3.88 | 745 s | — |
| pointer | 3 of 3 | $1.99 | 1,468 s | 3.88M |
| skill | 2 of 3 | $2.55 (−34% against alone, +28% against pointer) | 1,417 s | 3.70M |

Per task, the skill's Claude cost against `alone` and `pointer`: `bug-fix` +29% and −9%, `investigation` +25% and −14%, `parallel-feature` −47% and +65%.

¹ Known-answer task, recorded ungraded because the runner had no terminal to ask on. As in the baseline round, Claude graded it and marked it passed in results.jsonl. The final message makes every point of the known answer: a 404 on the manifest HEAD means a missing tag; a new version is skipped with the locked entry kept and the note on stderr, and a later run retries; a vanished locked tag fails; no lock file fails; the 3.x path skips an unpushed patch without falling back to an earlier one; a token failure fails the run. Like both baseline answers, it doesn't say the HEAD request is anonymous. The run changed no files.

### The failed check

One of 278 core tests failed, `WidgetBehaviorTest.testOnToggleRepetition_onRestDay`, from the reference's acceptance tests: `expected:<Entry(2015-1-25, value=2)> but was:<Entry(2015-1-25, value=-1)>`. On a Rest day, a stored No shows as a Rest day, so the next tap on a checkmark widget must record Yes. The skill run's `WidgetBehavior.onToggleRepetition` still worked out the next value from the stored entry (`originalEntries`) rather than the shown one (`computedEntries`), so it recorded Unanswered. Both baselines read the shown value: `alone` did it itself, and the `pointer` Contract said "Rest day (YES_AUTO) → Yes as today".

Opus wrote that code itself, not a Delegate. See gap 1.

## How the skill changed behaviour

Against the baseline round's gaps:

- **Gap 1, over-use: closed for the bug fix, open for the investigation.** On `bug-fix`, Opus decided after one `wc` and a grep: "Small, tightly coupled fix (one function plus tests). I'll do this myself without delegating". On `investigation`, it delegated after a `git ls-files` and a `wc`, though the question rests on one 370-line file that Opus alone answered in 37 s. See gap 3.
- **Gap 2, duplicated work: closed.** On `investigation`, Opus wrote "I'll wait for it to finish, then spot-check what it reports", then made one read of the cited lines.
- **Gap 3, a Contract that holds the solution: closed.** No task part named the solution. The `investigation` task part stated the question, the files, what each case must cover and the stop rule. The `parallel-feature` task parts stated the goal, the interfaces and the criteria.
- **Gap 4, no decomposition: closed, without the wall-time gain.** Opus split `parallel-feature` into core tests (Write scope `uhabits-core/src/commonTest`) and the Android app (`uhabits-android`), and ran both at once. It wrote the core production change itself first, as the interface between them. See gap 4.
- **Gap 5, Checks that can't run in the sandbox: closed.** Both Delegations had `--network`, "only so Gradle could use local sockets", and the task parts told the Delegates how to run Gradle with a read-only home directory. Neither Delegate hit the loopback problem.
- **Gap 6, reading evidence: sound.** Opus trusted the wrapper's passing rerun over d1's `partial` and said why, reviewed both diffs, reran every Check in the merged working tree, fixed the core tests' ktlint errors, and found reference images the Android Delegate had missed.
- **Gap 7, routing: as before.** Medium for the investigation and the core tests, xhigh for the long Android part.

## Gaps

### 1. Production code written after a short read, as "the interface" (the failure)

On `parallel-feature`, Opus read for about 30 seconds (six commands) and then wrote the core change itself: the setting's removal, the new `onToggle`, the filter, and the full cycle for widgets and the Calendar card. It announced this as "the core interface edits". For widgets it only replaced `preferences.areQuestionMarksEnabled` with `true`, and never asked which value a widget tap should move on from. The `pointer` Opus read about as briefly, but it wrote down the rule ("Rest day (YES_AUTO) → Yes as today") and left the code to a Delegate at xhigh, which got it right. `alone` spent 58 turns on the task and got it right too.

Two pieces of the skill pull the same way here. "Decide before you read deeply" is about whether to delegate, but it was followed as a reason to read little before writing code Opus kept. "Fix the interfaces between them yourself" was read as licence to write behaviour, not just signatures. The revision should say that the reading rule is about the delegation decision only, and that work the Orchestrator keeps needs the reading it needs. It should also say that an interface is a signature and its contract, and that behaviour behind it is either worked out properly or handed to a Delegate with the user's criteria.

### 2. Delegated tests that test the Orchestrator's account (why the failure got through)

The core-tests task part told the Delegate that the production code was already changed, and described that change in Opus's words. Its success criteria asked for full cycles "starting from Unanswered", and mentioned a Rest day only for the filter. The Delegate wrote exactly those tests, they passed, and so did Opus's own reruns after merging, but no test covered a widget tap on a Rest day. The user's prompt had the criteria that would have caught it: each tap moves to the next state, the same in the list, on the Calendar card and on widgets, and Rest days keep their look. Added as a Gotcha.

### 3. A small investigation still delegated (over-use, read-only)

"Read-heavy investigation" is on the skill's list of work worth delegating. Opus treated a question about one 370-line file as read-heavy and widened the task part to the workflow, `notify.py`, the ADRs and the tests. The Delegate took 219 s and 292K Codex tokens. The run cost 25% more Claude Quota than Opus alone and seven times the wall time, though 14% less than `pointer`. The revision should give a size cue: an investigation Opus can answer by reading one or two files is Opus's, like the bug fix.

### 4. Splitting that didn't shorten the Run

The split cut the longest Delegation from 951 s (`pointer`) to 707 s, but the Run took 1,094 s against `pointer`'s 1,087 s. Opus spent about three minutes before the Delegations, writing the core change and compiling it, and about three and a half after them, reviewing an 850-line diff and running every Check in the merged tree. The Android part, at xhigh, still held most of the work. It also cost 65% more Claude Quota than `pointer` on this task: the production code Opus wrote, two diffs to review, and the ktlint fixes. The revision should say to balance the parts, so that no one Delegation is the whole Run, and to count the Orchestrator's own share of the work as time on the critical path.

### 5. The skill's own cost, even without a Delegation

`bug-fix` with the skill made no Delegation and still cost 29% more Claude Quota than `alone`. The skill and `start-run`'s output add about 7K tokens that are written once and reread every turn (255K cache reads against 143K), and the run took 9 turns against 6, one of them the `report` the skill asks for with no Delegations to show. Part of this is the price of having the plugin on at all. A shorter skill, or no `report` when there were no Delegations, would cut it.

### 6. `/tmp` is read-only to a writing Delegate (a new sandbox failure)

The wrapper keeps `/tmp` and `$TMPDIR` out of the writable roots (`exclude_slash_tmp`, `exclude_tmpdir_env_var`). The project's tests write under a hard-coded `/tmp/test-temp-N`, so 25 of 276 core tests failed in the sandbox with "Read-only file system". The Delegate tried `java.io.tmpdir`, which the project doesn't use, ran only its own tests instead, and returned `partial`. The wrapper's rerun, outside the sandbox, passed. Opus read that correctly, so the run lost only the Delegate's time. Added as a Gotcha.

## Gotchas added

Each names the failure it comes from:

- `/tmp` and `$TMPDIR` are read-only to a writing Delegate: gap 6, Delegation d1 of `parallel-feature`.
- Tests a Delegate writes for code you changed test your account, not the user's criteria: gap 2, the failed `parallel-feature` check.

Gaps 1, 3, 4 and 5 call for revised guidance, not Gotchas, and are left for the skill's revision.

## Limits

- One run per configuration and task. The `parallel-feature` failure is one test in one run, and `alone` and `pointer` could miss the same case on another run.
- The `investigation` grade is Claude's, as in the baseline round.
- The baseline ran at the user's `medium` setting and this round at `--effort medium`. The transcripts of both record `medium`.
- Wall times include contention: the two n8n runs ran together on four CPUs, and the baseline's four n8n runs ran together.
