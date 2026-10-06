"""`apply`: a writing Delegation's diff applied to the main working tree with a three-way apply."""

from __future__ import annotations

import subprocess

from support import FAREWELL, GREET, NEW_GREET, WritingDelegationTestCase, git, stdout_field

# The user's own change to src/greet.py, not staged, made before the Delegation started.
COMMENTED_GREET = f"# Greets people.\n{GREET}"


class ApplyTest(WritingDelegationTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.repo / "src" / "greet.py").write_text(COMMENTED_GREET)

    def delegation(self, scenario: str = "write-done") -> tuple[str, str]:
        """Run a writing Delegation with Write scope src/ and return the Run and Delegation ids."""
        run_id, _ = self.start_run()
        completed = self.delegate(run_id, write_scope=["src/"], scenario=scenario)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return run_id, stdout_field(completed.stdout, "Delegation")

    def apply(self, run_id: str, delegation_id: str) -> subprocess.CompletedProcess[str]:
        return self.run_wrapper("apply", "--run", run_id, "--delegation", delegation_id)

    def test_applies_cleanly_to_an_unchanged_working_tree_without_touching_the_index(self) -> None:
        run_id, delegation_id = self.delegation()
        index = (self.repo / ".git" / "index").read_bytes()

        completed = self.apply(run_id, delegation_id)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(stdout_field(completed.stdout, "Conflicts"), "none")
        self.assertEqual(
            self.files(),
            {"README.md": "# Demo\n", "src/farewell.py": FAREWELL, "src/greet.py": NEW_GREET},
        )
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index)
        self.assertEqual(
            git(self.repo, "status", "--porcelain"), " M src/greet.py\n D src/old.py\n?? src/farewell.py\n"
        )

    def test_reports_conflicts_where_the_working_tree_changed_in_the_same_place(self) -> None:
        run_id, delegation_id = self.delegation()
        (self.repo / "src" / "greet.py").write_text(COMMENTED_GREET.replace("Hello", "Hi"))

        completed = self.apply(run_id, delegation_id)

        self.assertEqual(completed.returncode, 3, completed.stderr)
        self.assertEqual(stdout_field(completed.stdout, "Conflicts"), "src/greet.py")
        greet = (self.repo / "src" / "greet.py").read_text()
        for marker in ("<<<<<<<", "=======", ">>>>>>>"):
            self.assertIn(marker, greet)
        self.assertIn('return f"Hi, {name}"', greet)
        self.assertIn('return f"Hello, {name}!"', greet)
        self.assertEqual((self.repo / "src" / "farewell.py").read_text(), FAREWELL)
        self.assertFalse((self.repo / "src" / "old.py").exists())

    def test_changes_nothing_when_the_diff_does_not_apply(self) -> None:
        run_id, delegation_id = self.delegation()
        (self.repo / "src" / "old.py").unlink()  # The diff deletes it too.
        files = self.files()

        completed = self.apply(run_id, delegation_id)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("src/old.py", completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(self.files(), files)

    def test_refuses_a_delegation_without_a_diff(self) -> None:
        run_id, _ = self.start_run()
        completed = self.delegate(run_id)
        read_only = stdout_field(completed.stdout, "Delegation")

        for delegation_id in (read_only, "d9", "../d1", ""):
            with self.subTest(delegation_id=delegation_id):
                completed = self.apply(run_id, delegation_id)

                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn("diff", completed.stderr)

    def test_applies_to_the_whole_repository_from_a_subdirectory(self) -> None:
        run_id, delegation_id = self.delegation("write-outside-scope")

        completed = self.run_wrapper(
            "apply", "--run", run_id, "--delegation", delegation_id, cwd=self.repo / "src"
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.files()["README.md"], "# Demo\n\nCall greet() to greet someone.\n")
        self.assertEqual(self.files()["src/greet.py"], NEW_GREET)
