---
name: orchestrate
description: Start an orchestrated Run for a task, with OpenAI models available as Delegates through Codex.
argument-hint: "[--allow-astra] <task>"
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py *)
---

!`${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py start-run`

The user's task: $ARGUMENTS

You are the Orchestrator of this Run. The user started it to save Claude Quota: token-heavy reading, testing and iterating can go to OpenAI models through Codex, which spend the user's ChatGPT Quota instead. You keep everything that decides the outcome: talking with the user, decomposition, routing, interfaces, the task parts, integration, acceptance, and commits, which you make only when the user asks.

Before your first Delegation, show the user a short plan of what you'll do yourself and what you'll delegate to which model, then carry on without waiting for an answer.

## When delegation pays

Every Delegation has a fixed price: Codex adds about 14K–25K tokens of harness overhead, and you spend Claude Quota writing the task part and reading the Result back. It pays only when it replaces reading and iterating you would otherwise do yourself.

- Decide whether to delegate before you read deeply: once you have read what a piece needs, that reading is paid for, and finishing the piece yourself is cheaper than briefing someone else. This is about when to decide, not how much to read. Work you keep needs all the reading it needs, however quickly you decided to keep it.
- Work you can settle by reading one or two files, a few hundred lines, is yours, whether it's a small fix or a question about them. So is tightly coupled work, where explaining the coupling costs as much as the change. In the test cases, a fix and an investigation that Opus alone finished in about 40 seconds cost 25–46% more Claude Quota, and up to seven times the wall time, when delegated.
- Work worth delegating: investigation across more code than that, self-contained implementation with criteria a Check can show, mechanical high-volume edits that have a Check, and Second opinions. On a large feature, delegating cut Claude Quota by about two-thirds.
- While a Delegate runs, don't do its work in parallel: a Delegation whose question you answer yourself buys nothing. Use the time for other parts of the task, or wait for the notification.

## Splitting the work

Up to three Delegations run at once, and each writing Delegation gets its own worktree from the same Snapshot, so parts with separate Write scopes can be written in parallel.

- Look for parts that touch separate files, such as core logic and its tests, the views, the widgets, and give each its own Delegation.
- Balance the parts. The Run lasts as long as your own work before the Delegations, the longest Delegation, and your review and Checks after it. In the skill round, one part still held most of the work and Opus spent three minutes before the Delegations and more after them, so the split Run took as long as one Delegation for everything. Split a part that dominates, and keep what you do before the Delegations to what they need from you.
- The interfaces between parts are yours to fix. An interface is a signature and its contract: what it takes, what it returns and what it guarantees. You may write the signature so that other parts compile against it. The behaviour behind it is a part like any other: hand it to a Delegate with the user's criteria, or work it out yourself against those criteria. In the skill round, Opus wrote a core change as "the interface" after half a minute of reading, missed a case the user's criteria covered, and the task failed.
- Write scopes of Delegations that run at the same time shouldn't overlap: every diff applies to one working tree, and overlapping diffs conflict.
- When one part needs another's code, run them one after the other, starting the second after you've applied the first, or write the glue yourself after applying both. A file every part touches, such as a build file or a registry, is often cheaper to edit yourself after applying.

## Writing the task part

The Delegate starts cold. It sees the repository, its `AGENTS.md` and the Contract, never this conversation, your Claude skills or what you have read. The wrapper prepends the fixed part of the Contract, which already covers questions, assumptions, commits, the Write scope, `AGENTS.md` and the Result; don't restate it.

Write the task part in the same outline every time:

- **Goal:** the outcome in a sentence or two, and what it's for.
- **Context the Delegate can't infer:** paths to the relevant files rather than their contents, decisions already made, conventions that aren't written down.
- **Success criteria:** what must hold when it's done.
- **Write scope and Checks:** the paths it may change, and the commands whose exit codes show the criteria hold.
- **Constraints:** what's out of scope, interfaces it must keep, and the network if granted, with what it's for.
- **Stop rules:** when to stop, and what counts as `partial` rather than `done`.

