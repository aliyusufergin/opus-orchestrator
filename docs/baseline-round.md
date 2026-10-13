# Baseline round

Test cases 1, 3 and 5 (`bug-fix`, `investigation`, `parallel-feature`), each run once in two configurations: `alone` (Opus alone) and `pointer` (Opus with the wrapper and the minimal pointer skill), for issue #11. The runs are the six lines of [results.jsonl](../plugins/opus-orchestrator/test-cases/results.jsonl) recorded on 2026-10-13. The gaps listed below are what the orchestrate skill is written from (issue #12, [ADR 0001](adr/0001-free-method-explicit-interface-invariants-in-code.md)).

## Setup

- **Orchestrator:** `claude-opus-5-5` at the user's usual effort (medium), through the runner's `claude -p` in auto mode; Claude Code 2.1.296
- **Codex CLI:** 0.159.2, signed in with ChatGPT
- **Machine:** 4 CPUs, 11 GB of memory. The four `n8n-custom-ytdlp` runs ran at the same time. The `parallel-feature` runs ran one after the other, so their Gradle builds didn't overlap; `alone` overlapped the last three minutes of the `investigation` `pointer` run.
- **Clones:** kept with `--keep` so that the Run records and Claude's transcripts could be read; they aren't part of the repository.

## Results

Claude's cost is Claude Code's list-price `costUSD` from the run's `modelUsage`. It's only a proxy for Claude Quota, but it weighs cache reads and output the way the windows roughly do. All runs used only `claude-opus-5-5`, with no subagents.

| Task | Config | Passed | Wall time | Claude turns | Claude output tokens | Claude cache reads | Claude cost | Delegations | Codex tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bug-fix | alone | yes | 39 s | 6 | 2,133 | 143K | $0.33 | — | — |
| bug-fix | pointer | yes | 89 s | 4 | 3,922 | 331K | $0.46 | 1: gpt-6.1-sol low, `done`, 39 s | 71,457 in (54,272 cached), 771 out |
| investigation | alone | yes¹ | 37 s | 5 | 2,961 | 134K | $0.35 | — | — |
| investigation | pointer | yes¹ | 292 s | 3 | 4,819 | 329K | $0.51 | 1: gpt-6.1-sol medium, read-only, `done`, 247 s | 286,512 in (226,432 cached), 8,030 out |
| parallel-feature | alone | yes | 669 s | 58 | 47,931 | 5,593K | $3.21 | — | — |
| parallel-feature | pointer | yes | 1,087 s | 9 | 12,108 | 971K | $1.02 | 1: gpt-6.1-sol xhigh, `partial`, 951 s | 3,518,417 in (3,373,696 cached), 28,390 out |

