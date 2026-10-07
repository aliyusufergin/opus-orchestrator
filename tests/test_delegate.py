"""`delegate` with Write scope `none`: a read-only Delegation through Codex."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from support import PLUGIN_ROOT, SCENARIOS, TASK_PART, WrapperTestCase, stdout_field


class ReadOnlyDelegationTest(WrapperTestCase):
    def test_runs_codex_exec_pinned_in_a_minimal_read_only_environment(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        call = self.only_codex_call()
        self.assertEqual(call.subcommand, "exec")
        self.assertEqual(call.option("--model"), "gpt-6-luna")
        self.assertEqual(call.config["model_reasoning_effort"], "medium")
        self.assertIn("--ignore-user-config", call.flags)
        self.assertIs(call.config["features.apps"], False)
        self.assertIs(call.config["agents.enabled"], False)
        self.assertEqual(call.option("--sandbox"), "read-only")
        self.assertEqual(call.config["web_search"], "disabled")
        self.assertIn("--json", call.flags)
        self.assertNotIn("--ephemeral", call.flags)
        self.assertEqual(call.option("--cd"), str(self.repo))
        self.assertEqual(call.cwd, str(self.repo))

    def test_asks_codex_for_a_result_in_the_result_schema_written_to_a_file(self) -> None:
        run_id, _ = self.start_run()

        self.delegate(run_id)

        call = self.only_codex_call()
        schema_path = call.option("--output-schema")
        assert schema_path is not None
        self.assertEqual(
            json.loads(Path(schema_path).read_text()),
            json.loads((PLUGIN_ROOT / "schemas" / "result.schema.json").read_text()),
        )
        self.assertIsNotNone(call.option("--output-last-message"))

    def test_closes_codex_stdin_even_when_its_own_stdin_stays_open(self) -> None:
        run_id, _ = self.start_run()
        read_end, write_end = os.pipe()
        self.addCleanup(os.close, write_end)
        self.addCleanup(os.close, read_end)

        completed = self.delegate(run_id, stdin=read_end)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(self.codex_calls()), 1)

    def test_sends_the_fixed_part_before_the_task_part_and_keeps_the_contract(self) -> None:
        run_id, record = self.start_run()

        self.delegate(run_id)

        contract = self.only_codex_call().stdin
        assert contract is not None
        fixed_part = (PLUGIN_ROOT / "contract" / "fixed-part.md").read_text().strip()
        self.assertTrue(contract.startswith(fixed_part), contract)
        self.assertTrue(contract.endswith(TASK_PART), contract)
        stored = [p for p in record.rglob("*") if p.is_file() and p.read_text() == contract]
        self.assertEqual(len(stored), 1, "the full Contract should be in the Run record")

    def test_fixed_part_covers_the_rules_every_delegate_works_under(self) -> None:
        run_id, _ = self.start_run()

        self.delegate(run_id)

        contract = self.only_codex_call().stdin
        assert contract is not None
        for rule in ["blocked", "assumption", "commit", "Write scope", "AGENTS.md", "Result", "preamble"]:
            self.assertIn(rule, contract)

    def test_writes_the_result_with_wrapper_evidence_alongside(self) -> None:
        run_id, record = self.start_run()

        completed = self.delegate(run_id)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result_path = Path(stdout_field(completed.stdout, "Result"))
        self.assertTrue(result_path.is_relative_to(record), result_path)
        result = json.loads(result_path.read_text())
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["summary"], 'The greet() call site is src/main.py:3 (`print(greet("world"))`).')
        self.assertEqual(result["checks"], [{"command": r"rg -n '\bgreet\s*\(' .", "exit_code": 0}])

        evidence = json.loads((result_path.parent / "evidence.json").read_text())
        self.assertEqual(evidence["delegation_id"], stdout_field(completed.stdout, "Delegation"))
        self.assertEqual(evidence["model"], "gpt-6-luna")
        self.assertEqual(evidence["effort"], "medium")
        self.assertEqual(evidence["thread_id"], "01a1159d-26a8-7c41-be41-af6ec376cc46")
        self.assertEqual(
            evidence["usage"],
            {
                "input_tokens": 19736,
                "cached_input_tokens": 8960,
                "output_tokens": 178,
                "reasoning_output_tokens": 0,
            },
        )
        started = datetime.fromisoformat(evidence["started_at"])
        ended = datetime.fromisoformat(evidence["ended_at"])
        self.assertLessEqual(started, ended)
        self.assertGreaterEqual(evidence["duration_seconds"], 0)

    def test_prints_a_compact_summary(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id)

        self.assertEqual(stdout_field(completed.stdout, "Status"), "done")
        self.assertIn("gpt-6-luna", stdout_field(completed.stdout, "Model"))
        self.assertIn("medium", stdout_field(completed.stdout, "Model"))
        tokens = stdout_field(completed.stdout, "Tokens")
        for count in ["19736", "8960", "178"]:
            self.assertIn(count, tokens)
        self.assertEqual(
            stdout_field(completed.stdout, "Summary"),
            'The greet() call site is src/main.py:3 (`print(greet("world"))`).',
        )
        self.assertLessEqual(len(completed.stdout.splitlines()), 10)

    def test_keeps_the_codex_events_in_the_run_record(self) -> None:
        run_id, record = self.start_run()

        self.delegate(run_id)

        events = (SCENARIOS / "read-only-done" / "events.jsonl").read_text()
        stored = [p for p in record.rglob("*") if p.is_file() and p.read_text() == events]
        self.assertEqual(len(stored), 1, "the JSONL events should be in the Run record")


class DelegateExitCodeTest(WrapperTestCase):
    def test_exits_zero_for_a_blocked_result(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, scenario="read-only-blocked")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(stdout_field(completed.stdout, "Status"), "blocked")
        result = json.loads(Path(stdout_field(completed.stdout, "Result")).read_text())
        self.assertEqual(result["open_questions"], ["What should greet() be renamed to?"])

    def test_refuses_an_unknown_run_without_calling_codex(self) -> None:
        self.start_run()

        completed = self.delegate("no-such-run")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("no-such-run", completed.stderr)
        self.assertEqual(self.codex_calls(), [])

    def test_refuses_a_run_id_that_points_outside_the_run_records(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(f"../runs/{run_id}")

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.codex_calls(), [])

    def test_refuses_a_missing_task_part_without_calling_codex(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, task=self.tmp / "missing.md")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("task part", completed.stderr)
        self.assertEqual(self.codex_calls(), [])

    def test_refuses_a_write_scope_that_isnt_inside_the_repository_without_calling_codex(self) -> None:
        run_id, _ = self.start_run()

        for write_scope in (["../elsewhere"], [str(self.repo / "src")], ["none", "src/"], [""]):
            with self.subTest(write_scope=write_scope):
                completed = self.delegate(run_id, write_scope=write_scope)

                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn("Write scope", completed.stderr)
        self.assertEqual(self.codex_calls(), [])

    def test_fails_when_codex_cannot_be_run(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, codex=self.tmp / "no-codex-here")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("OPUS_ORCHESTRATOR_CODEX", completed.stderr)
