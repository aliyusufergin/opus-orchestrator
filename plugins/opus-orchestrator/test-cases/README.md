# Test cases

The test cases measure whether the skill earns its place against baselines ([ADR 0001](../../../docs/adr/0001-free-method-explicit-interface-invariants-in-code.md)). Each runs once per configuration, at your usual effort, and spends Claude Quota and, with the plugin, ChatGPT Quota. They don't run in CI.

The five tasks are in [tasks.toml](tasks.toml). Each one names the repository it is cloned from, the commit to start from, the prompt and either a check or a known answer. The first round is `bug-fix`, `investigation` and `parallel-feature`.

## Configurations

- `alone`: Opus alone, with the prompt as given and the plugin off.
- `pointer`: Opus with the wrapper and the minimal pointer skill in [pointer-skill](pointer-skill/SKILL.md). The pointer stays here as a baseline once the plugin's own skill grows. Until then the two are the same, so measure only one of `pointer` and `skill`.
- `skill`: Opus with the plugin's own skill.

With the plugin, the prompt starts the skill, `/opus-orchestrator:orchestrate <prompt>`. The Run gets a copy of the plugin from this checkout, without this folder, so the task definitions and their answers stay out of its sight. An installed copy of the plugin is switched off for the run.

## Running

```sh
plugins/opus-orchestrator/test-cases/run.py list
plugins/opus-orchestrator/test-cases/run.py dry-run [--task <id>]...
plugins/opus-orchestrator/test-cases/run.py run --task <id> --config alone|pointer|skill [--keep]
```

`run` clones the task's repository into the system's temporary directory and runs `claude -p` there, headless, with `--model opus`, in auto permission mode. The clone holds the start commit and its history only, so the original solution isn't in it, and it has no remote, so nothing can be pushed back. Your repository is only read. When Claude ends, the runner judges the outcome:

- A check runs in the clone, after the reference's acceptance tests have been put in place; exit code 0 is a pass.
- A known answer is yours to judge: the runner shows the final message beside the known answer and asks. Without a terminal it records the run ungraded, with `passed` null and the final message kept.

It appends one line to [results.jsonl](results.jsonl) with the task, configuration, pass or fail, the check's exit code and output tail, wall time, the paths the Run left changed in the clone (`git status --porcelain`, so a read-only task can be checked for writes), Claude's tokens summed over every model the Orchestrator used (`modelUsage`, subagents included), and Codex's tokens summed over every Delegation in the clone's Run records. The clone is removed afterwards; `--keep` leaves it, with its Run records in `.git/opus-orchestrator/runs/`, for inspection.

`dry-run` sets up each task's clone and runs its check without starting Claude or Codex. The check must fail at the start and, where the task names a reference, pass at the reference. A known-answer task only has its clone set up, and its answer printed.

## Limits

- A Run in the clone could still read your original repositories elsewhere on disk; the prompts never point there.
- The `loop-habit-tracker-next` checks need the Android SDK through `ANDROID_HOME`, and Gradle; a check builds from scratch in the clone, which takes minutes.
- The Android view tests need an emulator, so the `parallel-feature` check covers the core tests and compiles the Android code only.
