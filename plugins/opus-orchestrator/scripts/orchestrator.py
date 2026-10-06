#!/usr/bin/env python3
"""The Orchestrator's wrapper around `codex exec`.

Commands:
  start-run  create a Run record and print the Run id
  delegate   run one Delegation through Codex and write its Result
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
FIXED_PART = PLUGIN_ROOT / "contract" / "fixed-part.md"
RESULT_SCHEMA = PLUGIN_ROOT / "schemas" / "result.schema.json"
MODEL_NOTES = PLUGIN_ROOT / "skills" / "orchestrate" / "model-notes.md"

# Replaces the Codex executable; the test seam.
CODEX_ENV = "OPUS_ORCHESTRATOR_CODEX"
# Replaces the Model notes, so tests can date them.
MODEL_NOTES_ENV = "OPUS_ORCHESTRATOR_MODEL_NOTES"

# Older notes may no longer match the catalog or the models' measured strengths.
MODEL_NOTES_MAX_AGE_DAYS = 30
# `ultra` is xhigh plus automatic subagent delegation, which Delegates never get (ADR 0001).
REFUSED_EFFORTS = {"ultra"}

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


def codex_executable() -> str:
    return os.environ.get(CODEX_ENV) or "codex"


def read_catalog(cwd: Path) -> list[dict[str, Any]]:
    """The models Codex's live catalog lists, from `codex debug models`.

    Hidden models are Codex's own or retired, so they are neither offered nor accepted.
    """
    command = [codex_executable(), "debug", "models"]
    try:
        completed = subprocess.run(
            command, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True
        )
    except OSError as error:
        raise WrapperError(
            f"cannot run Codex ({command[0]}) to read its model catalog: {error.strerror}; "
            f"set {CODEX_ENV} to its path"
        ) from None
    if completed.returncode != 0:
        raise WrapperError(
            f"codex debug models failed (exit code {completed.returncode}): {completed.stderr.strip()}"
        )
    try:
        models = json.loads(completed.stdout)["models"]
    except (ValueError, KeyError, TypeError):
        raise WrapperError("codex debug models printed no model catalog") from None
    if not isinstance(models, list):
        raise WrapperError("codex debug models printed no model catalog")
    return [
        model
        for model in models
        if isinstance(model, dict)
        and isinstance(model.get("slug"), str)
        and model.get("visibility", "list") == "list"
    ]


def supported_efforts(model: dict[str, Any]) -> list[str]:
    levels = model.get("supported_reasoning_levels")
    if not isinstance(levels, list):
        return []
    efforts = (level.get("effort") for level in levels if isinstance(level, dict))
    return [effort for effort in efforts if isinstance(effort, str)]


def model_notes_path() -> Path:
    return Path(os.environ.get(MODEL_NOTES_ENV) or MODEL_NOTES)


def read_model_notes(path: Path) -> tuple[str | None, set[str]]:
    """The Model notes' `date` field as written, and the models their table covers."""
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    dated = None
    for line in (match.group(1) if match else "").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "date":
            dated = value.strip().strip("\"'")
    covered = set()
    for line in text.splitlines():
        cells = line.strip().split("|")
        if line.lstrip().startswith("|") and len(cells) > 2:
            covered.update(re.findall(r"`([^`]+)`", cells[1]))
    return dated, covered


def model_notes_warnings(notes: Path, dated: str | None, today: date) -> list[str]:
    try:
        age = (today - date.fromisoformat(dated or "")).days
    except ValueError:
        return [f"the Model notes ({notes}) have no `date: YYYY-MM-DD` line; treat them as stale"]
    if age > MODEL_NOTES_MAX_AGE_DAYS:
        return [
            f"the Model notes are {age} days old (dated {dated}); their routing guidance may be stale"
        ]
    return []


def print_models(cwd: Path) -> None:
    """Show the live catalog's models and warn where the Model notes may mislead."""
    notes = model_notes_path()
    warnings = []
    covered: set[str] | None = None
    try:
        dated, covered = read_model_notes(notes)
    except OSError as error:
        warnings.append(f"cannot read the Model notes: {error}")
    else:
        print(f"Model notes: {notes} (dated {dated})")
        warnings += model_notes_warnings(notes, dated, date.today())
    try:
        listed = [model["slug"] for model in read_catalog(cwd)]
    except WrapperError as error:
        warnings.append(f"cannot check the live model catalog: {error}")
    else:
        print(f"Models: {', '.join(listed)}")
        uncovered = [slug for slug in listed if covered is not None and slug not in covered]
        if uncovered:
            warnings.append(
                f"the Model notes don't cover {', '.join(uncovered)}; "
                "route by the catalog's description until they do"
            )
    for warning in warnings:
        print(f"Warning: {warning}")


def check_model_and_effort(cwd: Path, model: str, effort: str) -> None:
    """Refuse `ultra`, and any model or effort missing from the live catalog."""
    if effort in REFUSED_EFFORTS:
        raise WrapperError(
            f"effort {effort!r} is refused: it adds automatic subagent delegation; use xhigh at most",
            EXIT_USAGE,
        )
    catalog = {entry["slug"]: entry for entry in read_catalog(cwd)}
    if model not in catalog:
        raise WrapperError(
            f"model {model!r} isn't listed in Codex's live model catalog; available: {', '.join(catalog)}",
            EXIT_USAGE,
        )
    efforts = [e for e in supported_efforts(catalog[model]) if e not in REFUSED_EFFORTS]
    if efforts and effort not in efforts:
        raise WrapperError(
            f"model {model!r} doesn't support effort {effort!r}; supported: {', '.join(efforts)}",
            EXIT_USAGE,
        )


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
    print_models(Path.cwd())
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


def codex_command(args: argparse.Namespace, workdir: Path, last_message: Path) -> list[str]:
    return [
        codex_executable(),
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
    check_model_and_effort(workdir, args.model, args.effort)

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
    print(f"Summary: {summary}")


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
