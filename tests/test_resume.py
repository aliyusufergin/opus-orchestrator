"""`delegate --resume`: a follow-up task part that continues an earlier Delegate's Codex session."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from support import (
    FAREWELL,
    GREET,
    NEW_GREET,
    WrapperTestCase,
    WritingDelegationTestCase,
    stdout_field,
)

FOLLOW_UP = "# Follow-up\nAlso say where greet() is defined.\n"
FOLLOWED_UP_FAREWELL = 'def farewell(name):\n    """Return a farewell for the given name."""\n    return f"Goodbye, {name}!"\n'
READ_ONLY_THREAD = "01a1159d-26a8-7c41-be41-af6ec376cc46"
WRITING_THREAD = "01a1159d-9fe5-7490-b406-718479d29be3"


class ResumeTestCase(WrapperTestCase):
    def resume(
        self,
        run_id: str,
        delegation_id: str,
        *extra: str,
        scenario: str = "read-only-done",
        checks: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        task = self.tmp / "follow-up.md"
        task.write_text(FOLLOW_UP)
        return self.run_wrapper(
            "delegate",
            "--run", run_id,
            "--resume", delegation_id,
            "--task", str(task),
            *(arg for check in checks or [] for arg in ("--check", check)),
            *extra,
            scenario=scenario,
        )

    def record_of(self, completed: subprocess.CompletedProcess[str]) -> tuple[Path, dict[str, Any]]:
        """The Delegation directory a `delegate` call wrote, and its evidence."""
        self.assertEqual(completed.returncode, 0, completed.stderr)
        directory = Path(stdout_field(completed.stdout, "Result")).parent
        return directory, json.loads((directory / "evidence.json").read_text())

    def only_resume_call(self) -> Any:
        calls = self.codex_calls("exec resume")
        self.assertEqual(len(calls), 1, "expected exactly one resumed Codex session")
        return calls[0]


class ResumeReadOnlyTest(ResumeTestCase):
    def test_continues_the_codex_session_with_the_follow_up_task_part(self) -> None:
        run_id, _ = self.start_run()
        self.delegate(run_id)

        completed = self.resume(run_id, "d1")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        call = self.only_resume_call()
        self.assertEqual(call.positionals, [READ_ONLY_THREAD, "-"])
        self.assertEqual(call.stdin, FOLLOW_UP)
        self.assertEqual(call.cwd, str(self.repo))
        self.assertEqual(call.option("--sandbox"), "read-only")
        self.assertEqual(call.option("--model"), "gpt-6-luna")
        self.assertEqual(call.config["model_reasoning_effort"], "medium")
        self.assertIn("--ignore-user-config", call.flags)
        self.assertIs(call.config["agents.enabled"], False)
        self.assertIsNotNone(call.option("--output-schema"))

    def test_gets_its_own_result_and_evidence_linked_to_the_delegation_it_resumes(self) -> None:
        run_id, record = self.start_run()
        self.delegate(run_id)

        completed = self.resume(run_id, "d1")

        directory, evidence = self.record_of(completed)
        self.assertEqual(directory, record / "delegations" / "d2")
        self.assertEqual(evidence["delegation_id"], "d2")
        self.assertEqual(evidence["resumes"], "d1")
        self.assertEqual(evidence["thread_id"], READ_ONLY_THREAD)
        self.assertEqual(evidence["model"], "gpt-6-luna")
        self.assertEqual(evidence["write_scope"], "none")
        self.assertEqual(json.loads((directory / "result.json").read_text())["status"], "done")
        self.assertEqual((directory / "contract.md").read_text(), FOLLOW_UP)
        self.assertEqual(stdout_field(completed.stdout, "Resumes"), "d1")
        first = json.loads((record / "delegations" / "d1" / "evidence.json").read_text())
        self.assertIsNone(first["resumes"])

    def test_report_names_the_delegation_resumed(self) -> None:
        run_id, _ = self.start_run()
        self.delegate(run_id)
        self.resume(run_id, "d1")

        report = self.run_wrapper("report", "--run", run_id)

        self.assertEqual(report.returncode, 0, report.stderr)
        d2 = next(line for line in report.stdout.splitlines() if line.startswith("d2 "))
        self.assertIn("resumes d1", d2)


class ResumeRefusalTest(ResumeTestCase):
    def assert_refused(self, completed: subprocess.CompletedProcess[str], text: str) -> None:
        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn(text, completed.stderr)
        self.assertEqual(self.codex_calls("exec resume"), [])

    def test_refuses_a_delegation_the_run_lacks(self) -> None:
        run_id, _ = self.start_run()

        self.assert_refused(self.resume(run_id, "d1"), "no Delegation 'd1'")

    def test_refuses_a_delegation_codex_gave_no_session(self) -> None:
        run_id, _ = self.start_run()
        self.delegate(run_id, scenario="no-thread")

        self.assert_refused(self.resume(run_id, "d1"), "no Codex session")

    def test_refuses_a_model_effort_or_write_scope_of_its_own(self) -> None:
        run_id, _ = self.start_run()
        self.delegate(run_id)

        for extra in (["--model", "gpt-6-luna"], ["--effort", "high"], ["--write-scope", "src/"]):
            with self.subTest(extra=extra):
                self.assert_refused(self.resume(run_id, "d1", *extra), "keeps")

    def test_requires_model_effort_and_write_scope_without_resume(self) -> None:
        run_id, _ = self.start_run()

        completed = self.run_wrapper(
            "delegate", "--run", run_id, "--task", str(self.write_task("# Goal\n")),
            "--model", "gpt-6-luna", "--effort", "medium",
        )

        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn("--write-scope", completed.stderr)


class ResumeWritingTest(ResumeTestCase, WritingDelegationTestCase):
    def test_recreates_the_worktree_at_the_same_path_with_the_previous_changes(self) -> None:
        run_id, _ = self.start_run()
        self.delegate(run_id, write_scope=["src/"], scenario="write-done")
        first = self.only_codex_call()

        completed = self.resume(run_id, "d1", scenario="write-followup")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        call = self.only_resume_call()
        self.assertEqual(call.positionals, [WRITING_THREAD, "-"])
        self.assertEqual(call.cwd, first.cwd)
        self.assertEqual(call.option("--cd"), first.cwd)
        self.assertEqual(call.option("--sandbox"), "workspace-write")
        self.assertIs(call.config["sandbox_workspace_write.network_access"], False)
        self.assertEqual(
            call.files,
            {"README.md": "# Demo\n", "src/farewell.py": FAREWELL, "src/greet.py": NEW_GREET},
        )
        self.assertFalse(Path(call.cwd).exists())
        self.assertEqual(self.worktrees(), [])

    def test_measures_the_new_diff_against_the_original_snapshot(self) -> None:
        run_id, _ = self.start_run()
        _, first = self.record_of(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))
        # The working tree moves on; the resumed Delegate still starts from the first Snapshot.
        (self.repo / "README.md").write_text("# Demo, edited\n")

        _, evidence = self.record_of(
            self.resume(run_id, "d1", scenario="write-followup", checks=["test -f src/farewell.py"])
        )

        self.assertEqual(evidence["resumes"], "d1")
        self.assertEqual(evidence["snapshot"], first["snapshot"])
        self.assertEqual(evidence["write_scope"], ["src"])
        self.assertEqual(evidence["changed_paths"], ["src/farewell.py", "src/greet.py", "src/old.py"])
        self.assertEqual(evidence["outside_write_scope"], [])
        self.assertEqual([check["exit_code"] for check in evidence["check_reruns"]], [0])
        self.assertEqual(self.files()["src/greet.py"], GREET, "the main working tree should be unchanged")

        applied = self.run_wrapper("apply", "--run", run_id, "--delegation", "d2")

        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(
            self.files(),
            {
                "README.md": "# Demo, edited\n",
                "src/farewell.py": FOLLOWED_UP_FAREWELL,
                "src/greet.py": NEW_GREET,
            },
        )

    def test_refuses_while_the_worktree_path_is_taken_and_starts_no_delegation(self) -> None:
        run_id, record = self.start_run()
        _, first = self.record_of(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))
        Path(first["worktree"]).mkdir()
        self.addCleanup(Path(first["worktree"]).rmdir)

        completed = self.resume(run_id, "d1", scenario="write-followup")

        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn(first["worktree"], completed.stderr)
        self.assertEqual(self.codex_calls("exec resume"), [])
        self.assertFalse((record / "delegations" / "d2").exists())
