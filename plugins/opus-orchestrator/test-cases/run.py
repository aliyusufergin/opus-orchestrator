#!/usr/bin/env python3
"""Measure one configuration of the Orchestrator on one test case, in a throwaway clone.

The test cases are in tasks.toml. A run clones the task's repository at its start state,
runs Claude headless in one of three configurations, then judges the outcome by the task's
check or known answer and appends a line to the results log:

- alone:   Opus alone, without the plugin.
- pointer: Opus with the wrapper and the minimal pointer skill in pointer-skill/.
- skill:   Opus with the plugin's own skill.

A dry run sets up each task's clone and runs its check without starting Claude or Codex:
the check must fail at the start and, where the task names a reference, pass there.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TEST_CASES = Path(__file__).resolve().parent
PLUGIN_ROOT = TEST_CASES.parent
TASKS = TEST_CASES / "tasks.toml"
RESULTS = TEST_CASES / "results.jsonl"
POINTER_SKILL = TEST_CASES / "pointer-skill" / "SKILL.md"
PLUGIN_NAME = "opus-orchestrator"
SKILL_COMMAND = f"/{PLUGIN_NAME}:orchestrate"
CONFIGS = ("alone", "pointer", "skill")
CODEX_USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
CLAUDE_USAGE_FIELDS = {
    "input": "inputTokens",
    "cache_creation": "cacheCreationInputTokens",
    "cache_read": "cacheReadInputTokens",
    "output": "outputTokens",
}
OUTPUT_TAIL_CHARS = 4000


class RunnerError(Exception):
    pass


@dataclass
class Task:
    id: str
    title: str
    repository: Path
    start: str
    prompt: str
    check: str | None = None
    answer: str | None = None
    reference: str | None = None
    reference_files: list[str] = field(default_factory=list)


def load_tasks(path: Path) -> list[Task]:
    try:
        entries = tomllib.loads(path.read_text()).get("tasks", [])
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RunnerError(f"cannot read {path}: {error}") from None
    tasks = []
    for entry in entries:
        name = entry.get("id", "?")
        if unknown := set(entry) - set(Task.__dataclass_fields__):
            raise RunnerError(f"{name}: unknown keys {sorted(unknown)}")
        for key in ("id", "title", "repository", "start", "prompt"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise RunnerError(f"{name}: {key} is missing")
        if ("check" in entry) == ("answer" in entry):
            raise RunnerError(f"{name}: give either a check or an answer")
        if entry.get("reference_files") and "reference" not in entry:
            raise RunnerError(f"{name}: reference_files need a reference")
        tasks.append(Task(**{**entry, "repository": Path(entry["repository"]).expanduser()}))
    ids = [task.id for task in tasks]
    if len(set(ids)) != len(ids):
        raise RunnerError(f"{path}: task ids must be unique")
    return tasks


def find_task(tasks: list[Task], task_id: str) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise RunnerError(f"no task {task_id!r}; the tasks are {', '.join(t.id for t in tasks)}")


def git(cwd: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace").strip()
        raise RunnerError(f"git {' '.join(args)} in {cwd} failed: {stderr}")
    return completed.stdout


@contextmanager
def throwaway_clone(task: Task, commit: str, keep: bool = False) -> Iterator[Path]:
    """A new repository holding `commit` and its history only, with no remote.

    Fetching just that commit keeps the reference solution and anything after it out of
    the clone, and without a remote nothing can be pushed back to the user's repository,
    which is only read.
    """
    parent = Path(tempfile.mkdtemp(prefix="opus-orchestrator-test-case-"))
    clone = parent / task.repository.name
    try:
        git(parent, "init", "--quiet", "--initial-branch=main", str(clone))
        git(clone, "fetch", "--quiet", "--no-tags", str(task.repository), commit)
        git(clone, "reset", "--quiet", "--hard", "FETCH_HEAD")
        yield clone
    finally:
        if not keep:
            shutil.rmtree(parent, ignore_errors=True)


def run_check(task: Task, clone: Path) -> dict[str, Any]:
    """Put the reference's files for the check in place, then run the check in the clone."""
    assert task.check is not None
    for path in task.reference_files:
        content = git(task.repository, "show", f"{task.reference}:{path}")
        target = clone / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    completed = subprocess.run(
        ["bash", "-c", task.check],
        cwd=clone,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = completed.stdout.decode(errors="replace")
    return {"command": task.check, "exit_code": completed.returncode, "output_tail": output[-OUTPUT_TAIL_CHARS:]}


def dry_run_task(task: Task) -> list[str]:
    """Problems with a task definition: its clone can't be set up, or its check misjudges."""
    with throwaway_clone(task, task.start) as clone:
        head = git(clone, "rev-parse", "HEAD").decode().strip()
        if head != git(task.repository, "rev-parse", f"{task.start}^{{commit}}").decode().strip():
            return [f"the clone is at {head}, not at the start"]
        if task.check is None:
            return []
        if run_check(task, clone)["exit_code"] == 0:
            return ["the check passes at the start, before any work"]
    if task.reference is None:
        return []
    with throwaway_clone(task, task.reference) as clone:
        result = run_check(task, clone)
        if result["exit_code"] != 0:
            return [f"the check fails at the reference:\n{indent(result['output_tail'][-1000:])}"]
    return []


def indent(text: str) -> str:
    return "\n".join(f"      {line}" for line in text.splitlines())


@contextmanager
def plugin_copy(config: str) -> Iterator[Path | None]:
    """The plugin as the Run sees it, without the test cases and their answers."""
    if config == "alone":
        yield None
        return
    parent = Path(tempfile.mkdtemp(prefix="opus-orchestrator-plugin-"))
    try:
        plugin = parent / PLUGIN_NAME
        shutil.copytree(PLUGIN_ROOT, plugin, ignore=shutil.ignore_patterns("test-cases", "__pycache__"))
        if config == "pointer":
            shutil.copyfile(POINTER_SKILL, plugin / "skills" / "orchestrate" / "SKILL.md")
        yield plugin
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def claude_command(task: Task, model: str, plugin: Path | None) -> list[str]:
    prompt = task.prompt if plugin is None else f"{SKILL_COMMAND} {task.prompt}"
    # An installed copy of the plugin stays off, so only the configuration's copy is loaded.
    settings = {"enabledPlugins": {f"{PLUGIN_NAME}@{PLUGIN_NAME}": False}}
    command = [
        os.environ.get("OPUS_ORCHESTRATOR_CLAUDE", "claude"),
        "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--permission-mode", "auto",
        "--settings", json.dumps(settings),
    ]
    if plugin is not None:
        command += ["--plugin-dir", str(plugin)]
    return command


def claude_tokens(output: dict[str, Any]) -> dict[str, int] | None:
    """Claude's tokens over every model the Orchestrator used, subagents included."""
    models = output.get("modelUsage")
    if not isinstance(models, dict):
        return None
    return {
        name: sum(int(usage.get(key) or 0) for usage in models.values() if isinstance(usage, dict))
        for name, key in CLAUDE_USAGE_FIELDS.items()
    }


def codex_usage(clone: Path) -> dict[str, Any]:
    """Codex's tokens over every Delegation in the clone's Run records."""
    git_dir = Path(git(clone, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
    tokens: dict[str, int] | None = None
    models: dict[str, int] = {}
    delegations = 0
    for evidence_path in sorted((git_dir / PLUGIN_NAME / "runs").glob("*/*/evidence.json")):
        try:
            evidence = json.loads(evidence_path.read_text())
        except (OSError, ValueError):
            continue
        delegations += 1
        model = str(evidence.get("model"))
        models[model] = models.get(model, 0) + 1
        usage = evidence.get("usage")
        if isinstance(usage, dict):
            tokens = tokens or dict.fromkeys(CODEX_USAGE_FIELDS, 0)
            for key in CODEX_USAGE_FIELDS:
                tokens[key] += int(usage.get(key) or 0)
    return {"delegations": delegations, "models": models, "tokens": tokens}


def grade_answer(task: Task, final_message: str) -> bool | None:
    """The user judges a known-answer task; without a terminal it stays ungraded."""
    print(f"\nFinal message:\n{indent(final_message)}\n\nKnown answer:\n{indent(task.answer or '')}\n")
    if not sys.stdin.isatty():
        print("No terminal to ask on, so the run is recorded ungraded (passed: null).")
        return None
    while True:
        reply = input("Does the final message give the known answer? [y/n] ").strip().lower()
        if reply in ("y", "n"):
            return reply == "y"


def run_task(task: Task, config: str, model: str, results: Path, keep: bool) -> int:
    with throwaway_clone(task, task.start, keep=keep) as clone, plugin_copy(config) as plugin:
        command = claude_command(task, model, plugin)
        print(f"Running {task.id} ({config}) in {clone}", flush=True)
        started = time.monotonic()
        try:
            completed = subprocess.run(command, cwd=clone, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        except OSError as error:
            raise RunnerError(f"cannot start Claude: {error}") from None
        wall_seconds = round(time.monotonic() - started, 3)
        try:
            output = json.loads(completed.stdout)
        except ValueError:
            output = {}
        if completed.returncode != 0:
            print(f"Claude exited with {completed.returncode}: {completed.stderr.strip()[-1000:]}", file=sys.stderr)
        final_message = output.get("result") if isinstance(output.get("result"), str) else ""
        # What the Orchestrator left changed, before the check adds the acceptance tests.
        changed = git(clone, "status", "--porcelain", "--untracked-files=all").decode(errors="replace").splitlines()

        check = run_check(task, clone) if task.check is not None else None
        passed = check["exit_code"] == 0 if check is not None else grade_answer(task, final_message)
        entry = {
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": task.id,
            "config": config,
            "model": model,
            "passed": passed,
            "check": check,
            "wall_seconds": wall_seconds,
            "claude": {
                "exit_code": completed.returncode,
                "is_error": output.get("is_error"),
                "num_turns": output.get("num_turns"),
                "tokens": claude_tokens(output),
                "models": output.get("modelUsage"),
            },
            "codex": codex_usage(clone),
            "changed_paths": changed,
            "final_message": final_message,
            "clone": str(clone) if keep else None,
        }
    with results.open("a") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    verdict = {True: "passed", False: "failed", None: "ungraded"}[passed]
    print(f"{task.id} ({config}) {verdict} in {wall_seconds:.0f}s; recorded in {results}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("list", "list the test cases"),
        ("dry-run", "set up each clone and run each check, without Claude or Codex"),
        ("run", "run one configuration on one test case and record it"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--tasks", type=Path, default=TASKS, help="the task definitions")
        if name == "dry-run":
            command.add_argument("--task", action="append", dest="task_ids", help="only this task; repeatable")
        if name == "run":
            command.add_argument("--results", type=Path, default=RESULTS, help="the results log")
            command.add_argument("--task", required=True, dest="task_id", help="the task id")
            command.add_argument("--config", required=True, choices=CONFIGS, help="the configuration")
            command.add_argument("--model", default="opus", help="the Orchestrator's model (default: opus)")
            command.add_argument("--keep", action="store_true", help="keep the clone and its Run records")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        tasks = load_tasks(args.tasks)
        if args.command == "list":
            for task in tasks:
                kind = "check" if task.check is not None else "known answer"
                print(f"{task.id:<18} {task.title} ({kind})")
            return 0
        if args.command == "run":
            return run_task(find_task(tasks, args.task_id), args.config, args.model, args.results, args.keep)
        selected = [find_task(tasks, task_id) for task_id in args.task_ids] if args.task_ids else tasks
        failed = False
        for task in selected:
            print(f"..    {task.id}", flush=True)
            problems = dry_run_task(task)
            print(f"{'FAIL' if problems else 'ok':<4}  {task.id}")
            for problem in problems:
                print(f"      {problem}")
            if task.answer is not None:
                print(f"      known answer:\n{indent(task.answer)}")
            failed = failed or bool(problems)
        return 1 if failed else 0
    except RunnerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
