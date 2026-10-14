"""A Delegation whose wrapper is stopped from outside, as Claude Code stops a background command
when its Bash timeout runs out: what the Delegate did so far stays in the Run record."""

from __future__ import annotations

import json
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from support import (
    NEW_GREET,
    WRAPPER,
    WRAPPER_TIMEOUT_SECONDS,
    WritingDelegationTestCase,
    kill_quietly,
    stdout_field,
)


class StoppedDelegationTest(WritingDelegationTestCase):
    def stop_while_codex_runs(self, run_id: str, record: Path, signum: int) -> subprocess.CompletedProcess[str]:
        """Run a writing Delegation on the hanging fake Codex and stop the wrapper once Codex has
        made its edits and written its events."""
        args = self.delegate_args(run_id, write_scope=["src/"], checks=["exit 0"])
        wrapper = subprocess.Popen(
            [str(WRAPPER), *args],
            cwd=self.repo,
            env=self.wrapper_env("write-hang"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(kill_quietly, wrapper.pid)
        events = record / "delegations" / "d1" / "events.jsonl"
        deadline = time.monotonic() + WRAPPER_TIMEOUT_SECONDS
        while not (events.exists() and "thread.started" in events.read_text()):
            if time.monotonic() > deadline:
                self.fail("the fake Codex never wrote its events")
            time.sleep(0.05)

        wrapper.send_signal(signum)
        stdout, stderr = wrapper.communicate(timeout=WRAPPER_TIMEOUT_SECONDS)
        return subprocess.CompletedProcess(args, wrapper.returncode, stdout, stderr)

    def recorded(self, completed: subprocess.CompletedProcess[str]) -> tuple[dict[str, Any], dict[str, Any]]:
        """The Result and evidence a stopped Delegation left."""
        result_path = Path(stdout_field(completed.stdout, "Result"))
        return json.loads(result_path.read_text()), json.loads((result_path.parent / "evidence.json").read_text())

    def test_keeps_the_diff_and_records_the_delegation_as_stopped(self) -> None:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=signum.name):
                run_id, record = self.start_run()

                completed = self.stop_while_codex_runs(run_id, record, signum)

                self.assertEqual(completed.returncode, 128 + signum, completed.stderr)
                result, evidence = self.recorded(completed)
                self.assertEqual(evidence["failure_kind"], "stopped")
                self.assertIn(signum.name, evidence["failure"])
                self.assertEqual(result["status"], "partial")
                self.assertIsInstance(evidence["thread_id"], str)
                self.assertIn(NEW_GREET.splitlines()[1], Path(evidence["diff"]).read_text())
                # There may be no time left for Checks; the diff is what's kept.
                self.assertIsNone(evidence["check_reruns"])
                self.assertEqual(self.worktrees(), [])

    def test_a_stopped_delegation_can_be_resumed(self) -> None:
        run_id, record = self.start_run()
        self.stop_while_codex_runs(run_id, record, signal.SIGTERM)
        task = self.write_task("# Follow-up\nFinish what you started.\n")

        completed = self.run_wrapper(
            "delegate", "--run", run_id, "--resume", "d1", "--task", str(task), scenario="write-followup"
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.evidence(completed)["resumes"], "d1")
