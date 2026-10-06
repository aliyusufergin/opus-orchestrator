"""`start-run`: starting a Run creates its Run record."""

from __future__ import annotations

from support import WrapperTestCase, git, stdout_field


class StartRunTest(WrapperTestCase):
    def test_creates_an_untracked_run_record_inside_the_git_directory(self) -> None:
        completed = self.run_wrapper("start-run")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_id = stdout_field(completed.stdout, "Run id")
        record = stdout_field(completed.stdout, "Run record")
        self.assertTrue(record.startswith(f"{self.repo / '.git'}/"), record)
        self.assertTrue(record.endswith(run_id), record)
        self.assertEqual(git(self.repo, "status", "--porcelain", "--ignored"), "")

    def test_each_run_gets_its_own_id(self) -> None:
        first, _ = self.start_run()
        second, _ = self.start_run()

        self.assertNotEqual(first, second)

    def test_refuses_to_start_outside_a_git_repository(self) -> None:
        outside = self.tmp / "not-a-repo"
        outside.mkdir()

        completed = self.run_wrapper("start-run", cwd=outside)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not inside a Git repository", completed.stderr)
        self.assertEqual(list(outside.iterdir()), [])
