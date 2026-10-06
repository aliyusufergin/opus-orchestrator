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
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py delegate --run <Run id> --task <task-part file> --model <model> --effort <effort> --write-scope <paths, or none>
```

- Write the task part to a file outside the repository, so that it stays out of `git status` and out of what the Delegate reads. The wrapper adds the fixed part of the Contract and stores the full Contract in the Run record.
- Write scope `none` makes a read-only Delegation: the Delegate reads the current working tree in a read-only sandbox, without network access.
- Otherwise the Write scope is one or more repository-relative paths, each covering itself and everything below it; state it in the task part too. The Delegate works in a worktree of its own, made from a Snapshot of the current working tree with uncommitted and untracked files, and can write only there, without network access. Files the repository ignores are left out of the Snapshot and the diff. The main working tree stays as it is. The wrapper's evidence names the diff against the Snapshot and the changed paths outside the Write scope, which the wrapper flags but doesn't remove.
- To take a writing Delegation's changes, run `${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py apply --run <Run id> --delegation <Delegation id>`. It applies the whole diff to the working tree with a three-way apply and leaves the index alone. Exit code 3 means conflicts, left as conflict markers in the files it lists; a diff that doesn't apply changes nothing.
- Models: `gpt-6.1-sol`, `gpt-6-luna`, and `gpt-6-astra` only when the user's arguments above include `--allow-astra`. Efforts: `low`, `medium`, `high`, `xhigh`.
- A Delegation can take several minutes, so run the command in the background. Its output names the Result file and summarises the Result; `evidence.json` beside the Result is the wrapper's own record of the Delegation.
