# Fake Codex scenarios

Each directory is one scenario that [`fake_codex.py`](../../fake_codex.py) plays back:

- `events.jsonl`: written to stdout, as `codex exec --json` does.
- `last-message.json` (optional): written to the `--output-last-message` path. Without it, no final message is written.
- `exit-code` (optional): the exit code, 0 when absent.
- `edits.json` (optional): changes to the working directory, made before the events are written. `write` maps paths to their new text and `delete` lists paths to remove.
- `hang-seconds` (optional): how long to wait after the events, before writing the final message.

## Where the outputs come from

The events and final messages are real `codex exec --json` output, recorded with Codex CLI 0.159.2 on 2026-10-07 during the [real-Codex check](../../../docs/real-codex-check.md), through the wrapper with GPT-6 Luna. The Delegation ids below are that check's. The Delegates' final messages are already in the Result shape. Where a scenario is changed from its recording, the table says how.

| Scenario | Built from |
| --- | --- |
| `read-only-done` | d1, as recorded: one `rg` command, then the Result (usage 19736 input, 8960 cached, 178 output) |
| `read-only-blocked` | d9, as recorded: a Delegate told to ask the user returns `blocked` with only a final message (usage 9894 input, 68 output) |
| `read-only-slow` | As `read-only-done`, waiting two seconds before its final message |
| `no-result` | d1's opening events, then a `turn.failed` event shaped after Codex's documented event types. No failure was recorded. |
| `write-done` | d2, a writing Delegation with a `file_change` item, as recorded, except that two sandbox-probe entries are dropped from its Result's `checks` |
| `write-outside-scope` | d2's framing, with its `file_change` item naming `src/greet.py` and `README.md` |
| `write-no-result` | d2's opening and a `file_change` item for `src/greet.py`, ending in the `turn.failed` event of `no-result` |
| `write-hang` | d2's events up to the `item.started` of the command after its file change, then hanging: a timed-out Delegation's stream stops on a command still running, without `turn.completed`, as d10's did |
| `no-thread` | Only an `error` event, shaped after Codex's documented event types: Codex failed before starting a session. Not recorded. |
| `write-followup` | d11, as recorded: d2 resumed, continuing its thread with one further change. Its `edits.json` holds only that change, since the resumed worktree already holds d2's. |

The recorded `file_change` paths are absolute paths into the check's worktree; the wrapper doesn't read them. `edits.json` holds the changes the recorded Delegates made, or for the shaped scenarios the changes their events name.

## Codex error messages

[`error-messages.json`](error-messages.json) holds the quota and sign-in failure messages the wrapper recognises in Codex's `error` and `turn.failed` events, each with the failure kind it gives and where it comes from in Codex's source at tag `rust-v0.159.2`. Usage-limit messages end in a reset time, filled in here as Codex formats it. The real-Codex check could not observe them. The tests play each message back in an event built after the `no-result` framing. The wrapper matches the leading text the messages share, in `CODEX_ERROR_TEXTS`; when Codex changes a message, update both.

## Model catalogs

[`catalogs/`](catalogs) holds what `codex debug models` prints, selected by `FAKE_CODEX_CATALOG`:

| Catalog | Built from |
| --- | --- |
| `recorded` | `codex debug models` from Codex CLI 0.159.2 with ChatGPT sign-in, recorded on 2026-10-06 and unchanged on 2026-10-07, trimmed to the fields the wrapper reads or a reader needs: slug, name, description, default and supported efforts, visibility and priority |
| `uncovered` | `recorded` plus a listed `gpt-7-nova` that no Model notes cover |

The real-Codex check refreshes these from new recordings.
