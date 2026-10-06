"""`report`: one line per Delegation of a Run, for the Orchestrator's final report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from support import WrapperTestCase, stdout_field

TASK_PART = "# Goal\nFind where greet() is called.\n"

# Token usage in the fake Codex scenarios.
DONE_TOKENS = ("24587 input", "18944 cached", "130 output", "0 reasoning")
BLOCKED_TOKENS = ("13661 input", "0 cached", "19 output", "0 reasoning")


class ReportTestCase(WrapperTestCase):
    def delegate(
        self, run_id: str, model: str, effort: str, scenario: str = "read-only-done"
    ) -> subprocess.CompletedProcess[str]:
        return self.run_wrapper(
            "delegate",
            "--run", run_id,
            "--task", str(self.write_task(TASK_PART)),
            "--model", model,
            "--effort", effort,
            "--write-scope", "none",
            scenario=scenario,
        )

    def delegation(self, run_id: str, model: str, effort: str, scenario: str = "read-only-done") -> str:
        """Run a Delegation that returns a Result, and return its id."""
        completed = self.delegate(run_id, model, effort, scenario)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return stdout_field(completed.stdout, "Delegation")

    def report(self, run_id: str) -> subprocess.CompletedProcess[str]:
        return self.run_wrapper("report", "--run", run_id)

    def report_stdout(self, run_id: str) -> str:
        completed = self.report(run_id)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout


def delegation_line(stdout: str, delegation_id: str) -> str:
    lines = [line for line in stdout.splitlines() if line.split()[:1] == [delegation_id]]
    if len(lines) != 1:
        raise AssertionError(f"expected one line for {delegation_id} in report:\n{stdout}")
    return lines[0]


def model_total_line(stdout: str, model: str) -> str:
    lines = [line for line in stdout.splitlines() if line.strip().startswith(f"{model}:")]
    if len(lines) != 1:
        raise AssertionError(f"expected one total for {model} in report:\n{stdout}")
    return lines[0]


class RunReportTest(ReportTestCase):
    def test_lists_each_delegation_with_model_effort_status_tokens_and_times(self) -> None:
        run_id, _ = self.start_run()
        sol = self.delegation(run_id, "gpt-6.1-sol", "medium")
        luna = self.delegation(run_id, "gpt-6-luna", "high", scenario="read-only-blocked")
        astra = self.delegation(run_id, "gpt-6-astra", "high")

        stdout = self.report_stdout(run_id)

        for delegation_id, model, effort, status, tokens in [
            (sol, "gpt-6.1-sol", "medium", "done", DONE_TOKENS),
            (luna, "gpt-6-luna", "high", "blocked", BLOCKED_TOKENS),
            (astra, "gpt-6-astra", "high", "done", DONE_TOKENS),
        ]:
            line = delegation_line(stdout, delegation_id)
            self.assertIn(model, line)
            self.assertIn(effort, line)
            self.assertIn(status, line)
            for count in tokens:
                self.assertIn(count, line)
            self.assertIn("waited not recorded", line)
            self.assertRegex(line, r"ran \d+\.\d s")

    def test_lists_delegations_in_the_order_they_were_started(self) -> None:
        run_id, _ = self.start_run()
        ids = [self.delegation(run_id, "gpt-6.1-sol", "medium") for _ in range(11)]

        stdout = self.report_stdout(run_id)

        listed = [line.split()[0] for line in stdout.splitlines() if line.split()[0] in ids]
        self.assertEqual(listed, ids)

    def test_marks_astra_delegations(self) -> None:
        run_id, _ = self.start_run()
        sol = self.delegation(run_id, "gpt-6.1-sol", "medium")
        astra = self.delegation(run_id, "gpt-6-astra", "high")

        stdout = self.report_stdout(run_id)

        self.assertIn("ASTRA", delegation_line(stdout, astra))
        self.assertNotIn("ASTRA", delegation_line(stdout, sol))

    def test_totals_tokens_per_model(self) -> None:
        run_id, _ = self.start_run()
        self.delegation(run_id, "gpt-6.1-sol", "medium")
        self.delegation(run_id, "gpt-6.1-sol", "high", scenario="read-only-blocked")
        self.delegation(run_id, "gpt-6-astra", "high")

        stdout = self.report_stdout(run_id)

        sol_total = model_total_line(stdout, "gpt-6.1-sol")
        for count in ("38248 input", "18944 cached", "149 output", "0 reasoning", "2 Delegations"):
            self.assertIn(count, sol_total)
        astra_total = model_total_line(stdout, "gpt-6-astra")
        for count in (*DONE_TOKENS, "1 Delegation"):
            self.assertIn(count, astra_total)
        self.assertIn("ASTRA", astra_total)

    def test_shows_the_failure_kind_and_waiting_time_the_evidence_records(self) -> None:
        run_id, record = self.start_run()
        delegation_id = self.delegation(run_id, "gpt-6.1-sol", "medium")
        evidence_path = record / "delegations" / delegation_id / "evidence.json"
        evidence = json.loads(evidence_path.read_text())
        evidence.update(failure_kind="timeout", wait_seconds=42.3)
        evidence_path.write_text(json.dumps(evidence))

        line = delegation_line(self.report_stdout(run_id), delegation_id)

        self.assertIn("timeout", line)
        self.assertIn("waited 42.3 s", line)

    def test_shows_a_delegation_that_left_no_evidence(self) -> None:
        run_id, record = self.start_run()
        self.assertNotEqual(self.delegate(run_id, "gpt-6.1-sol", "medium", "no-result").returncode, 0)
        [delegation_dir] = (record / "delegations").iterdir()

        line = delegation_line(self.report_stdout(run_id), delegation_dir.name)

        self.assertIn("no evidence", line)

    def test_reports_a_run_without_delegations(self) -> None:
        run_id, _ = self.start_run()

        stdout = self.report_stdout(run_id)

        self.assertIn("no Delegations", stdout)

    def test_refuses_an_unknown_run(self) -> None:
        self.start_run()

        completed = self.report("no-such-run")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("no-such-run", completed.stderr)
