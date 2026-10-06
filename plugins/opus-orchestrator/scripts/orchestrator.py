#!/usr/bin/env python3
"""The Orchestrator's wrapper around `codex exec`.

Commands:
  start-run  create a Run record and print the Run id
  delegate   run one Delegation through Codex and write its Result
  apply      apply a writing Delegation's diff to the working tree with a three-way apply
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import posixpath
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FIXED_PART = PLUGIN_ROOT / "contract" / "fixed-part.md"
RESULT_SCHEMA = PLUGIN_ROOT / "schemas" / "result.schema.json"

# Replaces the Codex executable; the test seam.
CODEX_ENV = "OPUS_ORCHESTRATOR_CODEX"

# Run records live in the repository's Git directory, so they are never tracked.
RECORD_DIR = "opus-orchestrator"

EXIT_WRAPPER_ERROR = 1
EXIT_USAGE = 2
EXIT_CONFLICTS = 3

# Snapshots are the wrapper's own unreferenced commits, so they never depend on the user's identity.
SNAPSHOT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Opus Orchestrator",
    "GIT_AUTHOR_EMAIL": "opus-orchestrator@localhost",
    "GIT_COMMITTER_NAME": "Opus Orchestrator",
    "GIT_COMMITTER_EMAIL": "opus-orchestrator@localhost",
}

USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
SUMMARY_LIMIT = 300


class WrapperError(Exception):
    """Stops the wrapper with a message and a non-zero exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_WRAPPER_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def git_bytes(cwd: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    completed = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True)
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace").strip()
        raise WrapperError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
    return git_bytes(cwd, *args, env=env).decode(errors="replace").strip()


def runs_dir(cwd: Path) -> Path:
    try:
        git_dir = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    except WrapperError:
        raise WrapperError(
            "not inside a Git repository; a Run keeps its Run record in the repository's Git directory"
        ) from None
    return Path(git_dir) / RECORD_DIR / "runs"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def create_first_free(parent: Path, names: Iterable[str]) -> Path:
    """Create and return the first directory in `parent` whose name isn't taken."""
    parent.mkdir(parents=True, exist_ok=True)
    for name in names:
        try:
            (parent / name).mkdir()
            return parent / name
        except FileExistsError:
            continue
    raise WrapperError(f"no free name for a directory in {parent}")


def start_run(_: argparse.Namespace) -> int:
    run_dir = create_first_free(
        runs_dir(Path.cwd()),
        (
            f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{secrets.token_hex(2)}"
            for _ in itertools.count()
        ),
    )
    run_id = run_dir.name
    write_json(run_dir / "run.json", {"run_id": run_id, "started_at": now()})
    print(f"Run id: {run_id}")
    print(f"Run record: {run_dir}")
    return 0


def is_plain_name(name: str) -> bool:
    return name not in {"", ".", ".."} and Path(name).name == name


def run_record(cwd: Path, run_id: str) -> Path:
    run_dir = runs_dir(cwd) / run_id
    if not is_plain_name(run_id) or not (run_dir / "run.json").is_file():
        raise WrapperError(f"no Run {run_id!r} in this repository; start one with start-run", EXIT_USAGE)
    return run_dir


def new_delegation(run_dir: Path) -> Path:
    delegations = run_dir / "delegations"
    taken = len(list(delegations.iterdir())) if delegations.exists() else 0
    return create_first_free(delegations, (f"d{n}" for n in itertools.count(taken + 1)))


def parse_write_scope(values: list[str]) -> list[str] | None:
    """The repository-relative paths of a Write scope, or None for `none`."""
    if values == ["none"]:
        return None
    paths = []
    for value in values:
        path = posixpath.normpath(value) if value else ""
        if value in {"", "none"} or posixpath.isabs(path) or path == ".." or path.startswith("../"):
            raise WrapperError(
                f"Write scope {value!r} is not a path inside the repository; "
                "give repository-relative paths, or `none` alone",
                EXIT_USAGE,
            )
        paths.append(path)
    return paths


@contextmanager
def working_tree_index(directory: Path, base: str | None) -> Iterator[dict[str, str]]:
    """An environment in which Git's index is a temporary one holding `directory`'s working tree.

    Untracked files are in it unless ignored; files in the `base` commit count as tracked. The
    user's own index is neither read nor written.
    """
    with tempfile.TemporaryDirectory(prefix="opus-orchestrator-index-") as scratch:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch) / "index")}
        git(directory, "read-tree", *([base] if base else ["--empty"]), env=env)
        git(directory, "add", "--all", env=env)
        yield env


