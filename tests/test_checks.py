"""`delegate --check`: the wrapper reruns a writing Delegation's Checks itself."""

from __future__ import annotations

import json
from pathlib import Path

from support import WritingDelegationTestCase, stdout_field

# write-done claims done, with greet() ending in "!"; the task wanted a full stop.
FAILING_CHECK = "echo 'greet() still ends in !' >&2; grep -qF 'Hello, {name}.' src/greet.py"
PASSING_CHECK = "test -f src/farewell.py && ! test -e src/old.py"


class CheckRerunTest(WritingDelegationTestCase):
    def test_a_false_done_shows_its_checks_failing_when_rerun(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(
            run_id, write_scope=["src/"], scenario="write-done", checks=[PASSING_CHECK, FAILING_CHECK]
        )

        evidence = self.evidence(completed)
        result = json.loads(Path(stdout_field(completed.stdout, "Result")).read_text())
        self.assertEqual(result["status"], "done", "the Delegate's own claim is kept as it made it")
        self.assertIsNone(result["checks"])
        passed, failed = evidence["checks"]
        self.assertEqual(passed["command"], PASSING_CHECK)
        self.assertEqual(passed["exit_code"], 0)
        self.assertEqual(failed["command"], FAILING_CHECK)
        self.assertEqual(failed["exit_code"], 1)
        self.assertIn("greet() still ends in !", failed["output_tail"])
        self.assertEqual(stdout_field(completed.stdout, "Checks"), f"1 of 2 failed: {FAILING_CHECK}")

    def test_reruns_the_checks_in_the_delegates_worktree(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(run_id, write_scope=["src/"], scenario="write-done", checks=["pwd; ls src"])
        )

        [check] = evidence["checks"]
        self.assertEqual(check["output_tail"], f"{self.only_codex_call().cwd}\nfarewell.py\ngreet.py\n")

    def test_keeps_only_the_tail_of_a_long_output(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(run_id, write_scope=["src/"], scenario="write-done", checks=["seq 1000"])
        )

        tail = evidence["checks"][0]["output_tail"]
        self.assertTrue(tail.endswith("999\n1000\n"), tail)
        self.assertNotIn("\n1\n", f"\n{tail}")
        self.assertLess(len(tail), 1000)

    def test_check_side_effects_stay_out_of_the_diff(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(
                run_id, write_scope=["src/"], scenario="write-done", checks=["touch src/built.txt"]
            )
        )

        self.assertEqual(evidence["changed_paths"], ["src/farewell.py", "src/greet.py", "src/old.py"])

    def test_says_when_there_are_no_checks(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertEqual(self.evidence(completed)["checks"], [])
        self.assertEqual(stdout_field(completed.stdout, "Checks"), "none given")

    def test_says_when_every_check_passed(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(
            run_id, write_scope=["src/"], scenario="write-done", checks=[PASSING_CHECK, "true"]
        )

        self.assertEqual(stdout_field(completed.stdout, "Checks"), "2 passed")

    def test_refuses_checks_for_a_read_only_delegation_without_calling_codex(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, checks=["true"])

        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn("Check", completed.stderr)
        self.assertEqual(self.codex_calls(), [])
