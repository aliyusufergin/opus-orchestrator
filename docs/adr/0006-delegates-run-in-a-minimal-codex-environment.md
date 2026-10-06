# Delegates run in a minimal Codex environment

By default a Codex session started on this machine loads the user's config (including `gpt-6-astra` as default model), the ChatGPT account's connected apps (Slack, Outlook Email, Teams, SharePoint and others) and its own subagent tools, so a Delegate could read the user's email or start agents the Orchestrator never sees (local probes, Codex CLI 0.159.2). The wrapper therefore always passes `--ignore-user-config`, `--disable apps` and `-c agents.enabled=false`, and keeps network access off unless the Contract grants it. Delegates still read the target repo's `AGENTS.md`, because project conventions help; the fixed part of every Contract states that the Contract takes precedence where they conflict.

## Considered Options

- Keep the user's Codex config so Delegates behave like the user's own Codex: rejected because it leaks the Astra default, account apps and personal approval settings into unattended work.
- Hide `AGENTS.md` from Delegates: rejected because it drops the project's conventions; whether the precedence line resolves conflicts for GPT-6 models is untested and is one of the things the test cases measure.

## Consequences

`--disable multi_agent` does not remove Codex's spawn tools; `-c agents.enabled=false` does. Codex's bundled skills (such as `imagegen`) still load and cannot currently be turned off.
