"""At most three Delegations run at once on the machine; a fourth waits for a slot."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from support import WRAPPER, WRAPPER_TIMEOUT_SECONDS, CodexCall, WritingDelegationTestCase, git, stdout_field

# How long the test waits for the wrappers it started in the background to reach Codex.
START_DEADLINE_SECONDS = 10
# Above it, a Delegation waited for a slot; the slow scenario holds one for two seconds.
WAITED_SECONDS = 0.5


class ConcurrencyTestCase(WritingDelegationTestCase):
    def start_delegations(self, count: int, scenario: str) -> list[subprocess.Popen[str]]:
        """Start `count` Delegations in the background and wait until each has started Codex."""
        run_id, _ = self.start_run()
        wrappers = []
        for _ in range(count):
            wrapper = subprocess.Popen(
                [str(WRAPPER), *self.delegate_args(run_id)],
                cwd=self.repo,
                env=self.wrapper_env(scenario),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(end_wrapper, wrapper)
            wrappers.append(wrapper)
        deadline = time.monotonic() + START_DEADLINE_SECONDS
        while len(self.codex_calls()) < count:
            self.assertLess(time.monotonic(), deadline, "the Delegations didn't all start Codex")
            time.sleep(0.05)
        return wrappers

    def end_codex_left_behind(self) -> None:
        """Kill the fake Codex processes that killed wrappers left running."""
        for call in self.codex_calls():
            if call.pid is not None and call.ended_at is None:
                try:
                    os.kill(call.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def start_run_in(self, repo: Path) -> str:
        completed = self.run_wrapper("start-run", cwd=repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return stdout_field(completed.stdout, "Run id")


def end_wrapper(wrapper: subprocess.Popen[str]) -> None:
    if wrapper.poll() is None:
        wrapper.kill()
    wrapper.communicate()


class DelegationSlotTest(ConcurrencyTestCase):
    def test_a_fourth_delegation_starts_only_after_one_ends(self) -> None:
        holders = self.start_delegations(3, "read-only-slow")
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id))

        *held, fourth = sorted(self.codex_calls(), key=start_time)
        self.assertGreaterEqual(start_time(fourth), min(call.ended_at or float("inf") for call in held))
        self.assertIsInstance(evidence["wait_seconds"], float)
        self.assertGreater(evidence["wait_seconds"], WAITED_SECONDS)
        for holder in holders:
            stdout, stderr = holder.communicate(timeout=WRAPPER_TIMEOUT_SECONDS)
            self.assertEqual(holder.returncode, 0, stderr)
            self.assertLess(json.loads(evidence_path(stdout).read_text())["wait_seconds"], WAITED_SECONDS)

    def test_slots_are_shared_across_repositories(self) -> None:
        self.start_delegations(3, "read-only-slow")
        other = self.tmp / "other"
        other.mkdir()
        git(other, "init", "--quiet")
        run_id = self.start_run_in(other)

        completed = self.run_wrapper(*self.delegate_args(run_id), cwd=other)

        self.assertGreater(self.evidence(completed)["wait_seconds"], WAITED_SECONDS)

    def test_the_timeout_counts_from_when_codex_starts(self) -> None:
        self.start_delegations(3, "read-only-slow")
        run_id, _ = self.start_run()

        # 0.6 s: shorter than the wait for a slot, longer than the fake Codex takes.
        evidence = self.evidence(self.delegate(run_id, timeout="0.01"))

        self.assertGreater(evidence["wait_seconds"], 0.6)
        self.assertIsNone(evidence["failure_kind"])

    def test_a_killed_wrapper_does_not_leak_its_slot(self) -> None:
        wrappers = self.start_delegations(3, "read-only-slow")
        self.addCleanup(self.end_codex_left_behind)
        for wrapper in wrappers:
            wrapper.kill()
            wrapper.wait()
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id))

        self.assertLess(evidence["wait_seconds"], WAITED_SECONDS)


def start_time(call: CodexCall) -> float:
    assert call.started_at is not None
    return call.started_at


def evidence_path(stdout: str) -> Path:
    return Path(stdout_field(stdout, "Result")).parent / "evidence.json"
