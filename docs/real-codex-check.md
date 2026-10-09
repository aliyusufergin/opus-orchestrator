# Real-Codex check

The wrapper run against the real Codex, to confirm the assumptions behind the fake Codex and the design (issue #9). The recordings refresh the fake's scenarios in [tests/fixtures/codex](../tests/fixtures/codex/README.md). Rerun the check when Codex changes version, and add a dated section.

## 2026-10-07

- **Codex CLI:** 0.159.2, signed in with ChatGPT Plus, no API key
- **Git:** 2.53.0; Linux
- **Where:** a throwaway repository with `src/greet.py`, `src/main.py` and `src/old.py`, as in the tests
- **Run:** one Run of 11 Delegations, all on `gpt-6-luna`, plus one direct `codex exec` for the network grant
- **Token usage:** 320,890 input (194,560 cached) and 4,810 output tokens: 290,718 input (176,640 cached) and 4,413 output in the Run, and the rest in the direct network probe. The timed-out Delegation's usage was never reported.
- **Evidence:** the Run record and the direct probe's events stayed in the throwaway repository and aren't kept. The `start-run`, `apply` and process observations below come from the terminal output of the check.

| # | Assumption | Observed | Holds |
| --- | --- | --- | --- |
| 1 | Tracer: a real Run sends a question to GPT-6 Luna and the Orchestrator reads its Result | `start-run` listed the live catalog without warnings. A read-only Delegation (d1) ran one `rg` command and returned `done`, naming `src/main.py:3`, with the Result schema met and usage reported. 7.8 s. | yes |
| 2 | Three concurrent Delegations work signed in with ChatGPT | Four read-only Delegations started together. Three ran at once (d4–d6, all started 09:08:50), and the fourth (d7) waited 7.0 s for a slot. All four returned `done`, no event reported an error, and Codex's stderr was empty for each. The API-key fallback (ADR 0003) isn't needed. | yes |
| 3 | The Contract's precedence line wins over a conflicting `AGENTS.md` | `AGENTS.md` required a CHANGELOG.md line for every change under `src/`. With Write scope `src`, the Delegate (d8) changed only `src/greet.py` and recorded in `assumptions`: "The write scope permits changes only under src, so I did not update CHANGELOG.md despite the repository instruction." Hiding `AGENTS.md` (ADR 0006) isn't needed. | yes |
| 4 | A Delegate that wants to ask the user returns `blocked` in `exec` | Told to ask the user for a new name and wait, the Delegate (d9) returned `blocked` at once, with `open_questions: ["What should greet() be renamed to?"]`. Codex emitted no event asking for input: only the agent message and `turn.completed`. | yes |
| 5 | The Quota-exhausted error text matches what the wrapper recognises | Not observable: the Quota wasn't exhausted, and exhausting it on purpose would cost the user's five-hour window. The messages in `error-messages.json` stay as taken from Codex's source. | not checked |
| 6 | A writing Delegate can write inside its worktree under the sandbox, and nowhere else | A probe script run by the Delegate (d3), its output returned through the diff: writing in the worktree succeeded. `touch` failed on `/tmp`, on the main working tree and on `$HOME` (exit 1). Appending to the worktree's `.git` file failed (exit 2), while `git status` worked. The sandbox profile Codex passed to `codex-linux-sandbox` (seen in the process list) gives the worktree write access and its `.git` read access only. A commit also writes to the main repository's Git directory, which lies outside the worktree. A commit wasn't tried. | yes |
| 7 | The network is off, and a network grant turns it on | Through the wrapper, `curl https://example.com` failed with exit 6 (host not resolved), and so did Python's `urllib`. The same probe through `codex exec` with `-c sandbox_workspace_write.network_access=true`, and otherwise the wrapper's options, reached the network (exit 0 for both). Codex's mechanism works, **but the wrapper has no option to grant network**, though issue #1 and ADR 0006 give the Contract one. | mechanism yes; **wrapper lacks it** |
| 8 | The full flow from Snapshot to diff to three-way apply | With an uncommitted README.md and an untracked `src/notes.py` in the working tree, a writing Delegation (d2) saw `src/notes.py` and changed the three `src/` files asked for. Its Check passed when rerun, and the worktree was removed. `apply` took the diff over the uncommitted changes and left the index empty. Applying a second diff (d8) whose change touched the same lines left conflict markers in `src/greet.py`, with exit code 3. | yes |
| 9 | A timeout ends in `partial` | With a 1-minute timeout and a Delegate (d10) waiting on `sleep 300`, the wrapper stopped Codex at 60.0 s. It wrote a `partial` Result with `failure_kind: timeout` and the diff of the file already added, and its Check rerun passed. The worktree was removed. **But the sandboxed `sleep 300` kept running after the wrapper exited**; see below. | Result yes; **process cleanup no** |

Also checked: resuming the writing Delegate (d11 resumes d2). Codex continued the same thread: the resumed `thread.started` event repeats its id. The diff against the original Snapshot held both rounds.

## Failed assumptions and the user's decisions

### A timed-out Delegate's commands outlive it

The wrapper ends Codex's process group on timeout (`run_process_group`), assuming that this ends everything Codex started. On Linux, Codex runs each command through `codex-linux-sandbox` in a new session and PID namespace. So the sandboxed command isn't in the process group: it is reparented to init and runs on after the wrapper exits, here a `sleep 300` in the worktree that had been removed. With a network grant, or with a long build, such a leftover would keep using the network or the CPU unseen.

No fallback was recorded. The directions offered were:

- make the wrapper a child subreaper (`PR_SET_CHILD_SUBREAPER`) and end every descendant;
- run Codex in a cgroup or a systemd scope that can be killed whole;
- accept the leftover and have the evidence name it.

**Decided on 2026-10-09:** the wrapper tracks every process Codex starts and ends them all, as a child subreaper, without new dependencies. Issue #23.

### The wrapper has no network grant

Issue #1 lists "an optional network grant" among `delegate`'s inputs, and ADR 0006 keeps the network off "unless the Contract grants it". The wrapper always passes `sandbox_workspace_write.network_access=false`, and the read-only sandbox has no network, so no Delegation can get it. Codex's own setting works (item 7), so a grant is a small wrapper change for writing Delegations; whether the read-only sandbox can take a grant wasn't checked. **Decided on 2026-10-09:** add a network grant to `delegate` for writing Delegations, and check against the real Codex whether a read-only one can take it. Issue #24.

## Other observations

- **A Result can claim commands that never ran.** In d2, the Delegate's `checks` listed two `touch` probes with exit code 1, but its events hold no such command. The wrapper's Check reruns exist for this. It's a candidate for the skill's Gotchas: a Result's `checks` are claims, and the events and `check_reruns` are the evidence.
- **A timed-out Delegation reports no token usage**, because Codex is stopped before `turn.completed`. The report shows "not reported" for it, so the ChatGPT Quota it spent doesn't show.
- **`file_change` items carry absolute paths** into the worktree, where the old fake scenarios had relative ones. The wrapper doesn't read them.
- **A resumed turn numbers its items from `item_0` again.**
- **A Check can leave build output in the worktree**, such as `src/__pycache__/` from a Python Check. Here the Delegate removed it itself. The wrapper takes the diff before it reruns the Checks, so build output from the reruns stays out of the diff.
- **The live catalog was unchanged** from the recording of 2026-10-06.
