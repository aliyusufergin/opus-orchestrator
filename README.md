# Opus Orchestrator

A Claude Code plugin in which a Claude Opus session, started by you for a task, hands bounded pieces of the work to OpenAI models through Codex and stays responsible for the outcome. The vocabulary is in [CONTEXT.md](CONTEXT.md) and the decisions are in [docs/adr](docs/adr).

This is an early version. Its skill is a minimal pointer to the wrapper. The full skill will be written from measured gaps.

## Requirements

- Linux
- Claude Code
- The Codex CLI, signed in with ChatGPT (checked with 0.159.2)
- Python 3.11 or later; the wrapper uses only the standard library
- Git 2.31 or later

## Install from this checkout

Register the checkout as a local marketplace, then install the plugin from it:

```sh
claude plugin marketplace add /path/to/opus-orchestrator
claude plugin install opus-orchestrator@opus-orchestrator
```

Inside a session, `/plugin marketplace add /path/to/opus-orchestrator` does the same. Claude Code reads the plugin in place from the checkout, so edits take effect in the next session or after `/reload-plugins`.

## Start a Run

```text
/opus-orchestrator:orchestrate [--allow-astra] <task>
```

Only you can start a Run: Claude never invokes the skill on its own. `--allow-astra` lets the Orchestrator use GPT-6 Astra for this Run ([ADR 0003](docs/adr/0003-cost-is-quota-concurrency-capped-astra-needs-permission.md)).

Starting the skill creates a Run record in `.git/opus-orchestrator/runs/<Run id>/`, inside the repository's Git directory, so it is never tracked. Each Delegation leaves a folder there with its full Contract, Codex's JSONL events, the Result and the wrapper's evidence, and for a writing Delegation its diff and the output of each Check the wrapper reran.

A writing Delegation runs in a Git worktree in the system's temporary directory, made from a Snapshot of your working tree: an unreferenced commit recorded through a temporary index, so your index, HEAD and branches stay as they are. The worktree is removed when the Delegation ends, also when it fails or the wrapper is stopped.

At most three Delegations run Codex at once on the machine, across every Run and repository, because the ChatGPT Quota belongs to your account ([ADR 0003](docs/adr/0003-cost-is-quota-concurrency-capped-astra-needs-permission.md)). A further Delegation waits for a slot; its waiting time is in its evidence and doesn't count towards its timeout. The slots are locks on files in `~/.cache/opus-orchestrator/slots/` (or under `$XDG_CACHE_HOME`), so a slot is released when its wrapper exits, even when it is killed.

## What a Run sends to OpenAI

Starting a Run sends that repository's content to OpenAI. Delegates run in Codex, signed in with your ChatGPT account, and read the repository's files, uncommitted changes included. That content is handled under your ChatGPT data controls. On a personal ChatGPT plan, the "Improve the model for everyone" setting also decides whether your Codex tasks are used to train OpenAI's models; see OpenAI's [Data Controls FAQ](https://help.openai.com/en/articles/7730893-data-controls-faq). Start a Run only in repositories you are willing to send.

## Permission rule

The skill approves wrapper calls only for the turn that starts the Run. In auto mode, later calls go to the classifier. In other permission modes, add an allow rule so that Delegations don't prompt every time. Put it in `~/.claude/settings.json` for every project, or in a project's `.claude/settings.local.json`, with your checkout's path:

```json
{
  "permissions": {
    "allow": [
      "Bash(/path/to/opus-orchestrator/plugins/opus-orchestrator/scripts/orchestrator.py *)"
    ]
  }
}
```

## Development

`scripts/verify.sh` runs what CI runs: the wrapper tests and the package checks. The package checks need `jsonschema` (`pip install -r requirements-dev.txt`).

The tests drive the wrapper's command line in temporary Git repositories against a fake Codex, [tests/fake_codex.py](tests/fake_codex.py). It is selected through the `OPUS_ORCHESTRATOR_CODEX` environment variable, which replaces the Codex executable. Its scenarios are built from recorded Codex output; see [tests/fixtures/codex](tests/fixtures/codex/README.md).
