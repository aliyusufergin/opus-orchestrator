"""`delegate` with a Write scope: a writing Delegation in a worktree made from a Snapshot."""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from support import (
    FAREWELL,
    GREET,
    NEW_GREET,
    WRAPPER,
    WRAPPER_TIMEOUT_SECONDS,
    WritingDelegationTestCase,
    git,
    stdout_field,
)


class WorktreeTest(WritingDelegationTestCase):
    def test_runs_codex_in_a_worktree_outside_the_repository_writable_only_there(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        call = self.only_codex_call()
        worktree = Path(call.cwd)
        self.assertEqual(call.option("--cd"), str(worktree))
        self.assertFalse(worktree.is_relative_to(self.repo), worktree)
        self.assertEqual(call.files["src/greet.py"], GREET)
        self.assertEqual(call.option("--sandbox"), "workspace-write")
        self.assertIs(call.config["sandbox_workspace_write.exclude_slash_tmp"], True)
        self.assertIs(call.config["sandbox_workspace_write.exclude_tmpdir_env_var"], True)
        self.assertIs(call.config["sandbox_workspace_write.network_access"], False)
        self.assertEqual(call.options.get("--add-dir"), None)
        self.assertEqual(call.config["web_search"], "disabled")

    def test_removes_the_worktree_afterwards(self) -> None:
        run_id, _ = self.start_run()

        self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertFalse(Path(self.only_codex_call().cwd).exists())
        self.assertEqual(self.worktrees(), [])


class DiffTest(WritingDelegationTestCase):
    def test_stores_the_diff_against_the_snapshot_in_the_run_record(self) -> None:
        run_id, record = self.start_run()
        before = self.files()

        evidence = self.evidence(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))

        self.assertEqual(self.files(), before, "the main working tree should be unchanged")
        diff = Path(evidence["diff"])
        self.assertTrue(diff.is_relative_to(record), diff)
        self.assertEqual(evidence["changed_paths"], ["src/farewell.py", "src/greet.py", "src/old.py"])
        git(self.repo, "apply", str(diff))
        self.assertEqual(
            self.files(),
            {"README.md": "# Demo\n", "src/farewell.py": FAREWELL, "src/greet.py": NEW_GREET},
        )


