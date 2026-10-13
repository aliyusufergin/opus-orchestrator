"""When a Delegation ends, nothing it started keeps running.

On Linux, Codex runs each command in a session (and PID namespace) of its own, out of Codex's
process group; the fake Codex's detached `sleep` stands in for such a command.
"""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from support import (
    WRAPPER,
    WRAPPER_TIMEOUT_SECONDS,
    WritingDelegationTestCase,
    kill_quietly,
    process_exists,
)

# Far longer than any test, so the `sleep` is gone only if the wrapper ended it.
DETACHED_SECONDS = "300"
# Long enough for the fake Codex to start, far shorter than its hang.
SHORT_TIMEOUT = "0.02"

# A Check that leaves a `sleep` running in a session of its own and prints its pid.
DETACHING_CHECK = (
    f"{sys.executable} -c \"import subprocess; print(subprocess.Popen(['sleep', '{DETACHED_SECONDS}'],"
    " stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,"
    ' start_new_session=True).pid)"'
)


class ProcessCleanupTest(WritingDelegationTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.fake_codex_env["FAKE_CODEX_DETACH"] = DETACHED_SECONDS

    def detached_pid(self) -> int:
        return self.leftover(self.only_codex_call().detached_pid)

    def leftover(self, pid: int | None) -> int:
        """`pid`, which the test ends all the same should the wrapper miss it."""
        assert pid is not None
        self.addCleanup(kill_quietly, pid)
        return pid

    def test_ends_a_detached_command_when_codex_times_out(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(
            run_id, write_scope=["src/"], scenario="write-hang", timeout=SHORT_TIMEOUT
        )

        self.assertEqual(self.evidence(completed)["failure_kind"], "timeout")
        pid = self.detached_pid()
        self.assertFalse(process_exists(pid), f"detached command {pid} is still running")

    def test_ends_a_detached_command_when_codex_exits_cleanly(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertIsNone(self.evidence(completed)["failure_kind"])
        pid = self.detached_pid()
        self.assertFalse(process_exists(pid), f"detached command {pid} is still running")

    def test_ends_a_detached_command_of_a_read_only_delegation(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, scenario="read-only-done")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        pid = self.detached_pid()
        self.assertFalse(process_exists(pid), f"detached command {pid} is still running")

    def test_ends_a_detached_command_when_the_wrapper_is_stopped(self) -> None:
        run_id, _ = self.start_run()

        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=signum.name):
                calls = len(self.codex_calls()) + 1
                pid = self.stop_wrapper(
                    self.delegate_args(run_id, write_scope=["src/"]),
                    "write-hang",
                    signum,
                    lambda: self.started_codex(calls),
                )

                self.assertFalse(process_exists(pid), f"detached command {pid} is still running")

    def test_ends_a_detached_process_of_a_check_when_the_wrapper_is_stopped(self) -> None:
        del self.fake_codex_env["FAKE_CODEX_DETACH"]
        run_id, record = self.start_run()

        pid = self.stop_wrapper(
            self.delegate_args(
                run_id, write_scope=["src/"], checks=[f"{DETACHING_CHECK}; sleep 60"]
            ),
            "write-done",
            signal.SIGTERM,
            lambda: started_check(record / "delegations" / "d1" / "check-1.log"),
        )

        self.assertFalse(process_exists(pid), f"the Check's process {pid} is still running")

    def test_ends_a_detached_process_a_check_leaves(self) -> None:
        del self.fake_codex_env["FAKE_CODEX_DETACH"]
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(
                run_id, write_scope=["src/"], scenario="write-done", checks=[DETACHING_CHECK]
            )
        )

        [check] = evidence["check_reruns"]
        self.assertEqual(check["exit_code"], 0, check["output_tail"])
        pid = self.leftover(int(check["output_tail"]))
        self.assertFalse(process_exists(pid), f"the Check's process {pid} is still running")

    def test_ends_a_detached_process_of_a_check_that_times_out(self) -> None:
        del self.fake_codex_env["FAKE_CODEX_DETACH"]
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(
                run_id,
                write_scope=["src/"],
                scenario="write-done",
                timeout=SHORT_TIMEOUT,
                checks=[f"{DETACHING_CHECK}; sleep 60"],
            )
        )

        [check] = evidence["check_reruns"]
        self.assertIsNone(check["exit_code"])
        pid = self.leftover(int(check["output_tail"]))
        self.assertFalse(process_exists(pid), f"the Check's process {pid} is still running")

    def stop_wrapper(
        self, args: list[str], scenario: str, signum: int, started: Callable[[], int | None]
    ) -> int:
        """Stop the wrapper with `signum` once `started` gives the pid of a process it left running."""
        wrapper = subprocess.Popen(
            [str(WRAPPER), *args],
            cwd=self.repo,
            env=self.wrapper_env(scenario),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(kill_quietly, wrapper.pid)
        deadline = time.monotonic() + WRAPPER_TIMEOUT_SECONDS
        while (pid := started()) is None:
            if time.monotonic() > deadline:
                self.fail("the process to leave running never started")
            time.sleep(0.05)
        self.leftover(pid)

        wrapper.send_signal(signum)
        _, stderr = wrapper.communicate(timeout=WRAPPER_TIMEOUT_SECONDS)

        self.assertEqual(wrapper.returncode, 128 + signum, stderr)
        return pid

    def started_codex(self, calls: int) -> int | None:
        """The detached `sleep` of the fake Codex's `calls`th invocation, once it has started."""
        started = self.codex_calls()
        return started[calls - 1].detached_pid if len(started) >= calls else None


def started_check(log: Path) -> int | None:
    """The pid DETACHING_CHECK printed to its log, once it has."""
    try:
        line = log.read_text().strip()
    except FileNotFoundError:
        return None
    return int(line) if line else None
