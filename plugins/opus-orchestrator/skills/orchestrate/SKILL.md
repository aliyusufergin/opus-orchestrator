---
name: orchestrate
description: Start an orchestrated Run for a task, with OpenAI models available as Delegates through Codex.
argument-hint: "[--allow-astra] <task>"
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py *)
---

!`${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py start-run`

The user's task: $ARGUMENTS

For this Run you can hand read-only work to an OpenAI model through the wrapper:

```
${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py delegate --run <Run id> --task <task-part file> --model <model> --effort <effort> --write-scope none
```

- Write the task part to a file outside the repository, so that it stays out of `git status` and out of what the Delegate reads. The wrapper adds the fixed part of the Contract and stores the full Contract in the Run record.
- Write scope `none` is the only one available. The Delegate reads the current working tree in a read-only sandbox, without network access.
- Models: `gpt-6.1-sol`, `gpt-6-luna`, and `gpt-6-astra` only when the user's arguments above include `--allow-astra`. Efforts: `low`, `medium`, `high`, `xhigh`.
- A Delegation can take several minutes, so run the command in the background. Its output names the Result file and summarises the Result; `evidence.json` beside the Result is the wrapper's own record of the Delegation.