class SummaryTest(WritingDelegationTestCase):
    def test_names_the_diff_and_the_paths_outside_the_write_scope(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-outside-scope")

        evidence = self.evidence(completed)
        self.assertEqual(stdout_field(completed.stdout, "Diff"), evidence["diff"])
        self.assertEqual(stdout_field(completed.stdout, "Changed paths"), "2")
        self.assertEqual(stdout_field(completed.stdout, "Outside Write scope"), "README.md")
        self.assertLessEqual(len(completed.stdout.splitlines()), 12)

    def test_says_when_nothing_is_outside_the_write_scope(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertEqual(stdout_field(completed.stdout, "Outside Write scope"), "none")


class WriteScopeTest(WritingDelegationTestCase):
    def test_lists_paths_changed_outside_the_write_scope(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(run_id, write_scope=["src/"], scenario="write-outside-scope")
        )

        self.assertEqual(evidence["changed_paths"], ["README.md", "src/greet.py"])
        self.assertEqual(evidence["outside_write_scope"], ["README.md"])

    def test_a_write_scope_path_covers_itself_and_what_is_below_it(self) -> None:
        run_id, _ = self.start_run()
        cases = {
            ("src",): [],
            ("./src/greet.py", "src/farewell.py", "src/old.py"): [],
            ("src/greet.py",): ["src/farewell.py", "src/old.py"],
            ("src/gr", "src/old"): ["src/farewell.py", "src/greet.py", "src/old.py"],
            (".",): [],
        }
        for write_scope, outside in cases.items():
            with self.subTest(write_scope=write_scope):
                evidence = self.evidence(
                    self.delegate(run_id, write_scope=list(write_scope), scenario="write-done")
                )

                self.assertEqual(evidence["outside_write_scope"], outside)

    def test_records_the_write_scope_in_the_evidence(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(run_id, write_scope=["src/", "./README.md"], scenario="write-done")
        )

        self.assertEqual(evidence["write_scope"], ["src", "README.md"])


class SnapshotTest(WritingDelegationTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.repo / ".gitignore").write_text("build/\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "--quiet", "--message", "Ignore build output")
        # The user's work in progress: unstaged, staged then changed again, untracked and ignored.
        (self.repo / "README.md").write_text("# Demo\n\nWork in progress.\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "plan.md").write_text("Staged plan\n")
        git(self.repo, "add", "docs/plan.md")
        (self.repo / "docs" / "plan.md").write_text("Staged plan, edited since\n")
        (self.repo / "notes.txt").write_text("Untracked notes\n")
        (self.repo / "build").mkdir()
        (self.repo / "build" / "out.txt").write_text("Ignored output\n")

    def git_state(self) -> dict[str, Any]:
        """The user's index, HEAD, branches and stash, read without refreshing the index."""
        return {
            "index": (self.repo / ".git" / "index").read_bytes(),
            "head": git(self.repo, "symbolic-ref", "HEAD"),
            "refs": git(self.repo, "for-each-ref"),
            "stash": git(self.repo, "stash", "list"),
        }

    def test_the_delegate_starts_from_the_working_tree_with_uncommitted_and_untracked_files(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))

        seen = self.only_codex_call().files
        self.assertEqual(seen["README.md"], "# Demo\n\nWork in progress.\n")
        self.assertEqual(seen["docs/plan.md"], "Staged plan, edited since\n")
        self.assertEqual(seen["notes.txt"], "Untracked notes\n")
        self.assertNotIn("build/out.txt", seen)
        self.assertEqual(evidence["changed_paths"], ["src/farewell.py", "src/greet.py", "src/old.py"])

    def test_leaves_the_users_index_head_branches_and_working_tree_as_they_were(self) -> None:
        run_id, _ = self.start_run()
        files, state = self.files(), self.git_state()

        self.evidence(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))

        self.assertEqual(self.git_state(), state)
        self.assertEqual(self.files(), files)
        self.assertEqual(
            git(self.repo, "status", "--porcelain"), " M README.md\nAM docs/plan.md\n?? notes.txt\n"
        )


class CleanupTest(WritingDelegationTestCase):
    def test_removes_the_worktree_when_codex_returns_no_result(self) -> None:
        run_id, record = self.start_run()
        files = self.files()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-no-result")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("no Result", completed.stderr)
        self.assertFalse(Path(self.only_codex_call().cwd).exists())
        self.assertEqual(self.worktrees(), [])
        self.assertEqual(self.files(), files)
        self.assertEqual(len(list(record.rglob("changes.diff"))), 1, "the diff should still be kept")

    def test_removes_the_worktree_when_codex_cannot_be_run(self) -> None:
        run_id, _ = self.start_run()
        before = set(Path(tempfile.gettempdir()).glob(f"opus-orchestrator-{run_id}-*"))

        completed = self.delegate(run_id, write_scope=["src/"], codex=self.tmp / "no-codex-here")

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.worktrees(), [])
        self.assertEqual(set(Path(tempfile.gettempdir()).glob(f"opus-orchestrator-{run_id}-*")), before)

    def test_removes_the_worktree_when_the_wrapper_is_terminated(self) -> None:
        run_id, _ = self.start_run()
        wrapper = subprocess.Popen(
            [str(WRAPPER), *self.delegate_args(run_id, write_scope=["src/"])],
            cwd=self.repo,
            env=self.wrapper_env("write-hang"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(wrapper.kill)
        deadline = time.monotonic() + WRAPPER_TIMEOUT_SECONDS
        while not self.codex_calls() and time.monotonic() < deadline:
            time.sleep(0.05)
        worktree = Path(self.only_codex_call().cwd)

        wrapper.terminate()

        self.assertNotEqual(wrapper.wait(timeout=WRAPPER_TIMEOUT_SECONDS), 0)
        self.assertFalse(worktree.exists())
        self.assertEqual(self.worktrees(), [])
