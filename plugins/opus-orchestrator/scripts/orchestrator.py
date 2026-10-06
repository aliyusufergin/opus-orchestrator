#!/usr/bin/env python3
"""The Orchestrator's wrapper around `codex exec`.

Commands:
  start-run  create a Run record and print the Run id
  delegate   run one Delegation through Codex and write its Result
  report     print one line per Delegation of a Run, with token totals per model
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FIXED_PART = PLUGIN_ROOT / "contract" / "fixed-part.md"
RESULT_SCHEMA = PLUGIN_ROOT / "schemas" / "result.schema.json"

# Replaces the Codex executable; the test seam.
CODEX_ENV = "OPUS_ORCHESTRATOR_CODEX"

# Run records live in the repository's Git directory, so they are never tracked.
RECORD_DIR = "opus-orchestrator"

EXIT_WRAPPER_ERROR = 1
EXIT_USAGE = 2

USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
SUMMARY_LIMIT = 300


class WrapperError(Exception):
    """Stops the wrapper with a message and a non-zero exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_WRAPPER_ERROR) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise WrapperError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


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


def run_record(cwd: Path, run_id: str) -> Path:
    run_dir = runs_dir(cwd) / run_id
    if run_id in {"", ".", ".."} or Path(run_id).name != run_id or not (run_dir / "run.json").is_file():
        raise WrapperError(f"no Run {run_id!r} in this repository; start one with start-run", EXIT_USAGE)
    return run_dir


def new_delegation(run_dir: Path) -> Path:
    delegations = run_dir / "delegations"
    taken = len(list(delegations.iterdir())) if delegations.exists() else 0
    return create_first_free(delegations, (f"d{n}" for n in itertools.count(taken + 1)))


def delegations_in_order(run_dir: Path) -> list[Path]:
    """The Run's Delegation directories, d1, d2, ... in the order they were started."""
    delegations = run_dir / "delegations"
    if not delegations.is_dir():
        return []
    found = [p for p in delegations.iterdir() if p.is_dir() and p.name[1:].isdigit()]
    return sorted(found, key=lambda p: int(p.name[1:]))


def codex_command(args: argparse.Namespace, workdir: Path, last_message: Path) -> list[str]:
    return [
        os.environ.get(CODEX_ENV) or "codex",
        "exec",
        "--model", args.model,
        "-c", f"model_reasoning_effort={json.dumps(args.effort)}",
        # A minimal environment: no user config, account apps or Codex's own agents (ADR 0006).
        "--ignore-user-config",
        "--disable", "apps",
        "-c", "agents.enabled=false",
        # Network off: the read-only sandbox gives commands no network, and hosted web search is off.
        "--sandbox", "read-only",
        "-c", 'web_search="disabled"',
        "--json",
        "--output-schema", str(RESULT_SCHEMA),
        "--output-last-message", str(last_message),
        "--cd", str(workdir),
        "-",  # The Contract comes on stdin.
    ]


def delegate(args: argparse.Namespace) -> int:
    if args.write_scope != "none":
        raise WrapperError("only Write scope `none` (a read-only Delegation) is supported", EXIT_USAGE)
    cwd = Path.cwd()
    run_dir = run_record(cwd, args.run)
    try:
        task_part = Path(args.task).read_text()
    except OSError as error:
        raise WrapperError(f"cannot read the task part: {error}", EXIT_USAGE) from None
    workdir = Path(git(cwd, "rev-parse", "--show-toplevel"))

    contract = f"{FIXED_PART.read_text().rstrip()}\n\n{task_part}"
    delegation_dir = new_delegation(run_dir)
    delegation_id = delegation_dir.name
    (delegation_dir / "contract.md").write_text(contract)
    last_message = delegation_dir / "last-message.txt"

    command = codex_command(args, workdir, last_message)
    events_path = delegation_dir / "events.jsonl"
    started_at, started = now(), time.monotonic()
    with open(events_path, "wb") as events, open(delegation_dir / "codex-stderr.log", "wb") as stderr:
        try:
            codex = subprocess.run(
                command, input=contract.encode(), stdout=events, stderr=stderr, cwd=workdir
            )
        except OSError as error:
            raise WrapperError(
                f"cannot run Codex ({command[0]}): {error.strerror}; set {CODEX_ENV} to its path"
            ) from None
    duration = time.monotonic() - started

    result = read_json_object(last_message)  # The Delegate's final message.
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
        "write_scope": args.write_scope,
        "started_at": started_at,
        "ended_at": now(),
        "duration_seconds": round(duration, 3),
        "thread_id": thread_id,
        "usage": usage,
        "codex_exit_code": codex.returncode,
    }
    result_path = delegation_dir / "result.json"
    write_json(result_path, result)
    write_json(delegation_dir / "evidence.json", evidence)
    print_summary(result_path, result, evidence)
    return 0