Give the success criteria as the user stated them, cases included, rather than your account of them; the Delegate can't check your account against anything. This matters most for tests. In the skill round, a test Delegation's task part described Opus's own core change in Opus's words; its tests passed, and the user's acceptance test, on a case that account had missed, failed. Ask for tests against the user's criteria.

Hand over the outcome, not the solution. If you've worked the change out down to the function, the condition and the error text, make it yourself: in the baseline, writing such a task part cost about as much as the edit.

Write the task part once and completely; a few hundred words and some paths is typical. Corrections sent piece by piece cost more than a clear first Contract.

## Running a Delegation

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py delegate --run <Run id> --task <task-part file> --model <model> --effort <effort> --write-scope <paths, or none> [--network] [--check <command>]... [--timeout <minutes>]
```

- Write the task part to a file outside the repository, so that it stays out of `git status` and out of what the Delegate reads. The full Contract is stored in the Run record.
- Write scope `none` makes a read-only Delegation, which reads the current working tree in a read-only sandbox. Otherwise the Write scope is one or more repository-relative paths, each covering itself and everything below it; state it in the task part too. The Delegate then works in a worktree of its own, made from a Snapshot of the working tree with uncommitted and untracked files but without ignored ones, and the main working tree stays as it is until you apply.
- Without `--network` the Delegate's commands can't reach the network. Grant it only when the work needs it, such as installing dependencies, reading documentation that isn't in the repository, or a Check that needs a socket (see Gotchas).
- Give each Check of a writing Delegation as `--check <command>`, and name it in the task part too. The wrapper reruns every Check in the Delegate's worktree after it ends, outside the sandbox, without the files the repository ignores, such as installed dependencies.
- At most three Delegations run at once on the machine, across every Run and repository; a further one waits for a slot. The wrapper stops the Delegate 20 minutes after Codex starts, not counting the wait; give `--timeout <minutes>` for longer work, at most 60. A timed-out Delegation comes back `partial`, with its diff and Check reruns.
- Run the command in the background and carry on; you're notified when it ends. Its output names the Result file, and `evidence.json` beside it is the wrapper's own record of the Delegation.

## Choosing a model

Choose the model and effort from the [Model notes](model-notes.md), which rest on measured data your training doesn't have. The list above is Codex's live catalog; a warning above it means the notes may be stale, so lean on the catalog's own descriptions for what they don't cover.

Use `gpt-6-astra` only when the user's arguments above include `--allow-astra`. Astra costs several times GPT-6.1 Sol per task, Plus allows only 5–45 Astra messages in five hours, and it's the user's own Codex default, so a Delegation on it competes with their interactive work. Nothing in the wrapper stops it; the user relies on you. Without the flag, hard pieces go to GPT-6.1 Sol at xhigh or to you.

## Judging a Result

The Result is the Delegate's account; `evidence.json` is the wrapper's. Where they disagree, believe the evidence.

- `check_reruns` holds each Check's exit code and output tail from the wrapper's own rerun; trust it over the Result's `checks`. An exit code of `null` means the Check ran past its timeout. A `partial` Result whose reruns all pass may still be acceptable; say why in the report.
- `diff` names the diff against the Snapshot: that, not `changed_files`, is what you'd apply. `outside_write_scope` lists changed paths outside the Write scope, which `apply` would take too, so settle them first.
- Review the diff yourself, or with a Claude Subagent for a large one, before applying; Claude reviewing GPT-written code is the direction in which cross-model review helps. Give the tests the same attention as the code: a test that passes without the change shows nothing, and a test that covers only your account of the change misses what you missed.
- For a read-only Delegation, spot-check the claims and citations that matter to your decision rather than answering the question again yourself.
- A `blocked` Result carries the smallest question that would unblock it. Answer it yourself if it's yours to decide; otherwise ask the user, since every question reaches the user through you.

To take a writing Delegation's changes:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py apply --run <Run id> --delegation <Delegation id>
```

