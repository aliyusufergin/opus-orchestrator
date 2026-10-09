#!/usr/bin/env python3
"""A fake `claude` for the test-case runner's tests.

It records what it received and the state of the clone it ran in, makes the edits a test
asks for, leaves Delegations' evidence in the clone's Run record as the wrapper would,
and prints a headless JSON result.

Environment:
- FAKE_CLAUDE_RECORD: the file to write the record of this call to (JSON).
- FAKE_CLAUDE_EDITS: optional JSON object of repository-relative path to new content.
- FAKE_CLAUDE_USAGE: optional JSON list of Codex usage objects, one per Delegation.
- FAKE_CLAUDE_RESULT: the final message, "Done." by default.
- FAKE_CLAUDE_EXIT: the exit code, 0 by default.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], capture_output=True, text=True)
    return completed.stdout.strip()


def option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def main() -> int:
    argv = sys.argv[1:]
    plugin_dir = option(argv, "--plugin-dir")
    skill = Path(plugin_dir, "skills", "orchestrate", "SKILL.md") if plugin_dir else None
    record = {
        "argv": argv,
        "cwd": os.getcwd(),
        "stdin": sys.stdin.read() if not sys.stdin.closed else None,
        "head": git("rev-parse", "HEAD"),
        "commits": git("rev-list", "--all").split(),
        "remotes": git("remote").split(),
        "status": git("status", "--porcelain"),
        "skill": skill.read_text() if skill else None,
        "plugin_files": sorted(
            str(path.relative_to(plugin_dir)) for path in Path(plugin_dir).rglob("*")
        ) if plugin_dir else None,
    }
    Path(os.environ["FAKE_CLAUDE_RECORD"]).write_text(json.dumps(record))

    for path, content in json.loads(os.environ.get("FAKE_CLAUDE_EDITS", "{}")).items():
        Path(path).write_text(content)

    git_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    for number, usage in enumerate(json.loads(os.environ.get("FAKE_CLAUDE_USAGE", "[]")), start=1):
        delegation = git_dir / "opus-orchestrator" / "runs" / "run-1" / f"d{number}"
        delegation.mkdir(parents=True)
        evidence = {"model": "gpt-6.1-sol", "effort": "medium", "usage": usage}
        (delegation / "evidence.json").write_text(json.dumps(evidence))

    print(json.dumps({
        "type": "result",
        "is_error": False,
        "num_turns": 3,
        "result": os.environ.get("FAKE_CLAUDE_RESULT", "Done."),
        "total_cost_usd": 1.5,
        "modelUsage": {
            "claude-opus-5-5": {
                "inputTokens": 10,
                "outputTokens": 200,
                "cacheReadInputTokens": 3000,
                "cacheCreationInputTokens": 400,
            },
            "claude-haiku-5-5": {
                "inputTokens": 1,
                "outputTokens": 20,
                "cacheReadInputTokens": 300,
                "cacheCreationInputTokens": 40,
            },
        },
    }))
    return int(os.environ.get("FAKE_CLAUDE_EXIT", "0"))


if __name__ == "__main__":
    sys.exit(main())
