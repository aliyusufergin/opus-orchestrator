"""The test-case runner: task definitions, throwaway clones, dry runs and the results log."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from support import PLUGIN_ROOT, TESTS_DIR, git, isolated_env

TEST_CASES = PLUGIN_ROOT / "test-cases"
RUNNER = TEST_CASES / "run.py"
FAKE_CLAUDE = TESTS_DIR / "fake_claude.py"
RUNNER_TIMEOUT_SECONDS = 60

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
ACCEPTANCE_TEST = "from calc import add\nassert add(2, 3) == 5\n"


class TestCaseRunnerTest(unittest.TestCase):
    """A source repository whose second commit fixes a bug and adds its acceptance test."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.clones = self.tmp / "clones"
        self.clones.mkdir()
        self.source = self.tmp / "source"
        self.source.mkdir()
        git(self.source, "init", "--quiet", "--initial-branch=main")
        (self.source / "calc.py").write_text(BUGGY)
        git(self.source, "add", "calc.py")
        git(self.source, "commit", "--quiet", "--message", "Add calc")
        self.start = git(self.source, "rev-parse", "HEAD").strip()
        (self.source / "calc.py").write_text(FIXED)
        (self.source / "test_calc.py").write_text(ACCEPTANCE_TEST)
        git(self.source, "add", "calc.py", "test_calc.py")
        git(self.source, "commit", "--quiet", "--message", "Fix add")
        self.reference = git(self.source, "rev-parse", "HEAD").strip()
        # Work in progress in the source, which no run may touch.
        (self.source / "notes.txt").write_text("mine\n")
        self.results = self.tmp / "results.jsonl"
        self.claude_record = self.tmp / "claude-call.json"

    def write_tasks(self, tasks: str) -> Path:
        path = self.tmp / "tasks.toml"
        path.write_text(tasks)
        return path

    def bug_fix_task(self, check: str = "python3 test_calc.py") -> Path:
        return self.write_tasks(f'''
[[tasks]]
id = "bug-fix"
title = "Fix add"
repository = "{self.source}"
start = "{self.start}"
reference = "{self.reference}"
reference_files = ["test_calc.py"]
check = "{check}"
prompt = """
add() subtracts. Make it add.
"""
''')

    def investigation_task(self) -> Path:
        return self.write_tasks(f'''
[[tasks]]
id = "investigation"
title = "Explain add"
repository = "{self.source}"
start = "{self.start}"
answer = """
It subtracts.
"""
prompt = """
What does add() do?
"""
''')

    def run_runner(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        full_env = isolated_env()
        full_env["OPUS_ORCHESTRATOR_CLAUDE"] = str(FAKE_CLAUDE)
        full_env["FAKE_CLAUDE_RECORD"] = str(self.claude_record)
        full_env["TMPDIR"] = str(self.clones)
        full_env.update(env or {})
        return subprocess.run(
            [str(RUNNER), *args],
            env=full_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=RUNNER_TIMEOUT_SECONDS,
        )

    def claude_call(self) -> dict[str, Any]:
        call: dict[str, Any] = json.loads(self.claude_record.read_text())
        return call

    def results_log(self) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self.results.read_text().splitlines()]

    def assert_source_untouched(self) -> None:
        self.assertEqual(git(self.source, "rev-parse", "HEAD").strip(), self.reference)
        self.assertEqual(git(self.source, "status", "--porcelain"), "?? notes.txt\n")
        self.assertEqual(git(self.source, "worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertEqual(git(self.source, "remote"), "")

    def assert_no_clones_left(self) -> None:
        self.assertEqual(list(self.clones.iterdir()), [])


class ListTest(TestCaseRunnerTest):
    def test_the_five_task_definitions_load(self) -> None:
        completed = self.run_runner("list")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        ids = [line.split()[0] for line in completed.stdout.splitlines()]
        self.assertEqual(ids, ["bug-fix", "feature", "investigation", "refactor", "parallel-feature"])

    def test_refuses_a_task_with_both_a_check_and_an_answer(self) -> None:
        tasks = self.write_tasks(f'''
[[tasks]]
id = "both"
title = "Both"
repository = "{self.source}"
start = "{self.start}"
check = "true"
answer = "yes"
prompt = "Do it."
''')

        completed = self.run_runner("list", "--tasks", str(tasks))

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("both: give either a check or an answer", completed.stderr)


class DryRunTest(TestCaseRunnerTest):
    def test_the_check_fails_at_the_start_and_passes_at_the_reference(self) -> None:
        completed = self.run_runner("dry-run", "--tasks", str(self.bug_fix_task()))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("ok    bug-fix", completed.stdout)
        self.assertFalse(self.claude_record.exists(), "a dry run started Claude")
        self.assert_source_untouched()
        self.assert_no_clones_left()

    def test_a_check_that_already_passes_at_the_start_fails_the_dry_run(self) -> None:
        completed = self.run_runner("dry-run", "--tasks", str(self.bug_fix_task(check="true")))

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("FAIL  bug-fix", completed.stdout)
        self.assertIn("the check passes at the start", completed.stdout)
        self.assert_no_clones_left()

    def test_a_check_that_fails_at_the_reference_fails_the_dry_run(self) -> None:
        completed = self.run_runner("dry-run", "--tasks", str(self.bug_fix_task(check="false")))

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("the check fails at the reference", completed.stdout)

    def test_a_known_answer_task_sets_up_its_clone(self) -> None:
        completed = self.run_runner("dry-run", "--tasks", str(self.investigation_task()))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("ok    investigation", completed.stdout)
        self.assertIn("It subtracts.", completed.stdout)
        self.assert_no_clones_left()


class RunTest(TestCaseRunnerTest):
    def run_task(self, config: str, *args: str, env: dict[str, str] | None = None,
                 tasks: Path | None = None, task: str = "bug-fix") -> subprocess.CompletedProcess[str]:
        return self.run_runner(
            "run", "--task", task, "--config", config,
            "--tasks", str(tasks or self.bug_fix_task()), "--results", str(self.results), *args,
            env=env,
        )

    def test_claude_starts_in_a_throwaway_clone_at_the_start_state(self) -> None:
        completed = self.run_task("alone")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        call = self.claude_call()
        self.assertTrue(Path(call["cwd"]).is_relative_to(self.clones), call["cwd"])
        self.assertEqual(call["head"], self.start)
        self.assertNotIn(self.reference, call["commits"], "the clone holds the reference commit")
        self.assertEqual(call["remotes"], [], "the clone can reach the source")
        self.assertEqual(call["status"], "")
        self.assert_source_untouched()
        self.assert_no_clones_left()

    def test_opus_alone_gets_the_task_prompt_without_the_plugin(self) -> None:
        self.run_task("alone")

        argv = self.claude_call()["argv"]
        self.assertEqual(argv[argv.index("-p") + 1], "add() subtracts. Make it add.\n")
        self.assertEqual(argv[argv.index("--model") + 1], "opus")
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")
        self.assertNotIn("--plugin-dir", argv)
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertIs(settings["enabledPlugins"]["opus-orchestrator@opus-orchestrator"], False)

    def test_the_pointer_configuration_starts_the_skill_with_the_minimal_pointer(self) -> None:
        self.run_task("pointer")

        call = self.claude_call()
        argv = call["argv"]
        self.assertEqual(argv[argv.index("-p") + 1], "/opus-orchestrator:orchestrate add() subtracts. Make it add.\n")
        self.assertEqual(call["skill"], (TEST_CASES / "pointer-skill" / "SKILL.md").read_text())
        self.assertIn("scripts/orchestrator.py", call["plugin_files"])
        self.assertFalse(
            [f for f in call["plugin_files"] if f.startswith("test-cases")],
            "the task definitions and their answers are visible to the Run",
        )

    def test_the_skill_configuration_uses_the_plugin_skill(self) -> None:
        self.run_task("skill")

        call = self.claude_call()
        self.assertEqual(call["skill"], (PLUGIN_ROOT / "skills" / "orchestrate" / "SKILL.md").read_text())
        self.assertFalse([f for f in call["plugin_files"] if f.startswith("test-cases")])
        self.assert_no_clones_left()

    def test_records_a_pass_with_claude_and_codex_tokens_and_wall_time(self) -> None:
        usage = {"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 10, "reasoning_output_tokens": 4}
        env = {"FAKE_CLAUDE_EDITS": json.dumps({"calc.py": FIXED}), "FAKE_CLAUDE_USAGE": json.dumps([usage, usage])}

        completed = self.run_task("pointer", env=env)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        [entry] = self.results_log()
        self.assertEqual(entry["task"], "bug-fix")
        self.assertEqual(entry["config"], "pointer")
        self.assertIs(entry["passed"], True)
        self.assertEqual(entry["changed_paths"], [" M calc.py"])
        self.assertEqual(entry["check"]["exit_code"], 0)
        self.assertGreaterEqual(entry["wall_seconds"], 0)
        self.assertEqual(
            entry["claude"]["tokens"],
            {"input": 11, "cache_creation": 440, "cache_read": 3300, "output": 220},
        )
        self.assertEqual(entry["codex"]["delegations"], 2)
        self.assertEqual(
            entry["codex"]["tokens"],
            {"input_tokens": 200, "cached_input_tokens": 120, "output_tokens": 20, "reasoning_output_tokens": 8},
        )
        self.assertIn("passed", completed.stdout)

    def test_records_a_fail_when_the_check_fails(self) -> None:
        self.run_task("alone")

        [entry] = self.results_log()
        self.assertIs(entry["passed"], False)
        self.assertNotEqual(entry["check"]["exit_code"], 0)
        self.assertIn("AssertionError", entry["check"]["output_tail"])
        self.assertEqual(entry["codex"]["delegations"], 0)
        self.assertIsNone(entry["codex"]["tokens"])

    def test_a_failed_claude_run_is_still_checked_and_recorded(self) -> None:
        self.run_task("alone", env={"FAKE_CLAUDE_EXIT": "1"})

        [entry] = self.results_log()
        self.assertEqual(entry["claude"]["exit_code"], 1)
        self.assertIs(entry["passed"], False)

    def test_keep_leaves_the_clone_for_inspection(self) -> None:
        self.run_task("alone", "--keep")

        [entry] = self.results_log()
        self.assertTrue(Path(entry["clone"], "calc.py").exists())

    def test_a_known_answer_without_a_terminal_is_recorded_ungraded(self) -> None:
        completed = self.run_task(
            "alone", tasks=self.investigation_task(), task="investigation",
            env={"FAKE_CLAUDE_RESULT": "It subtracts b from a."},
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        [entry] = self.results_log()
        self.assertIsNone(entry["passed"])
        self.assertIsNone(entry["check"])
        self.assertEqual(entry["changed_paths"], [])
        self.assertEqual(entry["final_message"], "It subtracts b from a.")
        self.assertIn("It subtracts.", completed.stdout)

    def test_refuses_an_unknown_configuration(self) -> None:
        completed = self.run_task("everything")

        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(self.claude_record.exists())


if __name__ == "__main__":
    unittest.main()