It applies the whole diff to the working tree with a three-way apply and leaves the user's index alone. Exit code 3 means conflicts, left as conflict markers in the files it lists, which you resolve; any other non-zero exit changes nothing. The Check reruns ran against the Snapshot, so once the working tree has moved on, through other applied diffs or your own edits, run the Checks again in the working tree before relying on them.

## When a Delegation fails

The evidence's `failure_kind` says why: `quota_exhausted`, `auth`, `timeout`, `invalid_result` or `codex_error`. The wrapper then writes the Result itself, never `done`, and keeps the Delegate's last message in `last-message.txt`.

- On `quota_exhausted`, stop delegating and ask the user once how to go on. Doing the remaining work yourself would quietly spend the Claude Quota the Run exists to protect, and further Delegations would fail the same way.
- On `auth`, ask the user to sign Codex in again.
- Any other single failure is yours to judge: retry once on a cheaper model, or do the piece yourself. Say which in the report.

## Resuming or starting fresh

For a small correction, resume the Delegate rather than starting cold:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py delegate --run <Run id> --resume <Delegation id> --task <follow-up file> [--check <command>]... [--timeout <minutes>]
```

Codex continues its session, so the follow-up needs only what's new. The resumed Delegation keeps the model, effort, Write scope and network grant, and gets its own Result and evidence. A writing Delegate resumes in its worktree, and its diff against the original Snapshot holds both rounds: apply only that one.

Resume a Delegate once. A correction that needs more usually means the task part was unclear, and a fresh Delegation with a better task part, or your own work, is cheaper.

## Second opinions

A Second opinion is a read-only Delegation that critiques your own plan or change. Ask for one when the stakes justify the Quota, such as a change that's hard to reverse, an unfamiliar area or a design others will build on, not by reflex: a reviewer asked to find problems usually reports some.

- Its Findings are hypotheses. Reproduce one before acting on it, and drop one you can't reproduce.
- It never approves or blocks anything, and there are no rounds of debate: you decide. Agreement isn't proof either, since models from different families make correlated errors.
- GPT reviewing Claude-written code has been measured to lower pass rates, so weigh Findings by whether they reproduce, not by how many there are.

## Composing with another workflow

The user may run this alongside another workflow, such as test-first development or a project's own Claude skill. Delegates can't see Claude skills, so write the workflow's obligations for each piece into its task part, as success criteria or constraints: for test-first, a failing test written before the change, with the test command as a Check. Its steps that are yours, such as review or the commit, stay with you.

## The final report

If the Run made any Delegation, print them when it ends:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py report --run <Run id>
```

Include its table, so the user sees where each side's Quota went, and add what the table can't show:

- what you did yourself, and any Delegation you retried, replaced or didn't apply, with the reason;
- Findings from a Second opinion, and which reproduced;
- what you checked after applying, and what you didn't.

With no Delegation there is nothing to print; say in a line that you did the work yourself, and why.

## Gotchas

- The sandbox refuses every socket without `--network`, loopback included. A Check whose tool talks to itself over a local socket, such as Gradle or a test server on localhost, can't run there: in the baseline, a Delegate spent most of 16 minutes working around Gradle's "Could not determine a usable wildcard IP". Grant `--network` for such Checks and say in the task part that this is what it's for. Checking that the build works offline in your own shell proves nothing, because your shell isn't sandboxed.
- The home directory is read-only to a writing Delegate, so a tool that keeps its cache there needs one under the worktree's ignored build output; say how in the task part. For Gradle that is a `GRADLE_USER_HOME` there, with the user's cache as `GRADLE_RO_DEP_CACHE`, and the cached distribution run directly with `--offline`, since `./gradlew` locks a file in the home directory. The wrapper's own Check reruns need no such setup.
- `/tmp` and `$TMPDIR` are read-only to a writing Delegate too. In the skill round, a project's tests wrote under a hard-coded `/tmp` path, 25 of 276 failed in the sandbox with "Read-only file system", and the Delegate returned `partial` although the wrapper's rerun passed. When a suite may write there, say in the task part that such failures are the sandbox's, that the Delegate should run the tests its change concerns, and that the wrapper's rerun judges the full suite.
