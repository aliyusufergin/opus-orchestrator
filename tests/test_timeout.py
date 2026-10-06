"""`delegate --timeout`: a Delegation that runs too long is stopped."""

from __future__ import annotations

import json
import os
from pathlib import Path

from support import WritingDelegationTestCase, stdout_field


class TimeoutLimitTest(WritingDelegationTestCase):
    def test_refuses_a_timeout_above_60_minutes_without_calling_codex(self) -> None:
        run_id, _ = self.start_run()

        for timeout in ("61", "60.5"):
            with self.subTest(timeout=timeout):
                completed = self.delegate(run_id, timeout=timeout)

                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn("60", completed.stderr)
        self.assertEqual(self.codex_calls(), [])


# Long enough for the fake Codex to start and make its edits, far shorter than its hang.
SHORT_TIMEOUT = "0.02"


class TimeoutTest(WritingDelegationTestCase):
    def test_a_hang_times_out_to_partial_with_its_diff(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(
            run_id, write_scope=["src/"], scenario="write-hang", timeout=SHORT_TIMEOUT
        )

        evidence = self.evidence(completed)
        self.assertEqual(stdout_field(completed.stdout, "Status"), "partial")
        result = json.loads(Path(stdout_field(completed.stdout, "Result")).read_text())
        self.assertEqual(result["status"], "partial")
        self.assertEqual(evidence["failure_kind"], "timeout")
        self.assertEqual(evidence["timeout_minutes"], 0.02)
        self.assertEqual(evidence["changed_paths"], ["src/farewell.py", "src/greet.py", "src/old.py"])
        self.assertLess(evidence["duration_seconds"], 20)
        self.assertEqual(self.worktrees(), [])

    def test_reruns_the_checks_after_a_timeout(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(
                run_id,
                write_scope=["src/"],
                scenario="write-hang",
                timeout=SHORT_TIMEOUT,
                checks=["test -f src/farewell.py"],
            )
        )

        [check] = evidence["checks"]
        self.assertEqual(check["exit_code"], 0)

    def test_a_check_that_runs_past_the_timeout_is_stopped(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(
            run_id, write_scope=["src/"], scenario="write-done", timeout=SHORT_TIMEOUT, checks=["sleep 60"]
        )

        [check] = self.evidence(completed)["checks"]
        self.assertIsNone(check["exit_code"])
        self.assertEqual(stdout_field(completed.stdout, "Checks"), "1 of 1 failed: sleep 60")

    def test_ends_the_codex_process_on_timeout(self) -> None:
        run_id, _ = self.start_run()

        self.delegate(run_id, write_scope=["src/"], scenario="write-hang", timeout=SHORT_TIMEOUT)

        pid = int(next(self.codex_records.glob("*.json")).stem)
        self.assertFalse(process_exists(pid), f"fake Codex {pid} is still running")


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
