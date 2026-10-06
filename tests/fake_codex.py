#!/usr/bin/env python3
"""A stand-in for the `codex` executable in wrapper tests.

It accepts the `codex exec` options of Codex CLI 0.159.2 and rejects anything
else, reads stdin the way `codex exec` does (to end of file, so it hangs when
stdin is left open), records what it received, with options under their long
names and the files it found in its working directory, then plays back a
scenario from tests/fixtures/codex.

`codex debug models` prints a model catalog from tests/fixtures/codex/catalogs.

Environment:
  FAKE_CODEX_SCENARIO  scenario directory to play back
  FAKE_CODEX_CATALOG   catalog file for `codex debug models`
  FAKE_CODEX_RECORD    directory to write the invocation record into
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# `codex exec --help`, Codex CLI 0.159.2.
OPTIONS_WITH_VALUE = {
    "-c": "--config",
    "--config": "--config",
    "--enable": "--enable",
    "--disable": "--disable",
    "-i": "--image",
    "--image": "--image",
    "-m": "--model",
    "--model": "--model",
    "--local-provider": "--local-provider",
    "-p": "--profile",
    "--profile": "--profile",
    "-s": "--sandbox",
    "--sandbox": "--sandbox",
    "-C": "--cd",
    "--cd": "--cd",
    "--add-dir": "--add-dir",
    "--thread-source": "--thread-source",
    "--output-schema": "--output-schema",
    "--color": "--color",
    "-o": "--output-last-message",
    "--output-last-message": "--output-last-message",
}
FLAGS = {
    "--strict-config",
    "--oss",
    "--approve-for-me",
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-bypass-hook-trust",
    "--worktree",
    "--skip-git-repo-check",
    "--ephemeral",
    "--ignore-user-config",
    "--ignore-rules",
    "--json",
}
SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def record(invocation: dict[str, object]) -> None:
    record_dir = Path(os.environ["FAKE_CODEX_RECORD"])
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / f"{os.getpid()}.json").write_text(json.dumps(invocation, indent=2))


def debug_models(argv: list[str]) -> int:
    """`codex debug models`, which takes only config overrides and --bundled."""
    args = iter(argv)
    for arg in args:
        name, has_inline, _ = arg.partition("=")
        if name in {"-c", "--config", "--enable", "--disable"}:
            if not has_inline and next(args, None) is None:
                return fail(f"a value is required for '{name}'")
        elif arg != "--bundled":
            return fail(f"unexpected argument '{arg}' found")
    record(
        {
            "argv": ["debug", "models", *argv],
            "subcommand": "debug models",
            "options": {},
            "flags": [],
            "positionals": [],
            "stdin": None,
            "cwd": os.getcwd(),
            "files": {},
        }
    )
    sys.stdout.write(Path(os.environ["FAKE_CODEX_CATALOG"]).read_text())
    return 0


def files_in(directory: Path) -> dict[str, str]:
    """The text of every file under `directory`, Git's own files aside."""
    return {
        path.relative_to(directory).as_posix(): path.read_text(errors="replace")
        for path in sorted(directory.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(directory).parts
    }


def make_edits(directory: Path, edits: dict[str, Any]) -> None:
    """Change files as a Delegate would: `write` maps paths to new text, `delete` lists paths."""
    for name, text in edits.get("write", {}).items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    for name in edits.get("delete", []):
        (directory / name).unlink()


def main(argv: list[str]) -> int:
    if argv[:2] == ["debug", "models"]:
        return debug_models(argv[2:])
    if argv[:1] != ["exec"]:
        return fail("the fake supports only `codex exec` and `codex debug models`")

    options: dict[str, list[str]] = {}
    flags: list[str] = []
    positionals: list[str] = []
    args = iter(argv[1:])
    for arg in args:
        name, has_inline, inline = arg.partition("=")
        if name in OPTIONS_WITH_VALUE:
            value = inline if has_inline else next(args, None)
            if value is None:
                return fail(f"a value is required for '{name}'")
            options.setdefault(OPTIONS_WITH_VALUE[name], []).append(value)
        elif arg in FLAGS:
            flags.append(arg)
        elif arg.startswith("-") and arg != "-":
            return fail(f"unexpected argument '{arg}' found")
        else:
            positionals.append(arg)

    for mode in options.get("--sandbox", []):
        if mode not in SANDBOX_MODES:
            return fail(f"invalid value '{mode}' for '--sandbox <SANDBOX_MODE>'")

    # As codex exec: `-` forces reading the prompt from stdin; with a prompt
    # argument, piped stdin is read as additional input.
    prompt = positionals[0] if positionals else None
    stdin_text = None
    if prompt == "-" or not sys.stdin.isatty():
        if prompt is None:
            print("Reading prompt from stdin...", file=sys.stderr)
        elif prompt != "-":
            print("Reading additional input from stdin...", file=sys.stderr)
        stdin_text = sys.stdin.read()

    record(
        {
            "argv": argv,
            "subcommand": argv[0],
            "options": options,
            "flags": flags,
            "positionals": positionals,
            "stdin": stdin_text,
            "cwd": os.getcwd(),
            "files": files_in(Path.cwd()),
        }
    )

    scenario = Path(os.environ["FAKE_CODEX_SCENARIO"])
    edits = scenario / "edits.json"
    if edits.exists():
        make_edits(Path.cwd(), json.loads(edits.read_text()))
    sys.stdout.write((scenario / "events.jsonl").read_text())
    sys.stdout.flush()

    hang = scenario / "hang-seconds"
    if hang.exists():
        time.sleep(float(hang.read_text()))

    last_message = scenario / "last-message.json"
    output_paths = options.get("--output-last-message", [])
    if last_message.exists() and output_paths:
        Path(output_paths[-1]).write_text(last_message.read_text())

    exit_code = scenario / "exit-code"
    return int(exit_code.read_text()) if exit_code.exists() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