def head_commit(toplevel: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        cwd=toplevel, capture_output=True, text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def take_snapshot(toplevel: Path) -> str:
    """Record the working tree, with untracked files that aren't ignored, as an unreferenced commit.

    It is built in a temporary index, so the user's index, HEAD and branches stay as they are.
    """
    head = head_commit(toplevel)
    with working_tree_index(toplevel, head) as env:
        tree = git(toplevel, "write-tree", env=env)
        return git(
            toplevel,
            "commit-tree", "--no-gpg-sign", *(["-p", head] if head else []),
            "-m", "Opus Orchestrator Snapshot", tree,
            env={**env, **SNAPSHOT_IDENTITY},
        )


@contextmanager
def snapshot_worktree(toplevel: Path, snapshot: str, name: str) -> Iterator[Path]:
    """A worktree outside the repository with the Snapshot checked out, removed afterwards whatever happens."""
    worktree = Path(tempfile.mkdtemp(prefix=f"opus-orchestrator-{name}-")).resolve()
    try:
        # No hooks: a post-checkout hook has no business running in a Delegate's worktree.
        git(
            toplevel,
            "-c", f"core.hooksPath={os.devnull}",
            "worktree", "add", "--detach", "--quiet", str(worktree), snapshot,
        )
        yield worktree
    finally:
        removed = subprocess.run(
            ["git", "worktree", "remove", "--force", "--force", str(worktree)],
            cwd=toplevel, capture_output=True,
        )
        shutil.rmtree(worktree, ignore_errors=True)
        if removed.returncode != 0:
            subprocess.run(["git", "worktree", "prune"], cwd=toplevel, capture_output=True)


def in_write_scope(path: str, write_scope: list[str]) -> bool:
    return any(scope == "." or path == scope or path.startswith(f"{scope}/") for scope in write_scope)


def collect_changes(
    worktree: Path, snapshot: str, write_scope: list[str], delegation_dir: Path
) -> dict[str, Any]:
    """The Delegate's changes against the Snapshot, as evidence, with the diff stored in the Run record."""
    # Files the repository ignores are left out, as they would be from a Snapshot.
    with working_tree_index(worktree, snapshot) as env:
        tree = git(worktree, "write-tree", env=env)
    # Plumbing, so that the user's diff settings (external tools, prefixes, colour) can't change the
    # patch. --binary keeps files that aren't text and gives the full blob ids a three-way apply needs.
    diff_tree = ("diff-tree", "-r", "--no-renames", snapshot, tree)
    diff = delegation_dir / "changes.diff"
    diff.write_bytes(git_bytes(worktree, *diff_tree, "--patch", "--binary"))
    changed = git_bytes(worktree, *diff_tree, "--name-only", "-z").decode(errors="replace")
    changed_paths = sorted(path for path in changed.split("\0") if path)
    return {
        "snapshot": snapshot,
        "diff": str(diff),
        "changed_paths": changed_paths,
        "outside_write_scope": [path for path in changed_paths if not in_write_scope(path, write_scope)],
    }


def sandbox_options(write_scope: list[str] | None) -> list[str]:
    if write_scope is None:
        # The read-only sandbox also gives commands no network.
        return ["--sandbox", "read-only"]
    return [
        "--sandbox", "workspace-write",
        # Writable only in the worktree (`--cd`): not /tmp or $TMPDIR, which workspace-write
        # adds by default, and no network.
        "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
        "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
        "-c", "sandbox_workspace_write.network_access=false",
    ]


def codex_command(
    args: argparse.Namespace, write_scope: list[str] | None, workdir: Path, last_message: Path
) -> list[str]:
    return [
        os.environ.get(CODEX_ENV) or "codex",
        "exec",
        "--model", args.model,
        "-c", f"model_reasoning_effort={json.dumps(args.effort)}",
        # A minimal environment: no user config, account apps or Codex's own agents (ADR 0006).
        "--ignore-user-config",
        "--disable", "apps",
        "-c", "agents.enabled=false",
        # Network off: none for commands (see sandbox_options), and hosted web search is off.
        *sandbox_options(write_scope),
        "-c", 'web_search="disabled"',
        "--json",
        "--output-schema", str(RESULT_SCHEMA),
        "--output-last-message", str(last_message),
        "--cd", str(workdir),
        "-",  # The Contract comes on stdin.
    ]


def delegate(args: argparse.Namespace) -> int:
    write_scope = parse_write_scope(args.write_scope)
    cwd = Path.cwd()
    run_dir = run_record(cwd, args.run)
    try:
        task_part = Path(args.task).read_text()
    except OSError as error:
        raise WrapperError(f"cannot read the task part: {error}", EXIT_USAGE) from None
    toplevel = Path(git(cwd, "rev-parse", "--show-toplevel"))

    contract = f"{FIXED_PART.read_text().rstrip()}\n\n{task_part}"
    delegation_dir = new_delegation(run_dir)
    delegation_id = delegation_dir.name
    (delegation_dir / "contract.md").write_text(contract)
    last_message = delegation_dir / "last-message.txt"
    events_path = delegation_dir / "events.jsonl"

    started_at, started = now(), time.monotonic()
    if write_scope is None:
        codex = run_codex(codex_command(args, None, toplevel, last_message), contract, toplevel, events_path)
        changes = dict.fromkeys(("snapshot", "diff", "changed_paths", "outside_write_scope"))
    else:
        snapshot = take_snapshot(toplevel)
        with snapshot_worktree(toplevel, snapshot, f"{args.run}-{delegation_id}") as worktree:
            command = codex_command(args, write_scope, worktree, last_message)
            codex = run_codex(command, contract, worktree, events_path)
            changes = collect_changes(worktree, snapshot, write_scope, delegation_dir)
    duration = time.monotonic() - started

    result = read_result(last_message)
    if result is None:
        raise WrapperError(
            f"Codex returned no Result (exit code {codex.returncode}); "
            f"its events and stderr are in {delegation_dir}"
        )
    thread_id, usage = read_events(events_path)
    evidence = {
        "run_id": args.run,
        "delegation_id": delegation_id,
        "model": args.model,
        "effort": args.effort,
        "write_scope": "none" if write_scope is None else write_scope,
        "started_at": started_at,
        "ended_at": now(),
        "duration_seconds": round(duration, 3),
        "thread_id": thread_id,
        "usage": usage,
        "codex_exit_code": codex.returncode,
        **changes,
    }
    result_path = delegation_dir / "result.json"
    write_json(result_path, result)
    write_json(delegation_dir / "evidence.json", evidence)
    print_summary(result_path, result, evidence)
    return 0


def run_codex(
    command: list[str], contract: str, workdir: Path, events_path: Path
) -> subprocess.CompletedProcess[bytes]:
    """Run Codex with the Contract on stdin, its events and stderr going to the Run record."""
    with (
        open(events_path, "wb") as events,
        open(events_path.parent / "codex-stderr.log", "wb") as stderr,
    ):
        try:
            return subprocess.run(command, input=contract.encode(), stdout=events, stderr=stderr, cwd=workdir)
        except OSError as error:
            raise WrapperError(
                f"cannot run Codex ({command[0]}): {error.strerror}; set {CODEX_ENV} to its path"
            ) from None


def read_result(last_message: Path) -> dict[str, Any] | None:
    """The Delegate's final message, if it is a JSON object."""
    try:
        result = json.loads(last_message.read_text())
    except (OSError, ValueError):
        return None
    return result if isinstance(result, dict) else None


def read_events(events_path: Path) -> tuple[str | None, dict[str, int] | None]:
    """The thread id and the summed token usage from Codex's JSONL events."""
    thread_id = None
    usage: dict[str, int] | None = None
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # Not an event; Codex keeps other output on stderr.
        if not isinstance(event, dict):
            continue
        if event.get("type") == "thread.started" and thread_id is None:
            thread_id = event.get("thread_id")
        elif event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = usage or dict.fromkeys(USAGE_FIELDS, 0)
            for field in USAGE_FIELDS:
                count = event["usage"].get(field)
                usage[field] += count if isinstance(count, int) else 0
    return thread_id, usage


def print_summary(result_path: Path, result: dict[str, Any], evidence: dict[str, Any]) -> None:
    usage = evidence["usage"]
    tokens = (
        f"{usage['input_tokens']} input ({usage['cached_input_tokens']} cached), "
        f"{usage['output_tokens']} output ({usage['reasoning_output_tokens']} reasoning)"
        if usage
        else "not reported"
    )
    summary = " ".join(str(result.get("summary", "")).split())
    if len(summary) > SUMMARY_LIMIT:
        summary = summary[: SUMMARY_LIMIT - 1] + "…"
    print(f"Result: {result_path}")
    print(f"Delegation: {evidence['delegation_id']}")
    print(f"Status: {result.get('status')}")
    print(f"Model: {evidence['model']}, effort {evidence['effort']}")
    print(f"Duration: {evidence['duration_seconds']:.1f} s")
    print(f"Tokens: {tokens}")
    if evidence["diff"] is not None:
        print(f"Diff: {evidence['diff']}")
        print(f"Changed paths: {len(evidence['changed_paths'])}")
        print(f"Outside Write scope: {', '.join(evidence['outside_write_scope']) or 'none'}")
    print(f"Summary: {summary}")


def three_way_apply(toplevel: Path, diff: Path) -> list[str]:
    """Apply the diff to the working tree and return the paths left with conflicts."""
    # An index that matches the working tree, so that the three-way apply neither refuses the
    # user's uncommitted changes nor stages anything in the user's own index.
    with working_tree_index(toplevel, head_commit(toplevel)) as env:
        applied = subprocess.run(
            ["git", "apply", "--3way", str(diff)], cwd=toplevel, env=env, capture_output=True, text=True
        )
        unmerged = git_bytes(toplevel, "ls-files", "--unmerged", "-z", env=env).decode(errors="replace")
    conflicts = sorted({entry.partition("\t")[2] for entry in unmerged.split("\0") if entry})
    if applied.returncode != 0 and not conflicts:
        raise WrapperError(f"the diff doesn't apply, so nothing changed: {applied.stderr.strip()}")
    return conflicts


def apply(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    run_dir = run_record(cwd, args.run)
    diff = run_dir / "delegations" / args.delegation / "changes.diff"
    if not is_plain_name(args.delegation) or not diff.is_file():
        raise WrapperError(
            f"no diff for Delegation {args.delegation!r} in Run {args.run}; "
            "only a writing Delegation leaves one",
            EXIT_USAGE,
        )
    # From the top level: run in a subdirectory, git apply would skip the paths outside it.
    toplevel = Path(git(cwd, "rev-parse", "--show-toplevel"))
    conflicts = three_way_apply(toplevel, diff) if diff.stat().st_size else []
    print(f"Applied: {args.delegation}")
    print(f"Conflicts: {', '.join(conflicts) or 'none'}")
    return EXIT_CONFLICTS if conflicts else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="orchestrator", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(required=True, metavar="command")

    start_run_command = commands.add_parser("start-run", help="create a Run record and print the Run id")
    start_run_command.set_defaults(handler=start_run)

    delegate_command = commands.add_parser("delegate", help="run one Delegation through Codex")
    delegate_command.add_argument("--run", required=True, help="the Run id from start-run")
    delegate_command.add_argument("--task", required=True, help="file holding the task part of the Contract")
    delegate_command.add_argument("--model", required=True, help="Codex model, such as gpt-6.1-sol")
    delegate_command.add_argument("--effort", required=True, help="reasoning effort, such as medium")
    delegate_command.add_argument(
        "--write-scope",
        required=True,
        nargs="+",
        metavar="PATH",
        help="repository-relative paths the Delegate may change, or `none` for a read-only Delegation",
    )
    delegate_command.set_defaults(handler=delegate)

    apply_command = commands.add_parser(
        "apply", help="apply a writing Delegation's diff to the working tree with a three-way apply"
    )
    apply_command.add_argument("--run", required=True, help="the Run id from start-run")
    apply_command.add_argument("--delegation", required=True, help="the Delegation id from delegate")
    apply_command.set_defaults(handler=apply)

    return parser.parse_args(argv)


def stop_on_signal(signum: int, _: Any) -> None:
    # Raised so that cleanup runs: Codex is killed and a worktree removed.
    raise WrapperError(f"stopped by {signal.Signals(signum).name}", 128 + signum)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop_on_signal)
    try:
        return int(args.handler(args))
    except WrapperError as error:
        print(f"orchestrator: {error}", file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
