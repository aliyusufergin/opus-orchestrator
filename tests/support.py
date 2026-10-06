"""Shared helpers for tests that drive the wrapper's command-line interface."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "opus-orchestrator"
WRAPPER = PLUGIN_ROOT / "scripts" / "orchestrator.py"
FAKE_CODEX = TESTS_DIR / "fake_codex.py"
SCENARIOS = TESTS_DIR / "fixtures" / "codex"

# Keeps a test that waits on a hung process from hanging the suite.
WRAPPER_TIMEOUT_SECONDS = 30

@dataclass
class CodexCall:
    """What the fake Codex received in one invocation."""

    argv: list[str]
    subcommand: str
    options: dict[str, list[str]]  # By long name, such as --model.
    flags: list[str]
    positionals: list[str]
    stdin: str | None
    cwd: str

    def option(self, name: str) -> str | None:
        values = self.options.get(name, [])
        return values[-1] if values else None

    @property
    def config(self) -> dict[str, Any]:
        """Config overrides as Codex reads them, `--enable`/`--disable` included."""
        config: dict[str, Any] = {}
        for override in self.options.get("--config", []):
            key, _, raw = override.partition("=")
            try:
                config[key] = tomllib.loads(f"value = {raw}")["value"]
            except tomllib.TOMLDecodeError:
                config[key] = raw  # Codex uses an unparsable value as a literal string.
        for feature in self.options.get("--enable", []):
            config[f"features.{feature}"] = True
        for feature in self.options.get("--disable", []):
            config[f"features.{feature}"] = False
        return config


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=isolated_env(), check=True, capture_output=True, text=True
    ).stdout


def isolated_env() -> dict[str, str]:
    """The environment without the user's Git config or a real Codex override."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "OPUS_ORCHESTRATOR_"))}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    return env


class WrapperTestCase(unittest.TestCase):
    """A temporary Git repository with one commit, and a fake Codex."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "--quiet", "--initial-branch=main")
        (self.repo / "README.md").write_text("# Demo\n")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "--quiet", "--message", "Initial commit")
        self.codex_records = self.tmp / "codex-calls"

    def run_wrapper(
        self,
        *args: str,
        cwd: Path | None = None,
        scenario: str = "read-only-done",
        codex: Path = FAKE_CODEX,
        stdin: int | IO[Any] | None = subprocess.DEVNULL,
    ) -> subprocess.CompletedProcess[str]:
        env = isolated_env()
        env["FAKE_CODEX_SCENARIO"] = str(SCENARIOS / scenario)
        env["FAKE_CODEX_RECORD"] = str(self.codex_records)
        env["OPUS_ORCHESTRATOR_CODEX"] = str(codex)
        return subprocess.run(
            [str(WRAPPER), *args],
            cwd=cwd or self.repo,
            env=env,
            stdin=stdin,
            capture_output=True,
            text=True,
            timeout=WRAPPER_TIMEOUT_SECONDS,
        )

    def start_run(self) -> tuple[str, Path]:
        """Start a Run and return its id and Run record directory."""
        completed = self.run_wrapper("start-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return stdout_field(completed.stdout, "Run id"), Path(
            stdout_field(completed.stdout, "Run record")
        )

    def write_task(self, text: str) -> Path:
        task = self.tmp / "task.md"
        task.write_text(text)
        return task

    def codex_calls(self) -> list[CodexCall]:
        if not self.codex_records.exists():
            return []
        return [
            CodexCall(**json.loads(path.read_text()))
            for path in sorted(self.codex_records.glob("*.json"))
        ]

    def only_codex_call(self) -> CodexCall:
        calls = self.codex_calls()
        self.assertEqual(len(calls), 1, "expected exactly one Codex invocation")
        return calls[0]


def stdout_field(stdout: str, label: str) -> str:
    """The value of a `Label: value` line in the wrapper's output."""
    for line in stdout.splitlines():
        name, sep, value = line.partition(": ")
        if sep and name == label:
            return value
    raise AssertionError(f"no {label!r} line in output:\n{stdout}")
