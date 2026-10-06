#!/usr/bin/env python3
"""Package checks: the plugin manifest, the marketplace entry, the orchestrate
skill's frontmatter, the Result schema and local Markdown links.

Prints each failure and exits 1 if there is any.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_ROOT = REPO_ROOT / "plugins" / "opus-orchestrator"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
SKILL = PLUGIN_ROOT / "skills" / "orchestrate" / "SKILL.md"
WRAPPER = PLUGIN_ROOT / "scripts" / "orchestrator.py"
RESULT_SCHEMA = PLUGIN_ROOT / "schemas" / "result.schema.json"

RESULT_FIELDS = {
    "status",
    "summary",
    "changed_files",
    "checks",
    "assumptions",
    "open_questions",
    "findings",
}
# Keywords the Result schema may use: those Codex's output schemas accept in strict mode.
SCHEMA_KEYWORDS = {
    "type",
    "description",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "anyOf",
}
KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def check_plugin_manifest() -> list[str]:
    manifest = load_json(PLUGIN_MANIFEST)
    problems = []
    if not KEBAB_CASE.match(str(manifest.get("name", ""))):
        problems.append("plugin.json: name must be kebab-case")
    for field in ("version", "description"):
        if not manifest.get(field):
            problems.append(f"plugin.json: {field} is missing")
    if not manifest.get("author", {}).get("name"):
        problems.append("plugin.json: author.name is missing")
    return problems


def check_marketplace() -> list[str]:
    marketplace = load_json(MARKETPLACE)
    plugin_name = load_json(PLUGIN_MANIFEST).get("name")
    problems = []
    if not KEBAB_CASE.match(str(marketplace.get("name", ""))):
        problems.append("marketplace.json: name must be kebab-case")
    if not marketplace.get("owner", {}).get("name"):
        problems.append("marketplace.json: owner.name is missing")
    entries = [e for e in marketplace.get("plugins", []) if e.get("name") == plugin_name]
    if len(entries) != 1:
        return problems + [f"marketplace.json: needs exactly one entry named {plugin_name!r}"]
    source = entries[0].get("source")
    if not isinstance(source, str) or not source.startswith("./") or ".." in Path(source).parts:
        problems.append("marketplace.json: the entry's source must be a ./ path inside the repository")
    elif (REPO_ROOT / source).resolve() != PLUGIN_ROOT:
        problems.append(f"marketplace.json: the entry's source {source!r} isn't the plugin directory")
    return problems


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(), re.DOTALL)
    if not match:
        return {}, path.read_text()
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, match.group(2)


def check_skill() -> list[str]:
    fields, body = frontmatter(SKILL)
    problems = []
    if not fields:
        return ["SKILL.md: no frontmatter"]
    if fields.get("disable-model-invocation") != "true":
        problems.append("SKILL.md: disable-model-invocation must be true (user-invoked only)")
    if fields.get("user-invocable", "true") != "true":
        problems.append("SKILL.md: the user must be able to invoke the skill")
    if not fields.get("description"):
        problems.append("SKILL.md: description is missing")
    if "!`${CLAUDE_PLUGIN_ROOT}/scripts/orchestrator.py start-run`" not in body:
        problems.append("SKILL.md: the body must run the wrapper's start-run through shell injection")
    if not os.access(WRAPPER, os.X_OK):
        problems.append("scripts/orchestrator.py must be executable")
    return problems


def check_result_schema() -> list[str]:
    schema = load_json(RESULT_SCHEMA)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        return [f"result.schema.json: not a valid JSON Schema: {error.message}"]
    problems = strict_mode_problems(schema, "result.schema.json")
    if set(schema.get("required", [])) != RESULT_FIELDS:
        problems.append(f"result.schema.json: the Result needs exactly the fields {sorted(RESULT_FIELDS)}")
    status = schema.get("properties", {}).get("status", {})
    if status.get("enum") != ["done", "partial", "blocked"]:
        problems.append("result.schema.json: status must be done, partial or blocked")
    return problems


def strict_mode_problems(node: Any, where: str) -> list[str]:
    """Strict output schemas need every property required and no extra properties."""
    if not isinstance(node, dict):
        return []
    problems = [f"{where}: unsupported keyword {key!r}" for key in node if key not in SCHEMA_KEYWORDS]
    if node.get("type") == "object":
        if node.get("additionalProperties") is not False:
            problems.append(f"{where}: objects need additionalProperties false")
        if set(node.get("required", [])) != set(node.get("properties", {})):
            problems.append(f"{where}: every property must be required (use null when it doesn't apply)")
    for name, child in node.get("properties", {}).items():
        problems += strict_mode_problems(child, f"{where} > {name}")
    if "items" in node:
        problems += strict_mode_problems(node["items"], f"{where} > items")
    for i, child in enumerate(node.get("anyOf", [])):
        problems += strict_mode_problems(child, f"{where} > anyOf[{i}]")
    return problems


INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REFERENCE_LINK = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)")


def markdown_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [REPO_ROOT / line for line in listed.splitlines() if (REPO_ROOT / line).is_file()]


def check_markdown_links() -> list[str]:
    problems = []
    for path in markdown_files():
        in_fence = False
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            text = re.sub(r"`[^`]*`", "", line)
            targets = INLINE_LINK.findall(text) + REFERENCE_LINK.findall(text)
            for target in targets:
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                    continue  # A URL or an anchor in the same file.
                local = (path.parent / target.split("#", 1)[0]).resolve()
                where = f"{path.relative_to(REPO_ROOT)}:{number}"
                if not local.is_relative_to(REPO_ROOT):
                    problems.append(f"{where}: link leaves the repository: {target}")
                elif not local.exists():
                    problems.append(f"{where}: broken link {target}")
    return problems


CHECKS: list[tuple[str, Callable[[], list[str]]]] = [
    ("plugin manifest", check_plugin_manifest),
    ("marketplace entry", check_marketplace),
    ("orchestrate skill", check_skill),
    ("Result schema", check_result_schema),
    ("local Markdown links", check_markdown_links),
]


def main() -> int:
    failed = False
    for name, check in CHECKS:
        try:
            problems = check()
        except (OSError, ValueError) as error:
            problems = [str(error)]
        print(f"{'FAIL' if problems else 'ok'}  {name}")
        for problem in problems:
            print(f"      {problem}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