def read_json_object(path: Path) -> dict[str, Any] | None:
    """The file's content, if it is a JSON object."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def add_usage(total: dict[str, int] | None, usage: dict[str, Any]) -> dict[str, int]:
    """`total` with the token counts in `usage` added; non-integer counts count as zero."""
    total = total or dict.fromkeys(USAGE_FIELDS, 0)
    for field in USAGE_FIELDS:
        count = usage.get(field)
        total[field] += count if isinstance(count, int) else 0
    return total


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
            usage = add_usage(usage, event["usage"])
    return thread_id, usage


def format_tokens(usage: dict[str, int] | None) -> str:
    if not usage:
        return "not reported"
    return (
        f"{usage['input_tokens']} input ({usage['cached_input_tokens']} cached), "
        f"{usage['output_tokens']} output ({usage['reasoning_output_tokens']} reasoning)"
    )


def print_summary(result_path: Path, result: dict[str, Any], evidence: dict[str, Any]) -> None:
    tokens = format_tokens(evidence["usage"])
    summary = " ".join(str(result.get("summary", "")).split())
    if len(summary) > SUMMARY_LIMIT:
        summary = summary[: SUMMARY_LIMIT - 1] + "…"
    print(f"Result: {result_path}")
    print(f"Delegation: {evidence['delegation_id']}")
    print(f"Status: {result.get('status')}")
    print(f"Model: {evidence['model']}, effort {evidence['effort']}")
    print(f"Duration: {evidence['duration_seconds']:.1f} s")
    print(f"Tokens: {tokens}")
    print(f"Summary: {summary}")


def astra_mark(model: str) -> str:
    # Astra needs the user's permission, so every Astra Delegation stands out (ADR 0003).
    return "  ASTRA" if "astra" in model.lower() else ""


def format_seconds(seconds: Any) -> str:
    return f"{seconds:.1f} s" if isinstance(seconds, (int, float)) else "not recorded"


def report(args: argparse.Namespace) -> int:
    run_dir = run_record(Path.cwd(), args.run)
    delegation_dirs = delegations_in_order(run_dir)
    print(f"Run {args.run}: " + (f"{len(delegation_dirs)} Delegations" if delegation_dirs else "no Delegations"))

    # Per model: Delegation count and summed usage, None while no Delegation reported usage.
    totals: dict[str, tuple[int, dict[str, int] | None]] = {}
    for delegation_dir in delegation_dirs:
        evidence = read_json_object(delegation_dir / "evidence.json")
        if evidence is None:
            print(f"{delegation_dir.name}  no evidence: still running, or the wrapper failed")
            continue
        model = str(evidence.get("model"))
        result = read_json_object(delegation_dir / "result.json")
        status = str(result.get("status")) if result else "no Result"
        if evidence.get("failure_kind"):
            status += f" ({evidence['failure_kind']})"
        usage = evidence.get("usage")
        print(
            f"{delegation_dir.name}  {model}{astra_mark(model)}  "
            f"effort {evidence.get('effort')}  {status}  "
            f"tokens {format_tokens(usage)}  "
            f"waited {format_seconds(evidence.get('wait_seconds'))}, "
            f"ran {format_seconds(evidence.get('duration_seconds'))}"
        )
        count, summed = totals.get(model, (0, None))
        totals[model] = (count + 1, add_usage(summed, usage) if isinstance(usage, dict) else summed)

    if totals:
        print("Tokens per model:")
    for model, (count, summed) in totals.items():
        print(
            f"  {model}: {format_tokens(summed)}, {count} Delegation{'' if count == 1 else 's'}"
            f"{astra_mark(model)}"
        )
    return 0


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
    delegate_command.add_argument("--write-scope", required=True, help="`none` for a read-only Delegation")
    delegate_command.set_defaults(handler=delegate)

    report_command = commands.add_parser("report", help="print one line per Delegation of a Run")
    report_command.add_argument("--run", required=True, help="the Run id from start-run")
    report_command.set_defaults(handler=report)

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        return int(args.handler(args))
    except WrapperError as error:
        print(f"orchestrator: {error}", file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
