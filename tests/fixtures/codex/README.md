# Fake Codex scenarios

Each directory is one scenario that [`fake_codex.py`](../../fake_codex.py) plays back:

- `events.jsonl`: written to stdout, as `codex exec --json` does.
- `last-message.json` (optional): written to the `--output-last-message` path. Without it, no final message is written.
- `exit-code` (optional): the exit code, 0 when absent.
- `edits.json` (optional): changes to the working directory, made before the events are written. `write` maps paths to their new text and `delete` lists paths to remove.
- `hang-seconds` (optional): how long to wait after the events, before writing the final message.

## Where the outputs come from

The events are built from real `codex exec --json` output, recorded with Codex CLI 0.159.2 on 2026-10-05 during the design probes. The event framing, thread ids, the `command_execution` item shape and the token usage are as recorded. The Delegate's final messages are rewritten to the Result shape, because the probes used a different output schema.

| Scenario | Built from |
| --- | --- |
| `read-only-done` | A recorded `codex exec` call with one command item (usage 24587 input, 18944 cached, 130 output) |
| `read-only-blocked` | A recorded `codex exec` call with only a final message (usage 13661 input, 19 output) |
| `no-result` | The recorded opening events, then a `turn.failed` event shaped after Codex's documented event types. No failure was recorded. |
| `write-done`, `write-outside-scope` | The recorded framing, with a `file_change` item and token usage shaped after Codex's documented event types. No writing Delegation was recorded. |
| `write-no-result` | As `write-done`, ending in the `turn.failed` event of `no-result` |
| `write-hang` | As `write-done`, hanging before its final message |

## Model catalogs

[`catalogs/`](catalogs) holds what `codex debug models` prints, selected by `FAKE_CODEX_CATALOG`:

| Catalog | Built from |
| --- | --- |
| `recorded` | `codex debug models` from Codex CLI 0.159.2 with ChatGPT sign-in, recorded on 2026-10-06, trimmed to the fields the wrapper reads or a reader needs: slug, name, description, default and supported efforts, visibility and priority |
| `uncovered` | `recorded` plus a listed `gpt-7-nova` that no Model notes cover |

The real-Codex check (issue #9) refreshes these from new recordings.
