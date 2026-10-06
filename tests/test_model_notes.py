"""Model notes and routing guardrails: `start-run` compares the dated Model notes
with Codex's live catalog, and `delegate` refuses `ultra` and unknown models."""

from __future__ import annotations

from datetime import date, timedelta
import subprocess
from pathlib import Path

from support import FAKE_CODEX, PLUGIN_ROOT, WrapperTestCase, stdout_field

# The listed (not hidden) models in the recorded catalog.
LISTED_MODELS = (
    "gpt-6.1-sol",
    "gpt-6-astra",
    "gpt-6-sol",
    "gpt-6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)


class ModelNotesTestCase(WrapperTestCase):
    def write_model_notes(self, dated: date | str, models: tuple[str, ...] = LISTED_MODELS) -> Path:
        rows = "\n".join(f"| `{model}` | medium | – |" for model in models)
        notes = self.tmp / "model-notes.md"
        notes.write_text(
            f"---\ndate: {dated}\n---\n\n# Model notes\n\n"
            f"| Model | Default effort | Use for |\n|---|---|---|\n{rows}\n"
            "| All models | – | `ultra` never |\n"
        )
        return notes

    def warnings(self, stdout: str) -> list[str]:
        return [line for line in stdout.splitlines() if line.startswith("Warning:")]


class StartRunCatalogTest(ModelNotesTestCase):
    def test_shows_the_listed_models_and_where_the_notes_are(self) -> None:
        notes = self.write_model_notes(date.today())

        completed = self.run_wrapper("start-run", model_notes=notes)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(stdout_field(completed.stdout, "Models").split(", "), list(LISTED_MODELS))
        self.assertIn(str(notes), stdout_field(completed.stdout, "Model notes"))
        self.assertIn(str(date.today()), stdout_field(completed.stdout, "Model notes"))
        self.assertEqual(self.warnings(completed.stdout), [])

    def test_hidden_catalog_models_need_no_notes(self) -> None:
        notes = self.write_model_notes(date.today())

        completed = self.run_wrapper("start-run", model_notes=notes)

        self.assertNotIn("gpt-reserve", completed.stdout)
        self.assertNotIn("codex-auto-review", completed.stdout)

    def test_warns_without_failing_when_the_catalog_lists_a_model_the_notes_dont_cover(self) -> None:
        notes = self.write_model_notes(date.today())

        completed = self.run_wrapper("start-run", catalog="uncovered", model_notes=notes)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        stdout_field(completed.stdout, "Run id")
        warnings = self.warnings(completed.stdout)
        self.assertEqual(len(warnings), 1, completed.stdout)
        self.assertIn("gpt-7-nova", warnings[0])
        self.assertIn("gpt-7-nova", stdout_field(completed.stdout, "Models"))

    def test_warns_without_failing_when_the_notes_are_more_than_30_days_old(self) -> None:
        dated = date.today() - timedelta(days=31)
        notes = self.write_model_notes(dated)

        completed = self.run_wrapper("start-run", model_notes=notes)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        stdout_field(completed.stdout, "Run id")
        warnings = self.warnings(completed.stdout)
        self.assertEqual(len(warnings), 1, completed.stdout)
        self.assertIn("31 days old", warnings[0])

    def test_notes_exactly_30_days_old_are_still_fresh(self) -> None:
        notes = self.write_model_notes(date.today() - timedelta(days=30))

        completed = self.run_wrapper("start-run", model_notes=notes)

        self.assertEqual(self.warnings(completed.stdout), [])

    def test_warns_about_both_an_uncovered_model_and_stale_notes(self) -> None:
        notes = self.write_model_notes(date.today() - timedelta(days=90))

        completed = self.run_wrapper("start-run", catalog="uncovered", model_notes=notes)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(len(self.warnings(completed.stdout)), 2, completed.stdout)

    def test_warns_without_failing_when_the_notes_date_does_not_parse(self) -> None:
        notes = self.write_model_notes("last spring")

        completed = self.run_wrapper("start-run", model_notes=notes)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        stdout_field(completed.stdout, "Run id")
        warnings = self.warnings(completed.stdout)
        self.assertEqual(len(warnings), 1, completed.stdout)
        self.assertIn("date", warnings[0])

    def test_warns_without_failing_when_the_catalog_cannot_be_read(self) -> None:
        notes = self.write_model_notes(date.today())

        completed = self.run_wrapper(
            "start-run", model_notes=notes, codex=self.tmp / "no-codex-here"
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        stdout_field(completed.stdout, "Run id")
        warnings = self.warnings(completed.stdout)
        self.assertEqual(len(warnings), 1, completed.stdout)
        self.assertIn("catalog", warnings[0])

    def test_the_shipped_notes_cover_the_recorded_catalog(self) -> None:
        completed = self.run_wrapper("start-run")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(
            str(PLUGIN_ROOT / "skills" / "orchestrate" / "model-notes.md"),
            stdout_field(completed.stdout, "Model notes"),
        )
        self.assertFalse(
            [w for w in self.warnings(completed.stdout) if "cover" in w], completed.stdout
        )


class DelegateModelGuardrailTest(ModelNotesTestCase):
    def delegate(
        self,
        run_id: str,
        model: str,
        effort: str,
        catalog: str = "recorded",
        codex: Path = FAKE_CODEX,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_wrapper(
            "delegate",
            "--run", run_id,
            "--task", str(self.write_task("# Goal\nSummarise README.md.\n")),
            "--model", model,
            "--effort", effort,
            "--write-scope", "none",
            catalog=catalog,
            codex=codex,
        )

    def test_refuses_ultra_without_running_a_delegate(self) -> None:
        run_id, record = self.start_run()

        completed = self.delegate(run_id, "gpt-6.1-sol", "ultra")

        self.assertEqual(completed.returncode, 2)
        self.assertIn("ultra", completed.stderr)
        self.assertEqual(self.codex_calls(), [])
        self.assertFalse((record / "delegations").exists())

    def test_refuses_a_model_missing_from_the_live_catalog(self) -> None:
        run_id, record = self.start_run()

        completed = self.delegate(run_id, "gpt-6.1-sool", "medium")

        self.assertEqual(completed.returncode, 2)
        self.assertIn("gpt-6.1-sool", completed.stderr)
        self.assertIn("catalog", completed.stderr)
        self.assertIn("gpt-6.1-sol", completed.stderr, "the message should list the models")
        self.assertEqual(self.codex_calls(), [])
        self.assertFalse((record / "delegations").exists())

    def test_refuses_a_model_the_catalog_hides(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, "codex-auto-review", "medium")

        self.assertEqual(completed.returncode, 2)
        self.assertIn("codex-auto-review", completed.stderr)
        self.assertNotIn("codex-auto-review", completed.stderr.partition("available:")[2])
        self.assertEqual(self.codex_calls(), [])

    def test_reads_the_catalog_live_at_each_delegation(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, "gpt-7-nova", "medium", catalog="uncovered")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.only_codex_call().option("--model"), "gpt-7-nova")

    def test_refuses_an_effort_the_model_does_not_support(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, "gpt-6-luna", "hgih")

        self.assertEqual(completed.returncode, 2)
        self.assertIn("hgih", completed.stderr)
        self.assertIn("xhigh", completed.stderr, "the message should list the efforts")
        self.assertEqual(self.codex_calls(), [])

    def test_fails_when_the_catalog_cannot_be_read(self) -> None:
        run_id, _ = self.start_run()

        completed = self.delegate(run_id, "gpt-6-luna", "medium", codex=self.tmp / "no-codex-here")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("OPUS_ORCHESTRATOR_CODEX", completed.stderr)
