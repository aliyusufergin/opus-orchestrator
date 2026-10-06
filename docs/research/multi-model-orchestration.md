# Multi-model orchestration: Claude Opus orchestrating OpenAI models from Claude Code

Research date: **2026-10-05**. Versions checked locally: Claude Code **2.1.289**, Codex CLI **0.159.2** (signed in with ChatGPT, `auth_mode=chatgpt`, no `OPENAI_API_KEY`; `~/.codex/config.toml` default `model = "gpt-6-astra"`, `model_reasoning_effort = "medium"`). Models, prices, flags and plugins in this area change monthly, so re-check anything marked with a date before relying on it. Instruction and skill design is covered in a separate document and is only mentioned here in passing.

"Local probe" means a command run on this machine on 2026-10-05. The probes were `codex --help`, `codex exec --help`, `codex debug models`, and three `codex exec` calls on `gpt-6-luna` in an empty scratch directory.

---

## Summary

1. **`codex exec` via Bash is now the only stable, first-party way to delegate agentic work to Codex from Claude Code.** `codex mcp-server` was removed in CLI 0.154.0 (2026-09-09) ([release notes](https://github.com/openai/codex/releases/tag/rust-v0.154.0)). Its replacement, `app-server`, speaks its own JSON-RPC rather than MCP, and OpenAI calls it "experimental and isn't supported for production workloads" ([OpenAI](https://learn.chatgpt.com/docs/mcp-server)).
2. **`codex exec` has everything an orchestrator needs.** It offers `-m`, `-c model_reasoning_effort=…`, `-s read-only|workspace-write|danger-full-access`, `--output-schema`, `-o`, `--json` (with per-turn `usage`), `--ephemeral`, `--worktree`, `resume` and `fork`. It is read-only by default ([OpenAI](https://learn.chatgpt.com/docs/non-interactive-mode); local `codex exec --help`).
3. **Called from Claude Code's Bash tool, `codex exec` hangs forever unless stdin is closed.** It prints "Reading additional input from stdin..." and waits (local probe; [openai/codex#48716](https://github.com/openai/codex/issues/48716)). A trivial call then took 6.3 s and **13,661 input tokens of Codex harness overhead**, which was cached on the next call (13,056 cached) (local probe).
4. **OpenAI ships an official Claude Code plugin, [`openai/codex-plugin-cc`](https://github.com/openai/codex-plugin-cc)** (v1.0.6). It provides `/codex:review`, `/codex:adversarial-review`, `/codex:rescue` and an optional Stop-hook review gate. It wraps the app-server through a Sonnet "thin forwarder" subagent. Its last commit is 2026-07-07, and it has dozens of open lifecycle bugs, for example [#803](https://github.com/openai/codex-plugin-cc/issues/803), [#789](https://github.com/openai/codex-plugin-cc/issues/789) and [#751](https://github.com/openai/codex-plugin-cc/issues/751).
5. **A Claude Code subagent cannot natively be an OpenAI model.** The `model` field takes Claude aliases or IDs resolved against one session-wide endpoint ([docs](https://code.claude.com/docs/en/sub-agents)). Anthropic "doesn't support routing Claude Code to non-Claude models through any gateway" ([docs](https://code.claude.com/docs/en/llm-gateway)). Cross-provider delegation therefore means **a Claude-side caller (main agent, subagent, workflow agent or hook) shelling out to Codex or the OpenAI API**.
6. **The user's design already runs in production at Amp.** Amp's default "Medium" mode uses **Opus 5.5 as the agent and GPT-6 Astra as the "Oracle" advisor** ([ampcode.com/modes](https://ampcode.com/modes)). Amp chose cross-family advice, not wholesale delegation.
7. **At API list prices, GPT-6 Astra costs 2.5× Claude Opus 5.5 per token** ($10/$50 vs $4/$20). GPT-6.1 Sol costs half of Opus ($2/$10) and GPT-6 Luna is 40× cheaper ($0.10/$0.50) ([OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)). Delegating "to save money" to Astra is a false economy. Note that `codex exec` with no `-m` on this machine runs Astra.
8. **Multi-agent setups multiply tokens.** Anthropic measured agents at ~4× and multi-agent systems at ~15× the tokens of chat. Token usage explained 80% of performance variance. Anthropic also warns that "most coding tasks involve fewer truly parallelizable tasks than research" ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).
9. **Context sharing is the main failure risk, and writes should stay single-threaded.** Cognition first argued against parallel subagents ([2025](https://cognition.com/blog/dont-build-multi-agents)). Its 2026 update says multi-agent "work[s] best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions" ([2026](https://cognition.com/blog/multi-agents-working)).
10. **Cross-family review helps, but the effect is asymmetric and not guaranteed.** In one study, Claude reviewing Codex drafts raised the pass rate from 71.6% to 89.7%, while Codex reviewing Claude drafts *lowered* it from 91.4% to 82.8% ([arXiv 2607.21656](https://arxiv.org/abs/2607.21656)). In another, a cross-model review plus a fresh-context review found more planted errors than two fresh-context reviews (56.7% vs 42.7%) ([arXiv 2610.01471](https://arxiv.org/abs/2610.01471)).
11. **Model diversity is weaker insurance than it looks.** Errors are correlated across providers, more so for stronger models ([arXiv 2506.07962](https://arxiv.org/abs/2506.07962), [2502.04313](https://arxiv.org/abs/2502.04313)). Majority voting explains most of the gains attributed to multi-agent debate ([arXiv 2508.17536](https://arxiv.org/abs/2508.17536)). Mixing different models can *lower* ensemble quality compared with sampling the best one ([arXiv 2502.00674](https://arxiv.org/abs/2502.00674)).
12. **Codex delegates may delegate further, invisibly to Opus.** Codex subagents are on by default and inherit the parent's model and effort. The Codex-only `ultra` effort adds "automatic task delegation" ([OpenAI](https://learn.chatgpt.com/docs/agent-configuration/subagents.md); local `codex debug models`). Delegates should run with `-c agents.enabled=false` and never at `ultra`.

---

## 1. Mechanisms inside Claude Code for calling another provider's model

### 1.1 Comparison at a glance

| Substrate | Gets Codex's agent harness (tools, sandbox, AGENTS.md)? | Structured output | Parallel / background | Cost visibility | Failure handling | Status (2026-10) |
|---|---|---|---|---|---|---|
| **Bash → `codex exec`** | Yes | `--output-schema` + `-o` file | `run_in_background` Bash (30 min default, 2 h max), or N processes; each process is isolated | `--json` emits `turn.completed.usage` (input, cached, cache-write, output, reasoning) | Exit code, `turn.failed`/`error` events, stderr; you must add `timeout` and `</dev/null` | **Documented, supported** ([OpenAI](https://learn.chatgpt.com/docs/non-interactive-mode)) |
| Bash → `codex exec review` / `codex review` | Yes (built-in review prompt) | Built-in review format | Same as above | Same | Same | Supported; scope flags can't combine with a custom prompt ([ToB notes](https://github.com/trailofbits/skills/blob/main/plugins/second-opinion/skills/second-opinion/references/codex-invocation.md)) |
| Bash → `codex cloud exec --attempts N` | Yes, in OpenAI cloud | Diffs via `codex cloud diff/apply` | Remote, best-of-N | Plan usage | Remote task status | `[EXPERIMENTAL]` (local `codex cloud --help`) |
| **Official plugin `openai/codex-plugin-cc`** | Yes (via app-server) | Review JSON schema | Background jobs + `/codex:status`/`result`/`cancel` | Not exposed; review threads are ephemeral ([#675](https://github.com/openai/codex-plugin-cc/issues/675)) | Many open hang and lifecycle bugs (see §6) | v1.0.6, last commit 2026-07-07 |
| MCP: `codex mcp-server` | n/a | n/a | n/a | n/a | n/a | **Removed in 0.154.0** ([release](https://github.com/openai/codex/releases/tag/rust-v0.154.0)) |
| MCP: community (PAL/Zen, tuannvm) | PAL `clink`: yes, but bypasses sandbox by default | Tool-defined | Main-thread MCP calls auto-background after 2 min; subagent calls don't | Server-dependent | Server-dependent | PAL last pushed 2025-12-15 |
| Codex app-server JSON-RPC | Yes | `outputSchema` on `turn/start` | Yes | Events | Yes | "Experimental, … not supported for production" ([OpenAI](https://learn.chatgpt.com/docs/mcp-server)) |
| Direct OpenAI API script (Responses/Batch/Flex) | **No** (model only, unless you build a tool loop) | Strict JSON Schema structured outputs | Unlimited concurrency up to rate limits; Batch is asynchronous | Exact `usage` per response; per-token billing | Your code | Stable; needs an **API key**, not ChatGPT login |
| Gateway/router under Claude Code (CCR, LiteLLM, `ANTHROPIC_BASE_URL`) | No: the GPT model runs *inside Claude Code's harness* | n/a | n/a | Gateway logs | Translation 400s | Works by protocol translation; **not supported** by Anthropic for non-Claude models |

### 1.2 Bash calling `codex exec` (recommended substrate)

**Flags** (local `codex exec --help`, CLI 0.159.2, cross-checked with [OpenAI non-interactive docs](https://learn.chatgpt.com/docs/non-interactive-mode)):

| Need | Flag | Notes |
|---|---|---|
| Model | `-m <slug>` | Without it, Codex uses `~/.codex/config.toml`, which is `gpt-6-astra` on this machine |
| Reasoning effort | `-c model_reasoning_effort='"high"'` | Codex catalog levels: low, medium, high, xhigh, max; `ultra` on Sol/Astra (local `codex debug models`) |
| Sandbox | `-s read-only` (default) / `workspace-write` / `danger-full-access` | "By default, `codex exec` runs in a read-only sandbox" ([OpenAI](https://learn.chatgpt.com/docs/non-interactive-mode)). `workspace-write` has network off unless configured ([OpenAI](https://learn.chatgpt.com/docs/agent-approvals-security.md)) |
| Approvals | `exec` has no `-a`; `--approve-for-me` routes approvals to automatic review | `--full-auto` is deprecated ([OpenAI](https://learn.chatgpt.com/docs/non-interactive-mode)) |
| Isolation | `--worktree` (new managed git worktree), `-C <dir>`, `--add-dir` | `--worktree` is listed in local help; no doc page was found for it |
| Structured result | `--output-schema schema.json`, `-o last.json` | Local probe: `{"answer":"391","confidence":1}` matched an `additionalProperties:false` schema |
| Events and telemetry | `--json` (JSONL on stdout) | Events: `thread.started` (with `thread_id`), `turn.started`, `item.*`, `turn.completed` (with `usage`), `turn.failed`, `error` ([OpenAI](https://learn.chatgpt.com/docs/non-interactive-mode)) |
| Continuity | `codex exec resume <id>/--last`, `codex exec fork` | Requires *not* using `--ephemeral` |
| Hygiene | `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, `--skip-git-repo-check` | `--ignore-user-config` drops the user's default model, which is a useful guard |

**Observed behavior** (local probe, `gpt-6-luna`, effort low, empty directory, no AGENTS.md):
- Without `</dev/null`, the process blocked for more than 180 s on "Reading additional input from stdin...". `exec` appends piped stdin to the prompt and waits for EOF when stdin is not a TTY (local help text). The same bug is reported in [#48716](https://github.com/openai/codex/issues/48716), [#20919](https://github.com/openai/codex/issues/20919) and [#27019](https://github.com/openai/codex/issues/27019).
- With `</dev/null`: 6.3 s wall time, `usage: {input_tokens: 13661, cached_input_tokens: 0, output_tokens: 19}`. A repeat call took 8.4 s with `cached_input_tokens: 13056`. That is **~13.7K tokens of fixed per-call harness overhead before any repo context**, mostly cacheable across processes. A repo with AGENTS.md and skills will add more; that case was not measured.
- The `--json` stream carried `thread_id` and `usage` but **no model name**. Confirming which model actually ran therefore needs another source (unverified; see §7).

**Tradeoffs.** Context isolation is total: the delegate starts cold and re-reads what it needs, which is good for independence and bad for handoff fidelity. Latency is seconds for trivial calls and minutes for real tasks. Claude Code's Bash foreground timeout defaults to 2 min (max 10). On timeout the command moves to the background instead of dying. Background commands get 30 min by default and up to 2 h ([Claude Code tools reference](https://code.claude.com/docs/en/tools-reference)). Bash output inline is capped at roughly 30,000 characters (same source), so read results from the `-o` file rather than stdout.

**Prior art built on this substrate.**
- **Trail of Bits `second-opinion`** ([repo](https://github.com/trailofbits/skills/tree/main/plugins/second-opinion), v1.8.3) is a skill, not a subagent. It runs `codex exec -c model='"gpt-5.6-sol"' -c model_reasoning_effort='"xhigh"' --sandbox read-only --ephemeral --output-schema … -o "$output_file" - < "$prompt_file"`. It sends the *same captured diff* to Codex and/or Antigravity, runs providers concurrently, and presents agreements and disagreements "without turning agreement into proof". It treats nonzero exit, empty or invalid JSON, or sandbox denials as an incomplete review, and stops on auth or quota errors instead of cycling providers ([codex-invocation.md](https://github.com/trailofbits/skills/blob/main/plugins/second-opinion/skills/second-opinion/references/codex-invocation.md), [SKILL.md](https://github.com/trailofbits/skills/blob/main/plugins/second-opinion/skills/second-opinion/SKILL.md)).
  - *Correction to the brief:* the plugin **no longer** bundles `codex mcp-server` or the OpenAI cookbook prompt. Both were removed in commit `f44eeba` (2026-09-14, [PR #306](https://github.com/trailofbits/skills/pull/306)) after [issue #301](https://github.com/trailofbits/skills/issues/301) documented the 0.154.0 breakage. The pre-1.8.3 SKILL.md used the "Build Code Review with the Codex SDK" cookbook prompt verbatim, claiming GPT-5.4+ "received specific training on it" (diff of `f44eeba`).
  - Its default model, `gpt-5.6-sol`, is now "older generation" in Codex's catalog and costs 2× `gpt-6.1-sol` ($4/$20 vs $2/$10). Model defaults go stale quickly.

### 1.3 MCP servers

- **`codex mcp-server` is gone.** It was deprecated on 2026-08-24 per the OpenAI changelog, as reported by [Trail of Bits #301](https://github.com/trailofbits/skills/issues/301), and removed in 0.154.0 ("The deprecated `codex mcp-server` entry point is no longer available. (#42993)", [release](https://github.com/openai/codex/releases/tag/rust-v0.154.0)). On 0.159.2, `codex mcp-server` returns `error: unrecognized subcommand` (local). Third parties broke: [trailofbits/skills#301](https://github.com/trailofbits/skills/issues/301), [KjellKod/quest#176](https://github.com/KjellKod/quest/issues/176), [NousResearch/hermes-agent#118943](https://github.com/NousResearch/hermes-agent/issues/118943). It used to expose `codex` and `codex-reply` tools; the current OpenAI page no longer lists them, so that is unverified here. `codex mcp` (add/list/get/remove/login/logout) only manages *external* servers *for* Codex (local help).
- **Replacement: `codex app-server`.** It uses JSON-RPC (`thread/start`, `turn/start` with `outputSchema`, `review/start`), "not an MCP server or a drop-in replacement for an MCP client", and is experimental ([OpenAI](https://learn.chatgpt.com/docs/mcp-server), [app-server docs](https://learn.chatgpt.com/docs/app-server.md)). OpenAI steers automation to the **Codex SDK** instead: TypeScript `@openai/codex-sdk` (`startThread`, `run`, `resumeThread`) or Python `openai-codex` over app-server ([Codex SDK](https://learn.chatgpt.com/docs/codex-sdk.md)).
- **PAL MCP (formerly Zen) by BeehiveInnovations** ([repo](https://github.com/BeehiveInnovations/pal-mcp-server), 11.7K stars, **last push 2025-12-15**):
  - Tools: `chat`, `thinkdeep`, `planner`, `consensus` (multi-model with "stance steering"), `codereview`, `precommit`, `debug`, `challenge`, `apilookup`, `clink`, and others disabled by default to save context.
  - `clink` launches external CLIs as subagents. Its own docs warn: "Codex with `--dangerously-bypass-approvals-and-sandbox`" ([clink.md](https://github.com/BeehiveInnovations/pal-mcp-server/blob/main/docs/tools/clink.md)).
  - Its model recommendations still name GPT-5.2 / Gemini 3.0, so it is stale.
- **tuannvm/codex-mcp-server** ([repo](https://github.com/tuannvm/codex-mcp-server), last push 2026-05-25) exposes `codex` (sessions, model selection, structured metadata), `review`, `websearch`, `listSessions`, `ping` and `help`. It wraps the CLI rather than `codex mcp-server`. Its current compatibility with 0.159 was not tested.
- **Claude Code MCP limits that matter for delegation** ([docs](https://code.claude.com/docs/en/mcp)): tool output warns at 10K tokens and caps at 25K by default (`MAX_MCP_OUTPUT_TOKENS`). Text over 50K characters is saved to a file. `MCP_TOOL_TIMEOUT` defaults to about 28 h. Main-conversation MCP calls auto-background after 2 min, but **calls from subagents don't background**.

### 1.4 Claude Code primitives: what each can and can't do for cross-provider delegation

| Primitive | Can it run an OpenAI model directly? | Useful role in cross-provider delegation | Key facts |
|---|---|---|---|
| **Subagent** (`.claude/agents/*.md`) | **No.** `model` accepts `sonnet`/`opus`/`haiku`/`fable`, a full Claude ID, or `inherit` ([docs](https://code.claude.com/docs/en/sub-agents)). There is no per-agent endpoint | A cheap Claude **wrapper** that makes one `codex exec` call and returns its output. This gives context isolation, background execution and fan-out through the Agent tool. The official plugin's `codex-rescue` is exactly this, with `model: sonnet, tools: Bash` | Up to 20 concurrent (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); nesting up to 3 levels; background subagents keep Bash; `isolation: worktree`; `effort`, `permissionMode`, `hooks`, `mcpServers` fields (same doc) |
| **Skill** | No. `model` follows `/model` values; with `context: fork` it sets the forked subagent's Claude model ([docs](https://code.claude.com/docs/en/skills)) | Packages the *delegation protocol*: CLI recipe, schema, failure table. ToB `second-opinion` is a skill. `disable-model-invocation: true` stops Claude auto-triggering it | Skill design is out of scope here; see the companion research |
| **Plugin** | n/a (container) | Distributes commands, agents, skills, hooks and MCP together, e.g. `openai/codex-plugin-cc` | MCP tools are named `mcp__plugin_<plugin>_<server>__<tool>` ([docs](https://code.claude.com/docs/en/mcp)) |
| **Hooks** | A `command`/`http`/`mcp_tool` hook can call anything; `prompt`/`agent` hooks use Claude ([docs](https://code.claude.com/docs/en/hooks)) | **Gates**: a Stop hook can block stopping and feed a cross-model review back (the official plugin's review gate). `async` + `asyncRewake` can run a long Codex review in the background and wake Claude on exit code 2 | Default timeout is 600 s for command hooks. The plugin's Stop hook uses 900 s, which equals its review timeout, so a slow review ends the turn silently ([#766](https://github.com/openai/codex-plugin-cc/issues/766)) |
| **Slash commands** | n/a | Human-invoked entry points (`/codex:review`) | Keeps delegation explicit and user-controlled |
| **Dynamic workflows** | No. `agent()` spawns Claude subagents; the script itself has "no direct filesystem or shell access" ([docs](https://code.claude.com/docs/en/workflows)) | For large fan-outs, each `agent()` can wrap one `codex exec`. Intermediate results stay in script variables, not Opus's context. `schema` on `agent()` validates output with 5 retries | Up to 16 concurrent agents by default; 1,000 per run; "Large workflow" warning above 25 agents or 1.5M projected tokens. **Untested** with Codex wrappers |
| **Agent teams** | No (Claude instances) | Not a good fit: experimental, costs "approximately 7x more tokens … in plan mode" ([costs](https://code.claude.com/docs/en/costs)) | "Two teammates editing the same file leads to overwrites" ([docs](https://code.claude.com/docs/en/agent-teams)) |
| **Advisor tool** (`/advisor`) | **No.** Claude-only pairings, Anthropic API only, server-side ([docs](https://code.claude.com/docs/en/advisor)) | The *native* analog of a cross-model second opinion: the advisor sees the full transcript and Claude decides when to call it. Opus 5.5 can only take an Opus 5+ or Fable advisor | The advisor's read is not cached ("Each advisor call processes the full transcript anew") |
| **Ultracode** | n/a | A Claude Code setting that makes Claude plan workflows for every substantive task ([model-config](https://code.claude.com/docs/en/model-config)). This is the Claude-side analog of Codex `ultra`; leave it off while orchestrating explicitly | Raises token use; skips the large-workflow warning and the concurrency cap |

**Can `model:` point at a GPT model through a gateway?** The documented route is `ANTHROPIC_CUSTOM_MODEL_OPTION`, where "Claude Code skips validation … so you can use any string your API endpoint accepts" ([model-config](https://code.claude.com/docs/en/model-config)), plus a gateway that translates Anthropic Messages to OpenAI. Even then:
- The whole session must go through that gateway.
- Claude Code sends Claude-specific fields (adaptive thinking, `output_config`, `context_management`, `cache_control`) that a translator must bridge or the request returns 400 ([gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol)).
- Anthropic explicitly doesn't support non-Claude upstreams ([llm-gateway](https://code.claude.com/docs/en/llm-gateway)).
- The GPT model would run with *Claude Code's* system prompt and tools, not Codex's harness.

Whether a subagent `model:` value like `gpt-6.1-sol` passes validation was **not tested**.

### 1.5 Gateways and routers are a different pattern

[claude-code-router (CCR)](https://github.com/musistudio/claude-code-router) (37.5K stars, active) and LiteLLM ([docs](https://code.claude.com/docs/en/llm-gateway)) **replace the model under the harness**. They route by request, fail over, translate OpenAI Chat/Responses and Anthropic Messages, and log cost. That is *model substitution*, not orchestration:
- There is no second agent harness and no independent context.
- The "verifier" isn't independent, because it shares Claude Code's prompts and tools.
- Prompt caching, thinking and structured-output semantics are translated lossily.
- Claude Code's prompt cache and features assume Claude.

Gateways are useful for cost control or org policy across providers. They don't serve "Opus decides, OpenAI executes, Opus reconciles." Note also that setting a gateway credential replaces the claude.ai subscription credential for those requests, so usage moves to per-token billing ([llm-gateway](https://code.claude.com/docs/en/llm-gateway)).

### 1.6 Official integrations between Claude Code and OpenAI

- **[`openai/codex-plugin-cc`](https://github.com/openai/codex-plugin-cc)** (OpenAI-authored; marketplace `openai-codex`; install with `/plugin marketplace add openai/codex-plugin-cc`, then `/plugin install codex@openai-codex`):
  - **Commands:** `/codex:review` (read-only, "same quality … as running `/review` inside Codex", not steerable), `/codex:adversarial-review` (steerable challenge review), `/codex:rescue` (delegate a task; `--background`, `--resume`, `--fresh`, `--model`, `--effort`), `/codex:transfer` (convert this Claude session into a resumable Codex thread), and `/codex:status`/`/codex:result`/`/codex:cancel`.
  - **Optional `Stop`-hook review gate.** The README warns it "can create a long-running Claude/Codex loop and may drain usage limits quickly".
  - **Architecture** ([source](https://github.com/openai/codex-plugin-cc/tree/main/plugins/codex)): a Node companion talks to a per-workspace app-server *broker* over JSON-RPC. Threads start with `approvalPolicy: "never"` and `sandbox: "read-only"` by default (`workspace-write` with `--write`). The `codex-rescue` subagent is `model: sonnet, tools: Bash` and is told to be "a thin forwarding wrapper", returning Codex output verbatim and *not* attempting a Claude-side fix if Codex fails.
  - **Review schema:** `verdict`, `findings[]` with severity/file/line/confidence/recommendation, and `next_steps`. The result-handling skill forbids auto-applying review fixes.
  - **Defaults:** model and effort are unset unless the user asks, so they inherit `~/.codex/config.toml`. `rescue` is write-capable by default.
  - **Staleness:** the bundled prompting skill targets GPT-5.4, and effort validation rejects `max`/`ultra` ([#703](https://github.com/openai/codex-plugin-cc/issues/703), [#751](https://github.com/openai/codex-plugin-cc/issues/751)).
- **[`openai/openai-developers-for-claude`](https://github.com/openai/openai-developers-for-claude)** is a Claude Code plugin with the OpenAI Docs MCP plus skills for building *on* OpenAI (Agents SDK, ChatGPT Apps, API keys). It is not a delegation tool, but its Docs MCP is a good way to keep model facts current.
- **Anthropic's official marketplace** (`claude-plugins-official`, local snapshot with 315 plugins) contains **no** Codex/OpenAI delegation plugin. The OpenAI plugin is distributed through its own marketplace.
- No Anthropic-built integration with OpenAI models was found. Anthropic's own second-opinion features (`/advisor`, `opusplan`) are Claude-only.

### 1.7 Direct OpenAI API calls via a small script

This is useful when the delegated job is **"think about this artifact"** rather than "go operate on the repo."

- **Responses API with strict Structured Outputs.** Use `required` + `additionalProperties: false`; refusals arrive in a separate `refusal` field ([guide](https://developers.openai.com/api/docs/guides/structured-outputs)).
- **Batch:** 50% off, completes within 24 h, supports `/v1/responses`, up to 50,000 requests or 200 MB per batch ([guide](https://developers.openai.com/api/docs/guides/batch)).
- **Flex** (`service_tier: "flex"`, beta): Batch rates synchronously but slower. "429 Resource unavailable … You will not be charged"; retry with backoff or fall back to `auto`; SDK timeouts of ~15 min ([guide](https://developers.openai.com/api/docs/guides/flex-processing)).
- **Prompt caching** is automatic from 1,024 tokens. For GPT-5.6+ the cache lives 30 min, **writes cost 1.25×**, and reads cost 0.1× (**0.05× on GPT-6.1 Sol**) ([guide](https://developers.openai.com/api/docs/guides/prompt-caching)).
- **Tradeoffs.** The script, not Opus, should read the files it sends, so Opus doesn't pay output tokens to transcribe context. It has no agent loop: the model can't explore, so context packing decides quality. It requires `OPENAI_API_KEY` and per-token billing, separate from the ChatGPT plan. It is also the cleanest cost accounting.

---

## 2. Comparable orchestration patterns in other agent environments

| System | What it does concretely | Cross-provider? | Transferable lesson |
|---|---|---|---|
| **Amp (Sourcegraph): Oracle** | The main agent consults an "Oracle" for "difficult reasoning and planning questions". Medium mode: **Opus 5.5 agent + GPT-6 Astra oracle**. High: GPT-6 Astra + Fable 5.1 oracle. Search runs on GPT-5.6 Terra, Librarian on GPT-5.6 Sol ([modes](https://ampcode.com/modes), [docs](https://ampcode.com/docs/models-and-subagents)) | **Yes, by design** | Production evidence that the cheapest valuable cross-family integration is *advice at decision points* plus cheap specialist *readers*, not delegating the writing |
| **Claude Code advisor** | Executor consults a stronger model mid-task. Sonnet + Opus advisor scored +2.7 pp on SWE-bench Multilingual at 11.9% lower cost per task. Haiku + Opus scored 41.2% vs 19.7% solo on BrowseComp ([Anthropic blog, 2026-04-09](https://claude.com/blog/the-advisor-strategy)) | No (Claude-only) | The advisor pattern works when the *caller* is strong enough to know when to ask. Here Opus is the caller, which suits it |
| **Cognition (Devin)** | 2025: single-threaded agent plus context compression ([post](https://cognition.com/blog/dont-build-multi-agents)). 2026-03: a coordinator Devin manages child Devins, each in its own VM ([post](https://cognition.com/blog/devin-can-now-manage-devins)). 2026-04: "smart friend" with a *weaker* primary underperformed; cross-frontier routing works "when both models are strong"; clean-context reviewers average 2 bugs per PR, ~58% severe ([post](https://cognition.com/blog/multi-agents-working)) | Yes (routing across frontier models) | Single-threaded writes; parallel readers and reviewers; clean-context review; route by *capability*, not difficulty escalation |
| **Aider architect/editor** | An architect model proposes, an editor model emits edits. o1-preview + o1-mini/DeepSeek scored 85.0%, o1-preview + Sonnet 82.7%, Sonnet + Sonnet 80.5% on aider's benchmark (2024-09-26) ([blog](https://aider.chat/2024/09/26/architect.html), [docs](https://aider.chat/docs/usage/modes.html)) | Yes | Splitting *reasoning* from *edit formatting* helps when a model is strong at one and weak at the other. Codex's harness already handles edit formatting for GPT models |
| **Roo Code Orchestrator ("Boomerang")** | The orchestrator can't read or write files or run commands. It delegates through `new_task` (context passed explicitly), and only the `attempt_completion` summary returns ([docs](https://roocodeinc.github.io/Roo-Code/features/boomerang-tasks)). **Repo archived 2026-05** | Per-mode models (not verified) | A strict information diet for the orchestrator: explicit context down, summary up |
| **Cursor `/best-of-n`** | The same task runs on several models, each in its own worktree. No automatic merge; the user applies the winner (`/apply-worktree`) ([docs](https://cursor.com/docs/configuration/worktrees)) | Yes | Isolation by worktree is the standard answer to parallel writers. Selection is the hard part |
| **OpenAI Agents SDK** | "Agents as tools": the manager keeps control and combines outputs. "Handoffs": the specialist takes over the conversation. Code-based orchestration ("structured outputs to classify tasks", `asyncio.gather`, evaluator loops) gives "greater determinism" ([docs](https://openai.github.io/openai-agents-python/multi_agent/)) | Model-agnostic | Opus-orchestrates is **agents-as-tools**, never handoff. Put deterministic fan-out in code, not in the LLM |
| **Anthropic Research (orchestrator-worker)** | Opus 4 lead + Sonnet 4 subagents beat single Opus by 90.2% on research. ~15× chat tokens. Early failures: "spawning 50 subagents for simple queries" ([post](https://www.anthropic.com/engineering/multi-agent-research-system)) | No | Gains come from spending more tokens in parallel on *breadth-first* tasks. Coding parallelizes less |
| **Codex itself** | Native subagents (on by default; inherit model and effort; `agents.max_concurrent_threads_per_session`). `ultra` = proactive delegation ([docs](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)). `codex cloud exec --attempts N` = best-of-N (local help) | No (OpenAI only) | A delegate can itself fan out, so **disable** it for bounded contracts |
| **Factory Droid** | Spec-mode model separate from execution; subagent tiers light/medium/heavy, each pinnable to a model and effort, default `inherit` ([docs](https://docs.factory.com/cli/configuration/mixed-models)) | Yes | Tiered routing table with explicit pins; inheritance as a silent fallback is a known trap |
| **OpenHands SDK** | `RouterLLM` presents several LLMs as one, with `select_llm()`. `TaskToolSet` handles sub-agent delegation with parallel tool execution ([docs](https://docs.openhands.dev/sdk/guides/llm-routing)) | Yes | Router-as-LLM (substitution) vs task tool (delegation) are distinct, which mirrors §1.5 |
| **User's prior project, [codex-orchestration](https://github.com/aliyusufergin/codex-orchestration)** | A Codex Parent with six non-delegable decision rights. Pinned spawns (explicit model, effort and fresh context). Routing "starts cheap", with a one-line reason to escalate. A scrutiny floor by Consequence, using a *different model* for high-consequence review. Candidates are Parent commits. A spawn audit compares requested vs realized settings. Ultra is discouraged for the Parent because it auto-delegates (local `CONTEXT.md`, `docs/adr/0001-0007`) | No (OpenAI-only) | See the transfer table below |

**What transfers from codex-orchestration to an Opus-parent, OpenAI-delegate design:**

| Concept (ADR) | Transfers? | Adaptation |
|---|---|---|
| Parent keeps six decision rights: Intent, Architecture, Plan, Scrutiny, Integration, Acceptance (0001) | **Directly** | Opus owns them. Delegates return evidence or proposals and escalate at decision points |
| Only the parent spawns; every spawn is pinned (0002) | **Yes, stronger need** | Always pass `-m` and effort; add `-c agents.enabled=false` (Codex nested subagents are on by default and inherit settings). Optionally `--ignore-user-config` so `gpt-6-astra` can't leak in. Never use `ultra` for delegates |
| Spawn audit, requested vs realized (0002) | Partially | `--json` gives `thread_id` and `usage` but no model name (local probe). Realized-model proof would need persisted sessions (non-`--ephemeral`) or OpenAI usage logs (unverified) |
| Bounded work, contracts carry properties not roles (0005, 0006) | **Yes** | A contract becomes prompt + `--output-schema` + sandbox mode + `-C`/`--worktree` + write scope + acceptance commands |
| Bounded work delegated *by default* (0005) | **Reconsider** | Cross-provider delegation cost is higher than native spawns: cold context, ~13.7K-token harness overhead, prompt-family differences, verification. Delegate when the price gap or diversity pays for it (§5); Claude subagents are the cheap same-harness alternative |
| Routing starts cheap (0004) | Yes | Starting point is `gpt-6-luna` for mechanical work, `gpt-6.1-sol` for real coding. Compare against Claude Haiku 4.5 / Sonnet 5.5 as same-harness options |
| Scrutiny floor by Consequence, different model for high (0004) | **Yes, with a caveat** | Opus + GPT reviewer is cross-family by construction. But one study shows GPT reviewing Claude code can *hurt* (§4), so the floor should require executable evidence and Opus adjudication, not just "a different model looked" |
| Candidates are parent commits (0007) | **Yes** | Delegates never commit. This also sidesteps the worktree `gitdir`-outside-sandbox failure ([#765](https://github.com/openai/codex-plugin-cc/issues/765)) |
| Parent-only run when spawning is unavailable | Yes | Codex auth or quota failure means Opus does the work itself and labels it "no independent review" |

---

## 3. Approaches that challenge "the orchestrator delegates everything"

| Approach | Core claim | Evidence | Implication here |
|---|---|---|---|
| **Single agent with good context** (Cognition 2025) | "Share context, and share full agent traces"; "Actions carry implicit decisions, and conflicting decisions carry bad results" ([post](https://cognition.com/blog/dont-build-multi-agents)) | Flappy Bird example; Cognition's 2026 revision keeps writes single-threaded ([post](https://cognition.com/blog/multi-agents-working)) | Default to Opus doing coupled work; delegate reads, reviews and isolated leaves |
| **Start simple** (Anthropic) | Add complexity "only when it demonstrably improves outcomes"; patterns are routing, parallelization (sectioning and voting), orchestrator-workers and evaluator-optimizer ([post, 2024-12-19](https://www.anthropic.com/engineering/building-effective-agents)) | Design guidance | Evaluator-optimizer (Opus generates, GPT critiques, or the reverse) is lighter than full orchestration |
| **Cascades and routers for cost** | FrugalGPT matches GPT-4 "with up to 98% cost reduction" by learned cascades ([arXiv 2305.05176](https://arxiv.org/abs/2305.05176)); RouteLLM cuts cost ">2 times" with learned strong/weak routers ([arXiv 2406.18665](https://arxiv.org/abs/2406.18665)) | Benchmarks on short QA/chat | Cascade (cheap first, escalate on low confidence or failed checks) fits delegation, but needs a reliable *escalation signal*. Cognition found weak models bad at knowing when to escalate |
| **Mixture-of-Agents** | Layered aggregation of many LLMs scored 65.1% vs 57.5% for GPT-4o on AlpacaEval 2.0 ([arXiv 2406.04692](https://arxiv.org/abs/2406.04692)) | ... but **Self-MoA** (one best model sampled repeatedly) beat mixed MoA by 6.6% on AlpacaEval and 3.8% on average; "mixing different LLMs often lowers the average quality" ([arXiv 2502.00674](https://arxiv.org/abs/2502.00674)) | Don't ensemble weaker models for *generation*; diversity pays mainly in *verification* |
| **Multi-agent debate** | Debate improves reasoning and factuality ([Du et al., 2305.14325](https://arxiv.org/abs/2305.14325)) | MAD often fails to beat CoT or self-consistency ([2502.08788](https://arxiv.org/abs/2502.08788), [2311.17371](https://arxiv.org/abs/2311.17371)). Majority voting explains most of the gain, and debate alone is a martingale ([2508.17536](https://arxiv.org/abs/2508.17536)). *Heterogeneous* panels help ([2410.12853](https://arxiv.org/abs/2410.12853), [2502.08788](https://arxiv.org/abs/2502.08788)) but carry adversarial influence ([2606.19826](https://arxiv.org/abs/2606.19826)) | Prefer **independent parallel opinions + Opus adjudication** over multi-round model-to-model debate |
| **Best-of-N + verifier** | Coverage scales log-linearly with samples; on SWE-bench Lite, 15.9% at 1 sample rose to 56% at 250 samples ([2407.21787](https://arxiv.org/abs/2407.21787)). Without an automatic verifier, voting and reward models plateau | Coding has verifiers (tests) | Best-of-N delegation (Codex cloud `--attempts`, Cursor `/best-of-n`) only pays with executable selection criteria |
| **Advisor / second-opinion only** | Strong model consulted at decision points ([Anthropic advisor](https://claude.com/blog/the-advisor-strategy), [Amp](https://ampcode.com/modes)) | Production adoption at Amp; Anthropic benchmarks | **Highest value per token** for Opus + OpenAI: Opus does the work, GPT critiques plans, diffs and stuck diagnoses |

---

## 4. Evidence on verification and second opinions across model families

**Bias and correlation**
- **Self-preference is real and partly about familiarity.** LLM judges recognize and favor their own generations, and the bias scales with self-recognition ([Panickssery et al., 2404.13076](https://arxiv.org/abs/2404.13076)). Judges also rate low-perplexity, "familiar" text higher regardless of source ([Wataoka et al., 2410.21819](https://arxiv.org/abs/2410.21819)). MT-Bench already listed position, verbosity and self-enhancement biases ([2306.05685](https://arxiv.org/abs/2306.05685)).
- **Family similarity, not just identity.** Judges favor models *similar* to themselves, and "model mistakes are becoming more similar with increasing capabilities" ([Goel et al., 2502.04313](https://arxiv.org/abs/2502.04313)). Across 350+ LLMs, models agree on 60% of their errors on one leaderboard, and "larger and more accurate models have highly correlated errors, even with distinct architectures and providers" ([Kim et al., 2506.07962](https://arxiv.org/abs/2506.07962)).
- **Self-correction without external feedback doesn't work reliably** for reasoning ([Huang et al., 2310.01798](https://arxiv.org/abs/2310.01798)). External signals such as tests, compilers, or a different reviewer are what add information.

**Cross-model code review (2026, preprints, small samples)**
- **Asymmetric pairing** ([Xiang et al., 2607.21656](https://arxiv.org/abs/2607.21656)):
  - Setup: Claude Opus 4.7 via Claude Code 2.1.50 vs GPT-5.5 via Codex CLI, both at high effort; 116 LiveCodeBench tasks; *static* review with no test execution.
  - Claude reviewing Codex drafts: 71.6% → **89.7%**. Codex self-review: 84.5%.
  - Codex reviewing Claude drafts: 91.4% → **82.8%** (worse). Claude self-review left the baseline unchanged.
  - Cost per task $0.19–$0.44; latency 38–136 s.
  - Caveat: one model pair, older models, no execution.
- **When a second model helps** ([Song, 2610.01471](https://arxiv.org/abs/2610.01471)):
  - Setup: 30 artifacts, 150 planted errors, 900 sessions; reviewers GPT-5.4, Gemini 2.5 Pro, Gemini 2.5 Flash; "CCR" means same-model review in a fresh session.
  - A top-tier cross-model reviewer was not significantly better than CCR, but the two found *partly different* errors (Jaccard 41.2%).
  - With two review calls, CCR + cross-model found **56.7% vs 42.7%** for two CCRs.
  - A lightweight cross-model reviewer was no better than CCR.
  - Caveat: capability and model identity are confounded; artifacts in Korean; single generator.
- **Clean context matters as much as family.** Cognition's reviewer works better with "clean context" separate from the coder's ([post](https://cognition.com/blog/multi-agents-working)).

**Multi-agent failure taxonomy (MAST)** ([Cemri et al., 2503.13657](https://arxiv.org/abs/2503.13657); 1,600+ traces, 7 frameworks, κ = 0.88):
- **System design, 43.8%:** disobey task spec 11.8%, step repetition 15.7%, unaware of termination 12.4%, and others.
- **Inter-agent misalignment, 32.2%:** reasoning-action mismatch 13.2%, task derailment 7.4%, fail to ask for clarification 6.8%, and others.
- **Task verification, 23.5%:** incorrect verification 9.1%, none or incomplete 8.2%, premature termination 6.2%.
- Explicit verifiers reduce failures but are "not a silver bullet".
- Simple interventions (CEO approval before termination; objective verification) gave +9.4% and +15.6% on ChatDev, but success stayed low.

**When ensembles help vs add noise**

| Helps | Adds noise or cost |
|---|---|
| Executable selection signal (tests) with best-of-N ([2407.21787](https://arxiv.org/abs/2407.21787)) | Opinion-only voting past a few samples (plateaus, same source) |
| Independent cross-family reviewer at **similar or higher capability** on a clean context ([2610.01471](https://arxiv.org/abs/2610.01471)) | Lightweight cross-family reviewer (no better than same-model fresh review, same source) |
| Heterogeneous panels for reasoning, with voting ([2410.12853](https://arxiv.org/abs/2410.12853), [2508.17536](https://arxiv.org/abs/2508.17536)) | Multi-round debate without a correction bias; weaker models mixed into generation ([2502.00674](https://arxiv.org/abs/2502.00674)) |
| Claude reviewing GPT code (one study) | GPT reviewing Claude code (same study: −8.6 pp) |

---

## 5. Cost and token economics

### 5.1 List prices (USD per 1M tokens, standard tier, fetched 2026-10-05)

| Model | Input | Cache read | Cache write | Output | Batch (in/out) | Notes |
|---|---|---|---|---|---|---|
| **Claude Opus 5.5** | $4 | $0.20 (0.05×) | $5 (5 min) / $8 (1 h) | $20 | $2 / $10 | 1M context, 128K output; Fast mode $8/$40 ([pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models](https://platform.claude.com/docs/en/about-claude/models/overview)) |
| Claude Sonnet 5.5 | $2 | $0.20 | $2.50 | $10 | $1 / $5 | Same token price as GPT-6.1 Sol |
| Claude Haiku 4.5 | $1 | $0.10 | $1.25 | $5 | $0.50 / $2.50 | Retirement not sooner than 2026-10-15 |
| **gpt-6-astra** | $10 | $1.00 | $12.50 | $50 | $5 / $25 | Long context (>272K): 2× input, 1.5× output ([model page](https://developers.openai.com/api/docs/models/gpt-6-astra)) |
| **gpt-6.1-sol** | $2 | $0.10 (0.05×) | $2.50 | $10 | $1 / $5 | Released 2026-09-29 per [TechCrunch](https://techcrunch.com/2026/09/29/openai-launches-gpt-6-1-sol-says-it-nearly-matches-gpt-6-astra-and-costs-less/) (secondary); "near-Astra performance at a lower cost" ([model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol)) |
| **gpt-6-luna** | $0.10 | $0.01 | $0.125 | $0.50 | $0.05 / $0.25 | Supports Flex and Batch ([model page](https://developers.openai.com/api/docs/models/gpt-6-luna)) |
| gpt-5.6-sol | $4 | $0.40 | $5 | $20 | $2 / $10 | "Older generation" in the Codex catalog; promo pricing through ≥2026-11-21 |
| gpt-5.5 | $5 | $0.50 | – | $30 | $2.50 / $15 | **Retires from Codex 2026-10-14** (local `codex debug models` migration notice); still listed in the API |

Sources: [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

The user's 2026-09-30 snapshot ($0.10/$0.50, $2/$10, $10/$50) **matches** the current OpenAI pages.

**Effort levels.**
- The API model pages list `low`…`max` (Luna also accepts `none`). **No `ultra`.**
- `ultra` exists only in Codex's client catalog, on Sol/Astra (and 6-Sol, 5.6-Sol/Terra), described as "Maximum reasoning with automatic task delegation" (local `codex debug models`).
- Codex's catalog default effort is `low` for 6.1-Sol and Astra; the API page says the 6.1-Sol default is `medium`. Defaults differ by surface, so always pin.

**Caveats on cross-family comparison**
- **Tokenizers differ.** Claude 4.7+ "produces approximately 30% more tokens for the same text" than earlier Claude ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)). Per-token prices across families are therefore not per-task prices. Measure on your own tasks.
- **Reasoning tokens bill as output on both sides.** Effort settings move cost more than list price does.

### 5.2 Subscription (ChatGPT login) vs API key

- With ChatGPT auth, Codex usage draws on plan limits, not per-token billing.
- Plus local-message ranges per 5 h: **Luna 350–3,000, 6.1 Sol 15–160, Astra 5–45**. Pro is reported to have no 5-hour limits "currently" ([OpenAI Codex pricing](https://learn.chatgpt.com/docs/pricing)).
- Credit rates per 1M tokens: Luna 2.5 in / 12.5 out; Sol 50 / 250; Astra 250 / 1,250, a 1:20:100 ratio. Fast mode costs 2.5× included limits (same source).
- **Implication:** on Plus, a parallel Astra fan-out exhausts the 5-hour window in a handful of calls. Luna or Sol fan-out is viable.
- OpenAI recommends **API key auth for programmatic and CI use** ("Use API key authentication for programmatic Codex CLI workflows") and `CODEX_API_KEY` set inline per invocation ([auth](https://learn.chatgpt.com/docs/auth), [non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)).
- Some models are "not supported when using Codex with a ChatGPT account" ([ToB failure table](https://github.com/trailofbits/skills/blob/main/plugins/second-opinion/skills/second-opinion/references/codex-invocation.md)).

### 5.3 Where the tokens actually go

1. **Orchestrator ingestion is permanent.** Everything a delegate returns enters Opus's context and is re-read on every later turn, at the 0.05× cache-read rate while the cache is warm. A cache miss after the TTL reprocesses it in full ([costs](https://code.claude.com/docs/en/costs)). Schema-shaped, terse results keep this small. A raw transcript or diff does not.
2. **Delegation overhead per call.** About 13.7K input tokens of Codex harness (measured, empty directory). That is ≈$0.137 uncached on Astra, ≈$0.027 on 6.1 Sol and ≈$0.0014 on Luna, and roughly 10–20× less when cached. Add the delegate's own repo reading, because it starts cold. Add Opus's output tokens to write the contract (billed at $20/M) and to read the result.
3. **Multi-agent multiplier.** Agents use ~4× and multi-agent systems ~15× chat tokens ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Claude Code agent teams use ~7× in plan mode ([costs](https://code.claude.com/docs/en/costs)). Codex subagents "consume more tokens than comparable single-agent runs" ([OpenAI](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)).
4. **Verification can erase the savings.** If Opus re-reads the full diff and files to check the delegate's work, it pays most of what it would have paid to do the work, so the saving disappears. Cheap verification means tests and checks run by the delegate, with commands and exit codes returned as evidence, plus a targeted Opus read of only the risky hunks.
5. **Illustrative arithmetic** (list prices, not measured). A task needs ~60K tokens of reading and ~3K of output.
   - **Opus doing it:** ~$0.24 + $0.06. Those 60K tokens then sit in Opus's context, costing ~$0.012 per later turn at the cache rate (~$0.24 over 20 turns).
   - **6.1 Sol doing it:** ~$0.12 + $0.03, plus ~2K tokens of result in Opus (~$0.008).
   - **Astra doing it:** ~$0.60 + $0.15, so more expensive than Opus.
   - The dominant saving from delegation is often **context hygiene in the expensive orchestrator**, which Claude-native subagents also provide ([costs: "Delegate verbose operations to subagents"](https://code.claude.com/docs/en/costs)).

**When delegation saves money vs just shifts it**

| Saves | Shifts or increases |
|---|---|
| High-volume, mechanical or read-heavy work on Luna or Sol, with schema-compact returns | Delegating to Astra (2.5× Opus per token) |
| Work whose bulk is the delegate's own tool loop (reading, testing, iterating) | Tasks where Opus must re-read everything to verify |
| Non-urgent bulk through Batch or Flex (50% off) | Many tiny delegations: ~13.7K overhead each, plus Opus contract-writing at $20/M output |
| Keeping logs and diffs out of Opus context | Parallel fan-outs whose outputs all return verbatim to Opus |

Caching considerations: keep delegate prompts' **stable prefix first** (contract boilerplate, schema, AGENTS.md) so OpenAI's prefix cache hits across calls (≥1,024 tokens, 30-min retention). On the Claude side, delegations that alter early context, such as tool definitions or the model, invalidate Opus's cache ([costs](https://code.claude.com/docs/en/costs)).

---

## 6. Practical pitfalls (first-hand reports and official caveats)

| # | Pitfall | Evidence | Mitigation |
|---|---|---|---|
| 1 | `codex exec` hangs on stdin in non-TTY callers | Local probe (>180 s); [#48716](https://github.com/openai/codex/issues/48716), [#20919](https://github.com/openai/codex/issues/20919) | Always `</dev/null`, or pass the prompt with `-` from a file |
| 2 | Indefinite hangs on stream stalls or child-process waits | [#50775](https://github.com/openai/codex/issues/50775), [#34397](https://github.com/openai/codex/issues/34397) | Wrap with `timeout`, run in background Bash, and treat timeout as incomplete |
| 3 | Unpinned model inherits `~/.codex/config.toml` (`gpt-6-astra` here) | Local config; the official plugin leaves model unset by default | Always `-m` and effort; consider `--ignore-user-config` |
| 4 | Hidden nested delegation | Codex subagents are on by default and inherit model and effort; `ultra` auto-delegates ([OpenAI](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)); the user's ADR 0002 observed unpinned spawns at `gpt-6-astra/high` | `-c agents.enabled=false`; never `ultra` for delegates; keep Claude's own Ultracode off when orchestrating explicitly |
| 5 | Integrations built on `codex mcp-server` broke | 0.154.0 removal; [ToB #301](https://github.com/trailofbits/skills/issues/301), [quest #176](https://github.com/KjellKod/quest/issues/176) | Build on `codex exec` or the SDK; pin and smoke-test the CLI version |
| 6 | Shared app-server broker lifecycle across sessions | One session's SessionEnd kills another's job ([#803](https://github.com/openai/codex-plugin-cc/issues/803), [#671](https://github.com/openai/codex-plugin-cc/issues/671)); brokers leak ([#791](https://github.com/openai/codex-plugin-cc/issues/791)) | Prefer short-lived `exec` processes over long-lived brokers |
| 7 | **ChatGPT refresh-token reuse logs out every Codex client** | Long-lived brokers "burn the single-use ChatGPT refresh token (`refresh_token_reused`)" ([#789](https://github.com/openai/codex-plugin-cc/issues/789)); earlier race with concurrent app-servers ([codex#10332](https://github.com/openai/codex/issues/10332)) | Use API-key auth for automation (OpenAI's own advice); avoid many long-lived ChatGPT-auth processes |
| 8 | Concurrency glitches with many `exec` processes | Concurrent first-run sessions lose rows in state DB on a fresh `CODEX_HOME` ([#42447](https://github.com/openai/codex/issues/42447)); marketplace full clone per concurrent exec ([#36093](https://github.com/openai/codex/issues/36093)) | Warm `CODEX_HOME` once; cap parallelism; stagger starts |
| 9 | Parallel writers on one tree | "Two teammates editing the same file leads to overwrites" ([agent teams](https://code.claude.com/docs/en/agent-teams)); conflicting implicit decisions ([Cognition](https://cognition.com/blog/dont-build-multi-agents)) | Disjoint write scopes; `--worktree` or separate worktrees per writer; Opus integrates |
| 10 | Worktrees vs Codex sandbox | Linked worktree `gitdir` sits outside the writable roots, so git writes fail ([#765](https://github.com/openai/codex-plugin-cc/issues/765), [#673](https://github.com/openai/codex-plugin-cc/issues/673)); broker disables git hooks in worktrees ([#697](https://github.com/openai/codex-plugin-cc/issues/697)) | Delegates edit files only and **never commit**; Opus commits (ADR 0007 pattern) |
| 11 | False "done" | `codex-rescue reports completion without checking git state` ([#754](https://github.com/openai/codex-plugin-cc/issues/754)); MAST premature termination 6.2%, incorrect verification 9.1% ([2503.13657](https://arxiv.org/abs/2503.13657)) | Opus checks `git diff --stat` and acceptance commands itself before accepting |
| 12 | Write-capable by default | [#798](https://github.com/openai/codex-plugin-cc/issues/798); PAL `clink` ships `--dangerously-bypass-approvals-and-sandbox` ([clink.md](https://github.com/BeehiveInnovations/pal-mcp-server/blob/main/docs/tools/clink.md)) | Default `-s read-only`; grant `workspace-write` per contract; never `danger-full-access` outside a disposable container |
| 13 | Review gates that loop and drain quota | Plugin README warning; re-blocks the same finding ([#790](https://github.com/openai/codex-plugin-cc/issues/790)); hook timeout equals review timeout ([#766](https://github.com/openai/codex-plugin-cc/issues/766)); fails open on bad state ([#684](https://github.com/openai/codex-plugin-cc/issues/684), [#676](https://github.com/openai/codex-plugin-cc/issues/676)) | Gate only high-consequence turns; cap the number of review rounds; record overrides |
| 14 | Claude Code's sandbox vs Codex | Sandboxed Bash has "no direct route out" and starts with an **empty** domain allowlist; `excludedCommands` runs a command unsandboxed, but "a redirect to a file … keeps the whole call sandboxed" ([sandboxing](https://code.claude.com/docs/en/sandboxing)). Nested bubblewrap inside the Claude sandbox is undocumented | Allow OpenAI hosts and `~/.codex` writes explicitly, or run Codex as a narrowly matched excluded command. Test before relying on it |
| 15 | Output size limits | Bash inline ~30K characters ([tools](https://code.claude.com/docs/en/tools-reference)); MCP 25K tokens ([mcp](https://code.claude.com/docs/en/mcp)) | `-o` file + schema; Opus reads only the JSON |
| 16 | Stale model or effort assumptions in tooling | Plugin rejects `max`/`ultra` ([#751](https://github.com/openai/codex-plugin-cc/issues/751)); prompting skill targets retired GPT-5.4 ([#703](https://github.com/openai/codex-plugin-cc/issues/703)); ToB default `gpt-5.6-sol`; GPT-5.5 leaves Codex 2026-10-14 | Keep one dated capability table; prefer live `codex debug models` over hard-coded names |
| 17 | Prompt-format differences between families | OpenAI's own plugin ships a GPT prompting skill (XML-tagged blocks, explicit output contracts) ([skill](https://github.com/openai/codex-plugin-cc/blob/main/plugins/codex/skills/gpt-5-4-prompting/SKILL.md)); GPT-6 Astra "can also be more sensitive to information in context" ([OpenAI](https://developers.openai.com/api/docs/guides/latest-model)) | Use a separate contract template for OpenAI delegates (detail is in the companion instruction-design research). Codex reads AGENTS.md natively, and this repo's CLAUDE.md imports AGENTS.md, so both families share one instruction source |
| 18 | Nondeterminism | Repeated sampling changes outcomes ([2407.21787](https://arxiv.org/abs/2407.21787)) | Treat a single delegate run as a sample; use tests for selection and N>1 only where a verifier exists |
| 19 | Delegate output treated as instructions | Claude Code marks inter-agent messages as not-from-user; workflow prompts don't count as user requests in auto mode ([agent teams](https://code.claude.com/docs/en/agent-teams), [workflows](https://code.claude.com/docs/en/workflows)) | Treat Codex output as untrusted data: findings to verify, never commands to run |
| 20 | Data governance | ChatGPT auth follows workspace retention and RBAC; API key follows the API org's settings ([auth](https://learn.chatgpt.com/docs/auth)) | Decide which repos may be sent to OpenAI |

---

## 7. Design implications for Claude Opus orchestrating OpenAI models

### 7.1 Recommended substrate (opinionated)

1. **Primary: a repo-owned delegation wrapper around `codex exec`, called from Opus through Bash.**
   - Run it in the background for parallel work and return only a schema-validated JSON file.
   - Hard defaults:
     ```
     codex exec -m <pinned> -c model_reasoning_effort='"<pinned>"' -c agents.enabled=false \
       -s read-only --output-schema <contract-schema> -o <result.json> --json \
       [--ephemeral | keep session for resume/audit] [-C <worktree>] - < prompt.md
     ```
     Wrap it in `timeout`, send stdin from a file (never an open pipe), log JSONL events to a file, and parse `turn.completed.usage` for cost.
   - **Why this one:** it is the only option that is OpenAI-documented, harness-complete (Codex tools, sandbox, AGENTS.md, apply-patch, model-specific prompts), structured, measurable and resumable. It survived the `mcp-server` removal, and it is what Trail of Bits converged on after the breakage.
   - Use direct background Bash first. Use a Haiku or Sonnet wrapper subagent only when you need Agent-tool parallelism or isolation of the call itself.
   - **Untested option:** a dynamic workflow (`agent()` per Codex call) for large fan-outs that shouldn't touch Opus's context.
2. **Secondary: a small Responses API script for non-agentic second opinions** (plan critique, diff review on a packed artifact) **and bulk work through Batch or Flex.** It needs an API key, gives exact per-token accounting, and the script packs the context, not Opus.
3. **Use `openai/codex-plugin-cc` for ad-hoc, human-invoked reviews** (`/codex:review`, `/codex:adversarial-review`). **Don't build orchestration on it.** It isn't pinned by default, it is write-capable by default, it has broker and auth lifecycle bugs, and its effort list is stale. Borrow its review schema, its "thin forwarder, verbatim result, no Claude-side substitute on failure" rule, and its result-handling discipline.
4. **Keep Claude-native subagents (Haiku 4.5 / Sonnet 5.5) as the default for read-heavy exploration.** They cost the same as or less than Sol, need zero integration, keep cache and context semantics intact, and avoid cross-harness handoff. Choose OpenAI when you want **model diversity** (review, adversarial planning, a stuck second diagnosis), **Luna-class prices** for volume, or a specific Codex strength.

**Avoid:**
- Gateway model-swapping (CCR, LiteLLM) for this goal.
- `codex mcp-server` and stale MCP wrappers.
- PAL `clink` defaults.
- Multi-round model-to-model debate.
- Parallel writers on a shared tree.
- `ultra` or Ultracode during explicit orchestration.
- Any unpinned delegate.
- Astra as a cost-saving delegate.

### 7.2 Shape of the protocol

- **Decision rights stay with Opus** (from the user's ADR 0001): intent, architecture, plan, scrutiny, integration, acceptance. Delegates escalate at the first decision right they meet.
- **Every delegation is a contract:** goal, write scope (or `none`), inputs by path, acceptance commands, output schema, sandbox mode, model and effort with a one-line routing reason.
- **Parallelize reads and reviews freely; isolate writes.** Writes get disjoint scopes and separate worktrees, and run serially where scopes overlap. Opus integrates and is the only committer.
- **Verification ladder:**
  1. Delegate-run checks returned as evidence.
  2. Opus spot-reads risky hunks.
  3. For high consequence, an *independent* reviewer of another family on a clean context, at a capability at least equal to the author's.
- Opus adjudicates findings as hypotheses and reruns tests to confirm. Do not tally votes.
- **Asymmetry note.** The best evidence (one study) favors **Claude reviewing GPT-written code** over the reverse. So when GPT writes, Opus (or a Claude subagent) reviews. When Opus writes, a GPT review is a *second pair of eyes whose findings must be reproduced*, not a gate that can veto on opinion.
- **Routing starts cheap:**
  - Luna: mechanical, high-volume, triage.
  - 6.1 Sol: default delegate for real coding or review.
  - Astra: only for high-consequence review or hard problems where its price (2.5× Opus) is justified.
  - Re-derive the table from `codex debug models` and the pricing page when models change. GPT-5.5 leaves Codex on 2026-10-14.

### 7.3 Open questions the user must decide

1. **Auth and billing:** ChatGPT plan (quota per 5 h; refresh-token fragility with many processes; which plan tier?) or API key (per-token, Batch and Flex available, OpenAI's recommendation for automation)? Or both: plan for interactive use, key for fan-out?
2. **Scope of delegation:** review and advice only (low risk, highest evidence) vs write delegation (needs worktrees, integration and stronger verification)?
3. **Consequence levels and scrutiny floors:** what counts as high consequence, and which reviewer model and effort is the minimum per level?
4. **Parallelism cap:** bounded by plan quota or API tier limits (Tier 1 for 6.1 Sol and Astra is 500 RPM / 500K TPM), and by how many results Opus can absorb.
5. **Audit depth:** keep Codex sessions (non-ephemeral) to prove which model actually ran, or accept requested-settings-only logs?
6. **Data boundary:** which repos or paths may be sent to OpenAI?
7. **Claude-native vs cross-provider default:** when equal in price (Sonnet 5.5 vs 6.1 Sol), which family is the default delegate, given same-harness simplicity vs error independence?
8. **Sandbox posture:** run Claude Code's Bash sandbox (then allowlist OpenAI hosts and `~/.codex`), or rely on Codex's own sandbox?

### 7.4 Claims I could not verify

- Whether a Claude Code subagent `model:` set to a non-Claude ID (e.g. `gpt-6.1-sol`) through a translating gateway passes validation and works. Docs imply technically possible but unsupported; not tested.
- How Codex's bubblewrap sandbox behaves *inside* Claude Code's sandboxed Bash (nested user namespaces), and the exact OpenAI hostnames to allowlist. Undocumented; not tested.
- Whether any `codex exec --json` event or the persisted session records the *realized* model. The observed events had none.
- `codex exec --worktree` semantics: present in local `--help`, no doc page found.
- The exact tool names the removed `codex mcp-server` exposed (`codex`, `codex-reply`), from memory of older docs; current docs don't list them.
- The 2026-08-24 deprecation date of `codex mcp-server`, seen only via third-party quotes of the OpenAI changelog. The 0.154.0 removal is verified from release notes.
- GPT-6.1 Sol's release date (2026-09-29, DevDay) is from TechCrunch and search snippets. The OpenAI model page shows only a knowledge cutoff.
- Codex Pro plan "no five-hour limits currently" and other plan details come from a summarized fetch of the pricing page; exact numbers may vary by plan and date.
- Roo Code per-mode model configuration (not covered by the fetched page); Cursor `/best-of-n` "parent agent commentary/merge" (search snippets said yes, docs page says no automatic merge).
- tuannvm/codex-mcp-server compatibility with Codex 0.159: README only, not run.
- Codex harness overhead in a real repo with AGENTS.md and skills. Only an empty directory was measured (~13.7K tokens).

---

## Sources

**Claude Code and Anthropic (docs fetched 2026-10-05)**
- Subagents: https://code.claude.com/docs/en/sub-agents
- Skills: https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks
- MCP: https://code.claude.com/docs/en/mcp
- Tools reference (Bash limits, Monitor): https://code.claude.com/docs/en/tools-reference
- Dynamic workflows: https://code.claude.com/docs/en/workflows
- Agent teams: https://code.claude.com/docs/en/agent-teams
- Advisor: https://code.claude.com/docs/en/advisor
- Model config (custom model option, Ultracode): https://code.claude.com/docs/en/model-config
- LLM gateway: https://code.claude.com/docs/en/llm-gateway
- Gateway protocol: https://code.claude.com/docs/en/llm-gateway-protocol
- Sandboxing: https://code.claude.com/docs/en/sandboxing
- Costs: https://code.claude.com/docs/en/costs
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Multi-agent research system (2025-06-13): https://www.anthropic.com/engineering/multi-agent-research-system
- Building effective agents (2024-12-19): https://www.anthropic.com/engineering/building-effective-agents
- The advisor strategy (2026-04-09): https://claude.com/blog/the-advisor-strategy

**OpenAI and Codex**
- API pricing: https://developers.openai.com/api/docs/pricing
- Model pages: https://developers.openai.com/api/docs/models/gpt-6.1-sol, https://developers.openai.com/api/docs/models/gpt-6-astra, https://developers.openai.com/api/docs/models/gpt-6-luna
- Flex processing: https://developers.openai.com/api/docs/guides/flex-processing
- Batch: https://developers.openai.com/api/docs/guides/batch
- Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- Structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Latest-model guidance: https://developers.openai.com/api/docs/guides/latest-model
- Codex docs (now at learn.chatgpt.com):
  - Non-interactive mode: https://learn.chatgpt.com/docs/non-interactive-mode
  - MCP server removal: https://learn.chatgpt.com/docs/mcp-server
  - App server: https://learn.chatgpt.com/docs/app-server.md
  - Codex SDK: https://learn.chatgpt.com/docs/codex-sdk.md
  - Subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents.md
  - Approvals and security: https://learn.chatgpt.com/docs/agent-approvals-security.md
  - Auth: https://learn.chatgpt.com/docs/auth
  - Pricing: https://learn.chatgpt.com/docs/pricing
- Codex release 0.154.0: https://github.com/openai/codex/releases/tag/rust-v0.154.0
- Codex issues: https://github.com/openai/codex/issues/48716, /20919, /27019, /50775, /34397, /42447, /36093, /10332
- Official Claude Code plugin: https://github.com/openai/codex-plugin-cc (issues cited inline: #675, #684, #697, #703, #751, #754, #765, #766, #673, #671, #676, #789, #790, #791, #798, #803)
- OpenAI Developers plugin for Claude: https://github.com/openai/openai-developers-for-claude
- GPT-6.1 Sol launch (secondary): https://techcrunch.com/2026/09/29/openai-launches-gpt-6-1-sol-says-it-nearly-matches-gpt-6-astra-and-costs-less/

**Third-party tools and products**
- Trail of Bits second-opinion: https://github.com/trailofbits/skills/tree/main/plugins/second-opinion; issue https://github.com/trailofbits/skills/issues/301; PR https://github.com/trailofbits/skills/pull/306
- PAL MCP: https://github.com/BeehiveInnovations/pal-mcp-server (clink: docs/tools/clink.md)
- tuannvm/codex-mcp-server: https://github.com/tuannvm/codex-mcp-server
- claude-code-router: https://github.com/musistudio/claude-code-router
- Broken `mcp-server` integrations: https://github.com/KjellKod/quest/issues/176, https://github.com/NousResearch/hermes-agent/issues/118943
- Amp: https://ampcode.com/modes, https://ampcode.com/docs/models-and-subagents
- Aider: https://aider.chat/docs/usage/modes.html, https://aider.chat/2024/09/26/architect.html
- Roo Code (archived 2026-05): https://roocodeinc.github.io/Roo-Code/features/boomerang-tasks
- Cursor: https://cursor.com/docs/configuration/worktrees
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/multi_agent/
- Factory: https://docs.factory.com/cli/configuration/mixed-models
- OpenHands: https://docs.openhands.dev/sdk/guides/llm-routing
- Cognition: https://cognition.com/blog/dont-build-multi-agents (2025-06-12), https://cognition.com/blog/devin-can-now-manage-devins (2026-03-19), https://cognition.com/blog/multi-agents-working (2026-04-22)

**Papers (arXiv)**
- MAST, why multi-agent systems fail: 2503.13657
- Self-preference: 2404.13076, 2410.21819
- MT-Bench judge biases: 2306.05685
- Great Models Think Alike: 2502.04313
- Correlated errors: 2506.07962
- Mixture-of-Agents: 2406.04692
- Self-MoA: 2502.00674
- FrugalGPT: 2305.05176
- RouteLLM: 2406.18665
- Multiagent debate: 2305.14325
- Debate or Vote: 2508.17536
- Should we be going MAD?: 2311.17371
- Stop Overvaluing MAD: 2502.08788
- Diversity of Thought: 2410.12853
- Heterogeneous debate under adversaries: 2606.19826
- Cannot self-correct: 2310.01798
- Large Language Monkeys: 2407.21787
- More Agents: 2402.05120
- Cross-model code review, Claude vs Codex: 2607.21656
- When does a second model help: 2610.01471

**Local evidence (2026-10-05)**
- `codex --help`, `codex exec --help`, `codex exec resume --help`, `codex cloud exec --help`, `codex mcp-server` (unrecognized), `codex features list`, `codex debug models` (Codex CLI 0.159.2)
- Three `codex exec` probes on `gpt-6-luna` in a scratch directory
- Prior project: `/home/dev/projects/codex-orchestration` (README.md, CONTEXT.md, docs/adr/0001–0007, capability-snapshot.md dated 2026-09-30)