The Codex columns come from each clone's Run record through the wrapper's `report`. The runner first recorded 0 Delegations for the `pointer` lines because it looked for evidence one level too shallow (issue #29). Their `codex` field has since been recounted from the kept Run records.

¹ Known-answer task. The runner had no terminal to ask on and recorded both runs ungraded. The user left the grade to Claude, which marked both passed in results.jsonl. Both final messages give the known answer: 404 detection by a manifest HEAD, a new version skipped with the locked entry kept, a vanished locked tag failing, no lock file failing, and the 3.x path skipping a missing patch without falling back. Neither says the HEAD request is anonymous. Only `alone` names a failed token request explicitly; `pointer` says only that any error other than a 404 fails the run. That is an omission, not an error, so it still passes. Neither run changed a file.

**In short:** every run passed, so delegation didn't change the outcome. On the two small tasks it made things worse: more Claude Quota (+41% and +46%) and two to eight times the wall time. On the large task it cut Claude Quota by about two-thirds (−68%, with 75% fewer output tokens) for 1.6 times the wall time and 3.5M Codex input tokens, nearly all cached.

## Gaps

The issue asks for five kinds: skipped, over-used or misused delegation, weak Contracts, misread evidence and bad routing. Opus never skipped delegation in a `pointer` run: it delegated on all three tasks. Over-use is gap 1. Misuse is gaps 2, 4 and 5. Weak Contracts are gap 3, and gap 5 is also a Contract gap. Evidence and routing, gaps 6 and 7, showed no real fault.

### 1. Delegating after reading, on work Opus finishes in under a minute (over-use)

On `bug-fix`, the Orchestrator first read what Opus alone read: the whole test file and the relevant parts of `scripts/updater.py`. Only then did it delegate, so the reading had already been paid for. On `investigation` it delegated after a `git ls-files` and a grep, then read the code anyway (gap 2). Alone, Opus finished both tasks in about 40 s. With the wrapper, writing a Contract, waiting, and reading back and checking the Result came on top, so Claude Quota went up 41–46%. Delegation pays only when it replaces the Orchestrator's own reading and iterating. A task that Opus can settle after one read of two files is better done by Opus. Neither run weighed this; both delegated because the wrapper was there.

### 2. Doing the Delegate's work while waiting for it (duplicated work)

In `investigation`, Opus started a read-only Delegation and then, while the Delegate ran, read `resolve_n8n` and `main` itself. Its note: "I now have the core logic myself. I'll wait for the Delegate's report". It then checked the Result against what it had read. The Delegate's 247 s and 286K tokens bought only the extras: notes on the workflow, the README and the ADRs, and four low-severity Findings. Checking a Result should mean spot-checking its citations, not answering the question in parallel.

### 3. A Contract that holds the solution (weak Contract: over-specified)

The `bug-fix` task part named the function, the condition to test, the exception to raise, the error text, the test's name, its subtests and the exact helper calls. Opus had worked out the fix before writing it down, and the Delegate typed it out at low effort. The Contract cost Opus about as much as the edit would have. Either the Orchestrator does the work, or it hands over the goal, the context and the Check, and leaves the solution to the Delegate.

### 4. No decomposition of the parallelisable feature (missed parallelism)

`parallel-feature` splits into roughly three parts: core behaviour and tests, the list views with accessibility, and widgets, dialogs and the filter. Opus gave all of it to one Delegation at xhigh, with an 8 KB task part and a 60-minute timeout. Its reason: "long multi-step work across core, views, widgets, dialogs and tests". The single Delegate took 951 s, so the Run took 1.6 times as long as Opus alone and nothing overlapped. The pointer says that three Delegations can run at once but not when splitting pays. Opus never considered splitting by Write scope. This still saved the most Claude Quota of any run, so the Contract itself was strong. It had the goal, ADR constraints, file locations, a test plan per behaviour, offline Checks and a request to list the reference images.

### 5. Checks a Delegate can't run in its sandbox (environment blind spot)

The Contract named three Gradle Checks and granted no network. In Codex's workspace-write sandbox without network, every socket is refused, loopback included, so Gradle couldn't start: "Could not determine a usable wildcard IP". The Delegate spent most of its time and tokens on a workaround: it compiled the core sources and four test classes with the cached Kotlin compiler and ran them under standalone JUnit. Then it returned `partial` with the Android build unverified. Opus had checked beforehand that the build worked offline, but in its own shell, outside the sandbox. The pointer doesn't mention `--network`. The plugin's skill mentions it only for installing dependencies and reading documentation. See issue #30 below.

### 6. Reading evidence: sound, with light review of tests

No misreads. In every `pointer` run, Opus read the diff or Result and the wrapper's evidence before acting:

- In `parallel-feature` it trusted the wrapper's three passing Check reruns over the Delegate's `partial`, and said why in the report. It checked the widget's colour roles in the diff before applying, and questioned the Delegate's list of reference images, which looked too short.
- In `bug-fix` it confirmed that the new test fails without the fix, and restored a comment the Delegate had dropped.
- In `investigation` it spot-checked the workflow and README claims.

The weak spot was review depth on Delegate-written tests. In `parallel-feature` Opus "reviewed all the non-test code but only skimmed the tests", and it didn't rerun the Checks in the main tree after `apply`. Here the Snapshot was unchanged, so the reruns still held. Opus said both plainly in its report. Every `pointer` run ended with the `report` table, as the pointer asks.

### 7. Routing: as the Model notes say

Each Delegation followed the Model notes:

- `bug-fix`: low for a small, fully specified edit with a Check.
- `investigation`: medium for an investigation that needs judgement.
- `parallel-feature`: xhigh for long multi-step work, with the one-line reason the notes ask for.

GPT-6 Luna was never used, and none of the tasks had mechanical bulk work for it. Astra wasn't used and wasn't allowed. Routing showed no gap. The routing mistakes were about *whether* to delegate and how to split the work (gaps 1 and 4), not which model to pick.

## Wrapper and runner failures filed

- Issue #29 (fixed): the test-case runner missed Codex's tokens: it globbed `runs/*/*/evidence.json`, but evidence lives in `runs/<Run id>/delegations/<id>/`, and the fake Claude repeated the same wrong layout.
- Issue #30: without a network grant, a Delegate can't run Gradle or anything else that needs a loopback socket.

Apart from these, the wrapper worked as designed in every run: Snapshots, worktrees, Check reruns, `apply` and `report`. Issue #30 is the sandbox behaving as configured, filed because its consequence for Checks wasn't expected and needs a decision.

## Limits

- One run per configuration, at medium effort. Wall times include contention: the four n8n runs ran together on four CPUs, and `parallel-feature` `alone` started while `investigation` `pointer` was still running.
- The `investigation` grades are Claude's, at the user's request.
- The `skill` configuration isn't part of this round. It is measured in the [skill round](skill-round.md), issue #13.
