"""`delegate --network`: a network grant for the Delegate's commands, which are otherwise offline."""

from __future__ import annotations

from support import WrapperTestCase, WritingDelegationTestCase, stdout_field

# The permissions profile that gives a read-only Delegation network: Codex's own read-only one, plus network.
PROFILE = "read_only_network"


class WritingNetworkGrantTest(WritingDelegationTestCase):
    def test_without_the_grant_the_network_stays_off(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id, write_scope=["src/"], scenario="write-done"))

        call = self.only_codex_call()
        self.assertEqual(call.option("--sandbox"), "workspace-write")
        self.assertIs(call.config["sandbox_workspace_write.network_access"], False)
        self.assertIs(evidence["network"], False)

    def test_the_grant_turns_on_network_for_the_delegates_commands_and_nothing_else(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(
            self.delegate(run_id, write_scope=["src/"], scenario="write-done", network=True)
        )

        call = self.only_codex_call()
        self.assertEqual(call.option("--sandbox"), "workspace-write")
        self.assertIs(call.config["sandbox_workspace_write.network_access"], True)
        self.assertIs(call.config["sandbox_workspace_write.exclude_slash_tmp"], True)
        self.assertIs(call.config["sandbox_workspace_write.exclude_tmpdir_env_var"], True)
        self.assertEqual(call.config["web_search"], "disabled")
        self.assertIs(evidence["network"], True)

    def test_the_summary_says_network_was_granted(self) -> None:
        run_id, _ = self.start_run()

        granted = self.delegate(run_id, write_scope=["src/"], scenario="write-done", network=True)
        offline = self.delegate(run_id, write_scope=["src/"], scenario="write-done")

        self.assertEqual(stdout_field(granted.stdout, "Network"), "granted")
        self.assertEqual(stdout_field(offline.stdout, "Network"), "off")


class ReadOnlyNetworkGrantTest(WrapperTestCase):
    def test_without_the_grant_the_read_only_sandbox_has_no_network(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id))

        call = self.only_codex_call()
        self.assertEqual(call.option("--sandbox"), "read-only")
        self.assertNotIn("default_permissions", call.config)
        self.assertIs(evidence["network"], False)

    def test_the_grant_adds_network_to_codexs_read_only_permissions(self) -> None:
        run_id, _ = self.start_run()

        evidence = self.evidence(self.delegate(run_id, network=True))

        call = self.only_codex_call()
        # Codex takes a permissions profile in place of --sandbox, not alongside it.
        self.assertIsNone(call.option("--sandbox"))
        self.assertEqual(call.config["default_permissions"], PROFILE)
        self.assertEqual(call.config[f"permissions.{PROFILE}.extends"], ":read-only")
        self.assertIs(call.config[f"permissions.{PROFILE}.network.enabled"], True)
        self.assertEqual(call.config["web_search"], "disabled")
        self.assertEqual(call.cwd, str(self.repo))
        self.assertIs(evidence["network"], True)
