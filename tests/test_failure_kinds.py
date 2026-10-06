"""The failure kind in the evidence: why a Delegation went wrong, so the Orchestrator can act on it."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from support import SCENARIOS, WrapperTestCase, stdout_field

ERROR_MESSAGES = json.loads((SCENARIOS / "error-messages.json").read_text())["messages"]
DONE = SCENARIOS / "read-only-done"
OPENING_EVENTS = [
    {"type": "thread.started", "thread_id": "01a10d01-d5f0-7533-9bf3-f9a88af1f92d"},
    {"type": "turn.started"},
]


class FailureKindTestCase(WrapperTestCase):
    def scenario(
        self,
        name: str,
        *,
        events: list[dict[str, Any]] | None = None,
        last_message: str | None = None,
        exit_code: int = 0,
    ) -> Path:
        """A fake Codex scenario: the recorded `read-only-done` events unless given."""
        directory = self.tmp / "scenarios" / name
        directory.mkdir(parents=True)
        events_text = (
            (DONE / "events.jsonl").read_text()
            if events is None
            else "".join(json.dumps(event) + "\n" for event in events)
        )
        (directory / "events.jsonl").write_text(events_text)
        if last_message is not None:
            (directory / "last-message.json").write_text(last_message)
        (directory / "exit-code").write_text(str(exit_code))
        return directory

    def failed_delegation(
        self, scenario: Path
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], dict[str, Any]]:
        """Run a Delegation and return its output, Result and evidence."""
        run_id, _ = self.start_run()
        completed = self.delegate(run_id, scenario=str(scenario))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result_path = Path(stdout_field(completed.stdout, "Result"))
        result = json.loads(result_path.read_text())
        evidence = json.loads((result_path.parent / "evidence.json").read_text())
        return completed, result, evidence


class NoFailureTest(FailureKindTestCase):
    def test_a_delegation_that_went_well_has_no_failure_kind(self) -> None:
        _, result, evidence = self.failed_delegation(DONE)

        self.assertEqual(result["status"], "done")
        self.assertIsNone(evidence["failure_kind"])


class CodexErrorTest(FailureKindTestCase):
    def test_codex_failing_for_another_reason_is_a_codex_error(self) -> None:
        completed, result, evidence = self.failed_delegation(SCENARIOS / "no-result")

        self.assertEqual(evidence["failure_kind"], "codex_error")
        self.assertIn("stream disconnected before completion", evidence["failure"])
        self.assertEqual(result["status"], "blocked")
        self.assertIn("codex_error", stdout_field(completed.stdout, "Failure"))


class RecognisedCodexErrorTest(FailureKindTestCase):
    def test_recognises_quota_and_sign_in_failures_from_codexs_error_events(self) -> None:
        for number, entry in enumerate(ERROR_MESSAGES):
            with self.subTest(source=entry["source"]):
                scenario = self.scenario(
                    f"error-{number}",
                    events=[
                        *OPENING_EVENTS,
                        {"type": "error", "message": entry["message"]},
                        {"type": "turn.failed", "error": {"message": entry["message"]}},
                    ],
                    exit_code=1,
                )

                _, result, evidence = self.failed_delegation(scenario)

                self.assertEqual(evidence["failure_kind"], entry["kind"])
                self.assertEqual(evidence["failure"], entry["message"])
                self.assertEqual(result["status"], "blocked")

    def test_recognises_a_failure_reported_only_in_an_error_event(self) -> None:
        quota = next(entry["message"] for entry in ERROR_MESSAGES if entry["kind"] == "quota_exhausted")
        scenario = self.scenario(
            "error-event-only",
            events=[*OPENING_EVENTS, {"type": "error", "message": quota}],
            exit_code=1,
        )

        _, _, evidence = self.failed_delegation(scenario)

        self.assertEqual(evidence["failure_kind"], "quota_exhausted")


class InvalidResultTest(FailureKindTestCase):
    def test_a_missing_empty_or_schema_violating_result_is_an_invalid_result(self) -> None:
        done = json.loads((DONE / "last-message.json").read_text())
        cases = {
            "missing": None,
            "empty": "",
            "not-json": "All done!",
            "not-an-object": json.dumps(["done"]),
            "unknown-status": json.dumps({**done, "status": "finished"}),
            "missing-field": json.dumps({k: v for k, v in done.items() if k != "findings"}),
            "extra-field": json.dumps({**done, "confidence": "high"}),
            "wrong-item-type": json.dumps({**done, "changed_files": ["a.py", 3]}),
            "bad-check": json.dumps({**done, "checks": [{"command": "pytest", "exit_code": "0"}]}),
        }
        for name, last_message in cases.items():
            with self.subTest(result=name):
                completed, result, evidence = self.failed_delegation(
                    self.scenario(name, last_message=last_message)
                )

                self.assertEqual(evidence["failure_kind"], "invalid_result")
                self.assertNotEqual(result["status"], "done")
                self.assertEqual(stdout_field(completed.stdout, "Status"), result["status"])

    def test_keeps_the_delegates_own_message_in_the_run_record(self) -> None:
        message = json.dumps({"status": "finished"})

        completed, _, _ = self.failed_delegation(self.scenario("kept", last_message=message))

        kept = Path(stdout_field(completed.stdout, "Result")).parent / "last-message.txt"
        self.assertEqual(kept.read_text(), message)
