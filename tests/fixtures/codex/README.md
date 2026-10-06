# Fake Codex scenarios

Each directory is one scenario that [`fake_codex.py`](../../fake_codex.py) plays back:

- `events.jsonl`: written to stdout, as `codex exec --json` does.
- `last-message.json` (optional): written to the `--output-last-message` path. Without it, no final message is written.
- `exit-code` (optional): the exit code, 0 when absent.

## Where the outputs come from

The events are built from real `codex exec --json` output, recorded with Codex CLI 0.159.2 on 2026-10-05 during the design probes. The event framing, thread ids, the `command_execution` item shape and the token usage are as recorded. The Delegate's final messages are rewritten to the Result shape, because the probes used a different output schema.

| Scenario | Built from |
| --- | --- |
| `read-only-done` | A recorded `codex exec` call with one command item (usage 24587 input, 18944 cached, 130 output) |
| `read-only-blocked` | A recorded `codex exec` call with only a final message (usage 13661 input, 19 output) |
| `no-result` | The recorded opening events, then a `turn.failed` event shaped after Codex's documented event types. No failure was recorded. |

The real-Codex check (issue #9) refreshes these from new recordings.
