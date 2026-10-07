---
name: orchestrate
description: Start an orchestrated Run for a task, with OpenAI models available as Delegates through Codex.
argument-hint: "[--allow-astra] <task>"
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py *)
---

!`${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py start-run`

The user's task: $ARGUMENTS

For this Run you can hand work to an OpenAI model through the wrapper:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py delegate --run <Run id> --task <task-part file> --model <model> --effort <effort> --write-scope <paths, or none> [--check <command>]... [--timeout <minutes>]
```

- Write the task part to a file outside the repository, so that it stays out of `git status` and out of what the Delegate reads. The wrapper adds the fixed part of the Contract and stores the full Contract in the Run record.
- Write scope `none` makes a read-only Delegation: the Delegate reads the current working tree in a read-only sandbox, without network access.
- Otherwise the Write scope is one or more repository-relative paths, each covering itself and everything below it; state it in the task part too. The Delegate works in a worktree of its own, made from a Snapshot of the current working tree with uncommitted and untracked files, and can write only there, without network access. Files the repository ignores are left out of the Snapshot and the diff. The main working tree stays as it is. The wrapper's evidence names the diff against the Snapshot and the changed paths outside the Write scope, which the wrapper flags but doesn't remove.
- Give each Check of a writing Delegation as `--check <command>`, and name it in the task part too. After the Delegate ends, the wrapper reruns every Check in the Delegate's worktree and records its exit code and output tail in the evidence's `check_reruns`, apart from the Delegate's own `checks`; trust those reruns over the Result. A Check runs without the files the repository ignores, such as installed dependencies. The reruns share one more timeout of the Delegation's length; an exit code of `null` means a Check ran past it.
- At most three Delegations run at once on the machine, across every Run and repository; a further one waits for a slot rather than failing, and its evidence records `wait_seconds`.
- The wrapper stops the Delegate 20 minutes after Codex starts; the wait for a slot doesn't count. Give `--timeout <minutes>` for longer work, at most 60. A timed-out Delegation comes back `partial`, with its diff and Check reruns.
- When a Delegation goes wrong, the evidence's `failure_kind` says why: `quota_exhausted`, `auth`, `timeout`, `invalid_result` (Codex ended cleanly, but the Delegate's Result was missing or not in the Result shape) or `codex_error` (Codex failed for another reason, with or without a Result). The wrapper then writes the Result itself, never `done`, and keeps the Delegate's own last message in `last-message.txt`. On `quota_exhausted`, stop delegating and ask the user once how to go on, rather than doing the remaining work yourself: that would spend the Claude Quota the Run exists to protect. On `auth`, ask the user to sign Codex in again. Other failures are yours to judge: retry once on a cheaper model, or do the piece yourself and say so in the report.
- To take a writing Delegation's changes, run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py apply --run <Run id> --delegation <Delegation id>`. It applies the whole diff to the working tree with a three-way apply and leaves the index alone. Exit code 3 means conflicts, left as conflict markers in the files it lists; a diff that doesn't apply changes nothing.
- Choose the model and effort from the [Model notes](model-notes.md): they give each model's default effort, uses, things to avoid and relative Quota cost. The list above is Codex's live catalog; a warning above it means the notes may be stale, so lean on the catalog's own descriptions for what they don't cover. Use `gpt-6-astra` only when the user's arguments above include `--allow-astra`. The wrapper refuses `ultra` and any model or effort the live catalog lacks.
- A Delegation can take several minutes, so run the command in the background. Its output names the Result file and summarises the Result; `evidence.json` beside the Result is the wrapper's own record of the Delegation.

When the Run ends, print the Delegations for your final report:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py report --run <Run id>
```

It gives one line per Delegation (model, effort, status, tokens, waiting time and duration), marks Astra Delegations, and totals the tokens per model. Include it in the report so the user sees where each side's Quota went.
