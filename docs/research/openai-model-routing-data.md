# OpenAI model routing data: GPT-6 Luna, GPT-6.1 Sol and GPT-6 Astra by reasoning effort

Research date: **2026-10-06**. Local versions: Codex CLI **0.159.2** (ChatGPT Plus sign-in). This document collects the measured evidence behind the **Model notes**: which OpenAI model and reasoning effort a Delegation should use, and what each choice costs in ChatGPT **Quota**. It replaces the draft notes that were not based on evidence. Delegation mechanics are in [multi-model-orchestration.md](multi-model-orchestration.md); this document does not repeat them.

**How the sources were read**
- **openai.com** returns HTTP 403 to automated fetches. The launch posts were read through the `r.jina.ai` text reader on 2026-10-06. Their URLs are cited as the source, with "(via reader)".
- **Artificial Analysis (AA) per-effort numbers** come from the JSON embedded in AA's model and coding-agent pages ([gpt-6-1-sol](https://artificialanalysis.ai/models/gpt-6-1-sol), [gpt-6-astra](https://artificialanalysis.ai/models/gpt-6-astra), [gpt-6-luna](https://artificialanalysis.ai/models/gpt-6-luna), [coding agents](https://artificialanalysis.ai/agents/coding-agents)), fetched 2026-10-06. They were cross-checked against AA's article text: Astra max index 52.7 vs "53", Terminal-Bench 59.1% vs "59%", 6.1 Sol max $0.72/task vs "$0.72", Luna max $0.07 vs "$0.07", Codex 6 Sol max index 56.7 vs "57". A parsing error is still possible.
- **"Credits"** means Codex credits. All Quota arithmetic below is derived in §4.1.
- **"Measured"** means a third party ran the model, or a benchmark maintainer did. **"Vendor claim"** means OpenAI or Anthropic reported it. **"Inference"** means my reasoning from the data.

---

## Summary

1. **In Codex, GPT-6.1 Sol's coding score peaks between medium and xhigh. High adds nothing over medium, and max does worse than xhigh.** On AA's Coding Agent Index in the Codex harness, low through max scored 57.2 / 61.4 / 60.1 / 62.9 / 60.1, at $0.50 / 0.70 / 0.89 / 1.04 / 1.55 per task ([AA coding agents](https://artificialanalysis.ai/agents/coding-agents); measured).
2. **Effort is cheap on Sol, but it buys little on SWE-style work.** Per hard coding task, Sol uses about 11 / 16 / 20 / 24 / 35 credits from low to max. High therefore costs **1.26×** and xhigh **1.47×** the Quota of medium; Astra at max costs **11×** and Luna at max **0.27×** (derived from [AA](https://artificialanalysis.ai/agents/coding-agents) tokens × [Codex credit rates](https://learn.chatgpt.com/docs/pricing)).
3. **On coding, Sol matches or beats Astra for a fraction of the cost.** On AA's Coding Agent Index, Sol at xhigh scored 62.9 against Astra at max 61.6, "for less than 15% of the Cost per Task" ([AA 6.1 Sol](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence); measured).
4. **Astra's effort curve flattens at high.** On the official Terminal-Bench 4.0 leaderboard (Codex harness), Astra scored 50.6 / 54.2 / 57.9 / 57.9 / 58.2% from low to max, with ±2.7–3.0 pp 95% confidence intervals. Going from high to max costs **+44%** and gains 0.3 pp ([tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0); measured).
5. **Luna is not suited to long agentic coding at any effort.** It scored 15.2% on Terminal-Bench 4.0 in Codex at max, against 49.0% for Sol at low. On codebase Q&A it scored 44.4%, against 55.1% for Sol at low ([AA](https://artificialanalysis.ai/agents/coding-agents)). Vals measured 13.6% on Terminal-Bench ([vals](https://www.vals.ai/benchmarks/terminal-bench-4)). All measured.
6. **Luna at low collapses in multi-step tool use.** On AutomationBench it scored 12.0% at low, 40.5% at medium and 47.8% at high ([AA Luna](https://artificialanalysis.ai/models/gpt-6-luna); measured). OpenAI's own Codex advice is "Start with **High** for Luna" ([Codex models](https://learn.chatgpt.com/docs/models)).
7. **Luna reads long documents well but guesses when it doesn't know.** On AA-LCR (long-context reasoning) it scored 78–83% at medium to max, against 80–84% for Sol. Its AA-Omniscience hallucination rate is 77–85%, against about 50% for Sol. On GDP.pdf (reasoning over long PDFs) it scored 14–23%, against 27–32% for Sol ([AA](https://artificialanalysis.ai/models/gpt-6-luna); measured).
8. **Effort barely matters for reading or for short, self-contained code.** Sol scored 84.0% on AA-LCR at low and 83.0% at max, and 53–56% on SciCode at every effort. On codebase Q&A in Codex it scored 60.8% at medium and 61.0% at xhigh ([AA](https://artificialanalysis.ai/models/gpt-6-1-sol); measured).
9. **OpenAI says to start low and raise effort only on evidence.** For xhigh: "Only use when your evals show a clear benefit" ([reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)). Its other advice: "Most tasks do not need Max or Ultra" and "Start with High for Luna or Light for Astra" ([Codex models](https://learn.chatgpt.com/docs/models)). No reason is published for Codex defaulting Sol and Astra to `low` (vendor claim; the rationale is a gap).
10. **`ultra` means xhigh reasoning plus automatic subagent delegation.** The Codex catalog sets `multi_agent_reasoning_effort: "xhigh"` for Sol and Astra, and `resolve_reasoning_effort` maps Ultra to it ([source](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/openai_models/reasoning_effort.rs); local `codex debug models`).
11. **Codex credits are exactly 25× API dollars, cached input included.** Cached-input rates are 0.25 credits per 1M tokens for Luna, 2.5 for Sol and 25 for Astra. On cache-heavy agent loops Astra therefore costs **10×** Sol per cached token, not 5× ([Codex pricing](https://learn.chatgpt.com/docs/pricing), [API model pages](https://developers.openai.com/api/docs/models/gpt-6.1-sol); derived).
12. **Behaviours that matter for unattended runs:**
    - Astra asks clarifying questions and may stop after a first implementation ([GPT-6 guide](https://developers.openai.com/api/docs/guides/latest-model), [OpenAI blog](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)).
    - In OpenAI's adversarial evals, 6.1 Sol misrepresents its coding work in 1.50% of tasks against 0.51% for Astra, and persists past warnings in 23.5% of rollouts against 17.4% ([6.1 Sol system card](https://deploymentsafety.openai.com/gpt-6-1-sol); vendor).
    - All GPT-6 models default to `verbosity: low` in Codex (local `codex debug models`).

**Benchmark caveat.** Epoch rated DeepSWE v1.1 "Flawed" because at least 20.3% of its tasks have verifier errors ([Epoch](https://epoch.ai/benchmarks/deepswe/review)). DeepSWE is one third of AA's coding index and OpenAI's headline coding number. Neither benchmark maintainers nor OpenAI have published SWE-bench Verified or Pro scores for GPT-6 models (§Gaps).

### Corrections and additions to the facts already known

| Already known | Status | Correction or addition |
|---|---|---|
| API $/1M tokens: Luna $0.10/$0.50, 6.1 Sol $2/$10, Astra $10/$50, Opus 5.5 $4/$20, Sonnet 5.5 $2/$10 | **Confirmed** ([Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [AA Opus 5.5](https://artificialanalysis.ai/articles/claude-opus-5-5), [AA Sonnet 5.5](https://artificialanalysis.ai/articles/claude-sonnet-5-5)) | Cached input is priced differently per model: Luna $0.01 (10%), **Sol $0.10 (5%)**, Astra $1.00 (10%) |
| Plus local messages per 5 h: Luna 350–3,000, Sol 15–160, Astra 5–45 | **Confirmed** ([pricing](https://learn.chatgpt.com/docs/pricing)) | GPT-6 Sol is 15–150. OpenAI calls these "estimates… not fixed message limits" |
| Codex credits per 1M tokens: Luna 2.5/12.5, Sol 50/250, Astra 250/1,250 | **Confirmed** ([pricing](https://learn.chatgpt.com/docs/pricing)) | **Add cached-input rates:** Luna 0.25, Sol 2.5, Astra 25. Codex has no cache-write charge. All rates equal 25 × API $ |
| Catalog defaults: Sol and Astra `low`, Luna `medium`; `ultra` on Sol and Astra | **Confirmed** (local `codex debug models`, 0.159.2) | GPT-6 Sol defaults to `medium`. The API default is `medium` for 6.1 Sol, 6 Sol and Luna ([reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)); Astra's API default is not documented. `ultra` resolves to `xhigh` plus delegation. The Codex context window is **272K** (max 872K), against 1.05M in the API |
| 6.1 Sol release date 2026-09-29 (secondary in the earlier doc) | **Now verified** | System card "Published September 29, 2026" ([card](https://deploymentsafety.openai.com/gpt-6-1-sol)); Codex changelog 2026-09-29. Astra was released 2026-09-03 ([card](https://deploymentsafety.openai.com/gpt-6-astra)); 6 Sol and Luna on 2026-09-22 ([changelog](https://learn.chatgpt.com/docs/changelog)) |

---

## 1. Benchmark results

### 1.1 Coding-agent benchmarks run by third parties and maintainers (measured)

**AA Coding Agent Index v1.5, each model in its vendor's harness.** The index is DeepSWE v1.1 (113 tasks), Terminal-Bench 4.0 (66 tasks) and SWE-Atlas-QnA (124 tasks), each scored pass@1 over 3 attempts. Codex rows used CLI 0.154.0 (Astra: 0.151/0.153.4). Fetched 2026-10-06 ([AA coding agents](https://artificialanalysis.ai/agents/coding-agents)).

| Harness: model (effort) | Index | DeepSWE | TB 4.0 | SWE-Atlas-QnA | $/task | Wall time/task | Steps | Output tok/task |
|---|---|---|---|---|---|---|---|---|
| Codex: 6.1 Sol (low) | 57.2 | 67.6 | 49.0 | 55.1 | 0.50 | 518 s | 36 | 14.7K |
| Codex: 6.1 Sol (medium) | 61.4 | 72.0 | 51.5 | 60.8 | 0.70 | 651 s | 38 | 22.4K |
| Codex: 6.1 Sol (high) | 60.1 | 70.5 | 50.0 | 59.9 | 0.89 | 800 s | 39 | 28.7K |
| Codex: 6.1 Sol (xhigh) | **62.9** | 73.2 | 54.5 | 61.0 | 1.04 | 931 s | 40 | 35.4K |
| Codex: 6.1 Sol (max) | 60.1 | 69.6 | 53.0 | 57.8 | 1.55 | 1,463 s | 40 | 61.7K |
| Codex: Astra (max) | 61.6 | 67.6 | 55.6 | 61.8 | 7.47 | 1,762 s | 39 | 47.1K |
| Codex: 6 Sol (max) | 56.7 | 69.0 | 43.4 | 57.5 | 2.99 | 1,338 s | 87 | 62.2K |
| Codex: Luna (max) | 41.1 | 63.7 | 15.2 | 44.4 | 0.18 | 1,286 s | 89 | 98.3K |
| Codex: 5.6 Sol (max) | 54.6 | 72.3 | 37.4 | 54.0 | 6.35 | 1,238 s | 116 | 49.2K |
| Claude Code: Opus 5.5 (max) | 66.0 | 68.4 | 63.1 | 66.4 | 13.04 | 3,867 s | 155 | 333K |
| Claude Code: Sonnet 5.5 (max) | 68.4 | 72.0 | 66.2 | 66.9 | 14.19 | 5,245 s | 266 | 601K |
| Claude Code: Sonnet 5.5 (xhigh) | 62.9 | 68.4 | 58.1 | 62.1 | 3.33 | 1,619 s | 78 | 126K |
| Claude Code: Sonnet 5.5 (high) | 55.0 | 66.7 | 41.9 | 56.5 | 1.24 | 735 s | 37 | 41.5K |
| Claude Code: Sonnet 5.5 (medium) | 45.9 | 65.5 | 27.3 | 44.9 | 0.62 | 511 s | 22 | 20.5K |
| Claude Code: Sonnet 5.5 (low) | 42.1 | 61.9 | 25.3 | 39.0 | 0.48 | 381 s | 19 | 15.8K |

Costs are at API list price. Mean Codex cache-hit rates are 91–96% (same source). AA's Astra article gave $7.09/task on 2026-09-09; the page now shows $7.47, because AA updates cache-hit rates live ([AA Astra](https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra), [methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking)). Luna and Astra were run only at max in this index.

**Terminal-Bench 4.0, official leaderboard** (66 tasks × 5 trials; leaderboard updated 2026-09-21) ([tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0)):

| Agent: model | Effort | Accuracy ±95% CI | pass@5 | $/trial | Output tok/trial | Avg trial time |
|---|---|---|---|---|---|---|
| Codex: Astra | low | 50.6 ±2.8 | 63.6 | 4.72 | 24.2K | 28 min |
| Codex: Astra | medium | 54.2 ±2.7 | 66.7 | 5.80 | 32.6K | 31 min |
| Codex: Astra | high | **57.9 ±3.0** | 71.2 | 6.88 | 41.5K | 35 min |
| Codex: Astra | xhigh | 57.9 ±2.7 | 69.7 | 7.12 | 45.3K | 37 min |
| Codex: Astra | max | 58.2 ±2.8 | 71.2 | 9.90 | 72.7K | 47 min |
| Claude Code: Fable 5.1 | max | 57.9 ±3.8 | 78.8 | 18.92 | 191K | 65 min |
| Codex: GPT-5.6 Sol | max | 37.3 ±3.8 | 60.6 | 7.70 | 71.1K | 40 min |
| Codex: GPT-5.6 Luna | max | 17.3 ±2.9 | 33.3 | 1.05 | 186K | 68 min |

The leaderboard has no 6.1 Sol, 6 Sol, 6 Luna, Opus 5.5 or Sonnet 5.5 rows yet.

**Terminal-Bench 4.0, Vals AI, mini-SWE-agent harness** (avg@3, updated 2026-10-01; Vals' 6.1 Sol page lists "Reasoning Effort: max"; other models' efforts were not checked) ([Vals TB4](https://www.vals.ai/benchmarks/terminal-bench-4), [Vals 6.1 Sol](https://www.vals.ai/models/openai_gpt-6.1-sol)):

| Model | Score | $/test | Duration |
|---|---|---|---|
| Claude Opus 5.5 | 65.15% (58.08% if fallback-served attempts count as failures) | 13.20 | 1h04m |
| Claude Sonnet 5.5 | 64.14% (62.63% counting fallbacks as failures) | 16.51 | 1h22m |
| GPT-6 Astra | 59.60% | 9.58 | 35m42s |
| GPT-6.1 Sol | 55.05% | **1.72** | 45m12s |
| GPT-6 Sol | 44.44% | 5.79 | 34m56s |
| GPT-6 Luna | 13.64% | 0.35 | 32m46s |

### 1.2 Vendor-reported results (vendor claims)

| Model | Benchmark | Score | Effort | Source, date |
|---|---|---|---|---|
| Astra | Terminal-Bench 4.0 | 57.9% | "maximum at any effort". Anthropic says this figure is at high | [OpenAI](https://openai.com/index/gpt-6-astra/) (via reader) 2026-09-03; [Anthropic](https://www.anthropic.com/news/claude-opus-5-5) |
| Astra | DeepSWE v1.1 | 74.1% | max at any effort | [OpenAI](https://openai.com/index/gpt-6-astra/) |
| Astra | FrontierCode 1.1 Main / Extended | 53.3% / 64.5% | max at any effort | same |
| Astra | AA Coding Agent Index v1.4 | 67.0 | max at any effort (index version differs from v1.5 above) | same |
| Astra | Terminal-Bench Science 0.1 | 64.6% (68.1% in the 6.1 Sol post) | max at any effort | same; [6.1 Sol post](https://openai.com/index/introducing-gpt-6-1-sol/) |
| Astra | OpenAI MRCR v2 8-needle, 256K–512K / 512K–1M | 100.0% / 96.3% | max at any effort | [OpenAI](https://openai.com/index/gpt-6-astra/) |
| Astra | Internal hallucination benchmark (lower is better) | 4.2% (GPT-5.6 Sol 12.2%) | max at any effort | same |
| 6.1 Sol | DeepSWE v1.1 | "matches GPT-6 Astra"; 75.2% at **high** | high | [OpenAI](https://openai.com/index/introducing-gpt-6-1-sol/); 75.2% only in an [@OpenAIDevs post](https://x.com/OpenAIDevs/status/2104993067942219873) seen in a search snippet (**unverified**) |
| 6.1 Sol | DeepSWE v1.1 by effort | low 64, medium 73, high 75, xhigh 71, max 71 | per effort | A user's transcription of an OpenAI chart in [deep-swe#102](https://github.com/datacurve-ai/deep-swe/issues/102) (**secondary, unverified**) |
| 6.1 Sol | AutomationBench | +2.2 pp over Opus 5.5 at ~⅓ the cost | **medium** | [OpenAI](https://openai.com/index/introducing-gpt-6-1-sol/) |
| 6.1 Sol | OSWorld 2.0 offline | within 2.1 pp of Astra at ~1/7 the cost/task | max | same |
| 6.1 Sol | Factual errors on flagged prompts | 7.7% (6 Sol: 11.4%) | **low** | same |
| 6 Sol | DeepSWE v1.1 | 68.8% | max | [OpenAI](https://openai.com/index/introducing-gpt-6-sol-and-luna/) (via reader) 2026-09-22 |
| Luna | DeepSWE v1.1 | 66.6% (AA measured 63.7% in Codex) | max | same |
| 6 Sol / Astra | AutomationBench | 6 Sol 33.2% ($0.27/task) vs Astra 30.3% | 6 Sol **xhigh** vs Astra **low** | same |
| Opus 5.5 | Terminal-Bench 4.0 | 66.4% (64.8% at max per a secondary source) | **xhigh** | [Anthropic](https://www.anthropic.com/news/claude-opus-5-5) 2026-09-22 |
| Opus 5.5 | FrontierCode Main | 54.4% (table); 54.6% at **medium** (text) | max / medium | same |
| Opus 5.5 | CursorBench 4.0 | 57.8% (52.5% at medium per text) | max / medium | same |

### 1.3 Reasoning and long context by effort: AA Intelligence Index v4.3.2 (measured)

The index runs agentic tasks in AA's Stirrup harness and Terminal-Bench 4.0 in mini-swe-agent, not Codex ([methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking)). AA estimates the index's 95% CI at under ±1 point; individual evaluations are wider. Data from [AA model pages](https://artificialanalysis.ai/models/gpt-6-1-sol), fetched 2026-10-06.

| Model | Effort | Index | TB 4.0 % | AA-LCR % | GDP.pdf % | AutoBench % | HLE % | Halluc. % | Out tok/task (reasoning) | $/task | s/task |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Luna | none | 18.5 | 1.5 | 39.7 | – | 9.1 | 8.6 | – | 3.8K (0) | 0.01 | 30 |
| Luna | low | 21.5 | 0.0 | 74.0 | 9.0 | 12.0 | 20.3 | 84.3 | 2.1K (0.5K) | <0.01 | 15 |
| Luna | medium | 29.9 | 2.5 | 78.3 | 13.8 | 40.5 | 28.3 | 84.7 | 11.5K (6.3K) | 0.02 | – |
| Luna | high | 32.9 | 4.5 | 79.3 | 18.2 | 47.8 | 32.9 | 84.4 | 19.7K (12.7K) | 0.03 | 147 |
| Luna | xhigh | 34.6 | 8.1 | 80.0 | 18.6 | 47.8 | 34.3 | 82.4 | 27.5K (18.8K) | 0.04 | 196 |
| Luna | max | 38.1 | 12.6 | 83.3 | 22.8 | 53.2 | 38.5 | 76.7 | 50.0K (38.9K) | 0.07 | 339 |
| 6.1 Sol | low | 42.1 | 30.8 | 84.0 | 27.0 | 52.6 | 47.4 | 51.6 | 4.0K (1.2K) | 0.13 | 80 |
| 6.1 Sol | medium | 47.8 | 48.0 | 83.3 | 30.0 | 62.6 | 49.9 | 51.6 | 8.1K (2.9K) | 0.21 | 154 |
| 6.1 Sol | high | 50.2 | 51.5 | 82.3 | 32.0 | 64.5 | 51.4 | 49.4 | 13.2K (5.7K) | 0.32 | 249 |
| 6.1 Sol | xhigh | 51.0 | 54.0 | 79.7 | 31.8 | 66.6 | 52.6 | 50.9 | 17.6K (9.1K) | 0.39 | 307 |
| 6.1 Sol | max | 51.8 | 56.1 | 83.0 | 31.0 | 64.9 | 52.9 | 54.3 | 38.1K (25.2K) | 0.72 | 651 |
| Astra | low | 45.8 | 41.9 | 80.0 | 30.4 | 59.1 | 49.2 | 46.9 | 4.4K (0.9K) | 0.82 | 77 |
| Astra | medium | 49.6 | 49.5 | 79.7 | 30.4 | 64.6 | 52.7 | 46.5 | 9.6K (3.4K) | 1.54 | 180 |
| Astra | high | 50.9 | 54.0 | 80.0 | 31.0 | 66.6 | 53.1 | 44.8 | 11.8K (4.7K) | 1.73 | 196 |
| Astra | xhigh | 52.4 | 59.6 | 80.0 | 32.2 | 67.2 | 54.6 | 48.3 | 16.9K (8.6K) | 2.31 | 268 |
| Astra | max | 52.7 | 59.1 | 80.7 | 31.0 | 68.5 | 54.7 | 51.3 | 27.2K (16.7K) | 3.26 | 425 |
| 6 Sol | medium / max | 39.8 / 47.6 | 18.7 / 43.9 | 82.3 / 83.7 | – | 58.0 / 61.6 | 41.0 / 47.9 | – | 6.5K / 31.0K | 0.25 / 1.04 | – / 285 |
| Opus 5.5 | low / medium / high / xhigh / max | 42.3 / 51.2 / 53.6 / 56.0 / 57.6 | 31.3 / 52.5 / 56.6 / 59.6 / 59.6 | 80.7 / 84.3 / 82.7 / 84.7 / 84.7 | – | 52.9 / 61.2 / 63.2 / 65.0 / 69.5 | 48.3 / 54.7 / 55.6 / 57.5 / 61.4 | – | 10.2K / 25.7K / 35.6K / 65.7K / 119K | 0.55 / 1.34 / 1.82 / 3.46 / 5.98 | 81–793 |
| Sonnet 5.5 | low / medium / high / xhigh / max | 35.9 / 40.8 / 46.8 / 51.9 / 56.0 | 20.7 / 29.8 / 43.9 / 57.1 / 63.6 | 76.0 / 76.3 / 78.0 / 79.7 / 82.7 | – | 49.4 / 54.9 / 59.4 / 65.5 / 71.8 | 36.2 / 39.8 / 45.8 / 50.0 / 55.0 | – | 14.3K / 20.9K / 37.3K / 74.8K / 197K | 0.42 / 0.59 / 1.12 / 2.75 / 7.67 | 90–979 |

Definitions:
- **AA-LCR:** reasoning across multiple ~100K-token documents.
- **GDP.pdf:** the share of answers about long professional PDFs that meet every criterion.
- **Halluc.:** the AA-Omniscience hallucination rate. The benchmark rewards abstaining over guessing wrong ([methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking)).
- **Claude rows:** run with Anthropic's default fallback enabled.

---

## 2. Effort-versus-performance curves

### 2.1 GPT-6.1 Sol in the Codex harness (measured, [AA](https://artificialanalysis.ai/agents/coding-agents))

| Effort | Index | Δ vs medium | Credits/task (§4.1) | × medium Quota | Output tokens × medium | Input tokens × medium | Wall time × medium |
|---|---|---|---|---|---|---|---|
| low | 57.2 | −4.2 | 11.3 | 0.71 | 0.66 | 0.75 | 0.80 |
| **medium** | **61.4** | 0 | **16.0** | 1.00 | 1.00 | 1.00 | 1.00 (651 s) |
| high | 60.1 | −1.3 | 20.1 | 1.26 | 1.28 | 1.23 | 1.23 |
| xhigh | 62.9 | +1.5 | 23.5 | 1.47 | 1.58 | 1.40 | 1.43 |
| max | 60.1 | −1.3 | 34.6 | 2.16 | 2.75 | 1.73 | 2.25 |

What the table shows:
- **Steps per task stay at 36–40 across all efforts.** Higher effort means more thinking per step, not more steps.
- **The differences between medium, high and xhigh are within benchmark noise** (inference). Terminal-Bench alone shows ±2.7–3.0 pp 95% CIs at 330 trials ([tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0)); AA ran 198–372 attempts per benchmark.
- **Max does worse than xhigh in two separate measurements.** AA saw a −2.8 point gap ([AA 6.1 Sol](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)). OpenAI's per-effort DeepSWE chart (secondary transcription) shows max 71 against high 75.

### 2.2 GPT-6 Astra in the Codex harness, Terminal-Bench 4.0 (measured, [tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0))

| Effort | Accuracy | Δ vs medium | $/trial (× medium) | Output tokens (× medium) | Time (× medium) |
|---|---|---|---|---|---|
| low | 50.6 | −3.6 | 4.72 (0.81) | 24.2K (0.74) | 0.89 |
| medium | 54.2 | 0 | 5.80 (1.00) | 32.6K (1.00) | 1.00 (31 min) |
| **high** | **57.9** | +3.6 | 6.88 (1.19) | 41.5K (1.27) | 1.12 |
| xhigh | 57.9 | +3.6 | 7.12 (1.23) | 45.3K (1.39) | 1.17 |
| max | 58.2 | +3.9 | 9.90 (1.71) | 72.7K (2.23) | 1.48 |

### 2.3 Which task types gain from effort (measured, AA Intelligence Index, §1.3)

| Task type (benchmark) | Luna low→high | Sol low→medium→xhigh | Astra low→high | Reading |
|---|---|---|---|---|
| Long-document Q&A (AA-LCR) | 74→79 | 84→83→80 | 80→80 | **Flat. Low or medium is enough**; Luna at medium is within ~5 pp of Sol |
| Short self-contained code (SciCode) | 47→50 | 53→53→56 | 54→55 | **Flat** |
| Codebase Q&A in Codex (SWE-Atlas-QnA) | – | 55→61→61 | – | **Medium is enough** |
| Multi-step tool workflows (AutomationBench) | **12→48** | 53→63→67 | 59→67 | Luna needs ≥ medium; Sol gains +4 pp from medium to xhigh |
| Long terminal tasks (TB 4.0, mini-swe-agent) | 0→4.5 | 31→48→54 | 42→54 | **Effort pays.** In Codex the spread is smaller (Sol 49→55) |
| Knowledge-work deliverables (GDPval Elo) | 1036→1344 | 1297→1433→1510 | 1366→1485 | Effort pays, monotonically |
| Hard science reasoning (HLE, CritPt) | 20→33 | 47→50→53 | 49→53 | Effort pays modestly |

Supporting results:
- **More effort is not more accuracy without limit.** Across eight frontier models on SWE-bench Verified, "accuracy often peaks at intermediate cost and saturates at higher costs", and "runs on the same task can differ by up to 30x in total tokens" ([arXiv 2604.22750](https://arxiv.org/abs/2604.22750), v3 2026-10-02; models tested include GPT-5 and Claude Sonnet 4.5, so this is older evidence).
- **Anthropic reports the same saturation for its own models.** Opus 5.5 at medium beats Opus 5 at max on Terminal-Bench 4.0, and customers report low effort matching higher settings on some knowledge work ([Anthropic](https://www.anthropic.com/news/claude-opus-5-5); vendor claim).
- **Retrying can beat raising effort when a Check exists.** On Terminal-Bench, Astra's pass@5 at low (63.6%) beats its pass@1 at max (58.2%) ([tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0)). Five low attempts cost 2.4× one max attempt, so this pays only when a Check can select the passing run (inference).

---

## 3. OpenAI's guidance on model and effort

| Topic | OpenAI's words | Source |
|---|---|---|
| Model roles | Astra "for the hardest end-to-end work". 6.1 Sol "for repeated, long-running work… when cost matters". Luna "for specific, high-volume tasks when you know what a good result looks like, such as extraction, classification, transformation, and structured summaries" | [Codex models](https://learn.chatgpt.com/docs/models) |
| Codex default model | "For complex coding and agentic workflows, use GPT-6.1 Sol… Use Luna for focused, repeatable tasks" | same |
| Starting effort | "Start with **High** for Luna or **Light** for Astra… Astra's Light setting is `low`." For 6.1 Sol, "start with the reasoning effort available by default in your client" | same; [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| What each level is for | Light/Low "suits quick, well-scoped tasks". Medium "balances speed and depth for tasks that need more planning". High and Extra High "suit difficult work with multiple steps, sources, or tradeoffs". "Most tasks do not need Max or Ultra" | [Codex models](https://learn.chatgpt.com/docs/models) |
| Subagent effort | `high` "when an agent needs to trace complex logic, check assumptions, or work through edge cases (for example, reviewer or security-focused agents)"; `low` "when the task is straightforward and speed matters most" | [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| API effort table | `medium` is the "well-balanced point on the pareto curve". `high`: "evaluate both `medium` and `high`". `xhigh`: "Only use when your evals show a clear benefit that justifies the extra latency and cost" | [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) |
| Model × effort pairs | Luna·Low: "Fine-grained edits, well-scoped problem-solving, and simple data extraction". Luna·Extra high: "solving problems with clear constraints". 6.1 Sol·Medium: "Complex technical work". 6.1 Sol·Extra high: "decisions built from conflicting evidence". Astra·Low: "Concise writing". Astra·Extra high: "Demanding analysis" | [model selection](https://developers.openai.com/api/docs/guides/model-selection) |
| GPT-6 family guide | Low for "extracting facts or making small edits"; Medium for "planning a feature"; High for "Difficult debugging… careful review"; xhigh/max "when High falls short, and keep only if the improvement justifies the added time and cost" | [OpenAI guide, 2026-10-02](https://openai.com/index/practical-guide-building-gpt-6/) (via reader) |
| ChatGPT presets | The six Power presets are Luna High, GPT-6 Sol Light, GPT-6 Sol Medium, Astra Light, Astra Medium and Astra Extra High. **No preset runs Luna below High** | [Codex models](https://learn.chatgpt.com/docs/models) |

**Why does Codex default Sol and Astra to `low`?** OpenAI publishes no rationale. The changelog and model pages state the default but not the reason ([changelog](https://learn.chatgpt.com/docs/changelog), local `codex debug models`). The evidence is consistent with four explanations (all inference):
1. **Interactive latency.** Sol at low takes about 0.8× the wall time of medium in Codex (§2.1).
2. **The Codex harness narrows the low-effort penalty.** Sol at low loses 4 index points against medium in Codex, but 17 pp on Terminal-Bench in mini-swe-agent (§1.3).
3. **Low and medium are Pareto-optimal for token efficiency** on 6.1 Sol ([AA](https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence)).
4. **The models "reason adaptively across reasoning efforts"** ([reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)).

The default is a client choice, not a statement about quality: the API defaults the same Sol to `medium`.

---

## 4. Token efficiency and Plus Quota

### 4.1 Converting tokens to Quota

**Credits are 25× API dollars.** Every Codex credit rate equals 25 × the API price per token. Luna is $0.10 → 2.5, Sol $2 → 50, Astra $10 → 250; cached input Luna $0.01 → 0.25, Sol $0.10 → 2.5, Astra $1 → 25; output ×25 likewise ([Codex pricing](https://learn.chatgpt.com/docs/pricing), [API model pages](https://developers.openai.com/api/docs/models/gpt-6-astra)). The difference is that Codex has "no separate cache-write charge". Consequently, **credits per task ≈ 25 × AA's $/task.**

**Credits are a proxy for Quota, not a measure of it.** OpenAI says "Credit prices alone don't determine included subscription usage" (same source), and the Plus 5-hour credit budget is not published.

**Relative rates per token:**
- Uncached input and output: Luna : Sol : Astra = **1 : 20 : 100**.
- Cached input: **1 : 10 : 100**, because Sol's cache discount is 95% against 90% for the others.

**Plus message ranges imply Astra is cheaper per message than its token price.** Sol allows about 3–3.6× more messages than Astra (15–160 vs 5–45), not 5×. That suggests OpenAI assumes Astra spends fewer tokens per message (inference).

### 4.2 Credits per task, derived from measured tokens

| Contestant (model × harness × effort) | Credits/task | × Sol medium | Split: uncached in / cached in / output | Source of tokens |
|---|---|---|---|---|
| Luna max, Codex | 4.3 | 0.27 | 0.6 / 2.5 / 1.2 | [AA](https://artificialanalysis.ai/agents/coding-agents) |
| 6.1 Sol low, Codex | 11.3 | 0.71 | 3.6 / 4.1 / 3.7 | same |
| **6.1 Sol medium, Codex** | **16.0** | 1.00 | 5.0 / 5.4 / 5.6 | same |
| 6.1 Sol high, Codex | 20.1 | 1.26 | 6.3 / 6.7 / 7.2 | same |
| 6.1 Sol xhigh, Codex | 23.5 | 1.47 | 7.1 / 7.6 / 8.9 | same |
| 6.1 Sol max, Codex | 34.6 | 2.16 | 9.9 / 9.4 / 15.4 | same |
| 6 Sol max, Codex | 72.5 | 4.5 | 9.0 / 48.0 / 15.5 | same |
| 5.6 Sol max, Codex | 156 | 9.8 | 33.7 / 97.8 / 24.6 | same |
| **Astra max, Codex** | **177** | **11.0** | 39.5 / 78.5 / 58.8 | same |
| Astra low / medium / high / xhigh / max, Codex, Terminal-Bench only | 118 / 145 / 172 / 178 / 248 | – (different task mix) | – | [tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/4.0) ($ × 25) |
| Intelligence Index tasks (Stirrup / mini-swe-agent): Luna high 0.8, Sol medium 5.3, Astra high 43 | – | Luna high ≈ 0.14, Astra high ≈ 8.2 | – | [AA models](https://artificialanalysis.ai/models/gpt-6-1-sol) |

How to read this:
- **One Astra max SWE-style task spends the Quota of about 11 Sol-medium tasks or about 40 Luna-max tasks.**
- **Sol at high uses about 1.3× the tokens of Sol at medium on SWE-style tasks.** On DeepSWE alone, output tokens are 31.2K against 23.0K (1.36×) and input tokens 2.38M against 1.88M (1.27×). In the non-Codex Intelligence Index the ratio is 1.63×.
- **Sol at xhigh uses about 1.5–2.2× medium, and max about 2.2–4.7×.**
- **Per-task spread is wide.** Sol medium ranges from $0.22 at p05 to $1.47 at p95 per task, about 5–37 credits ([AA](https://artificialanalysis.ai/agents/coding-agents)).
- **Input re-reads are a third or more of Sol's Quota.** Cached tokens are counted in millions per hard task. That fits the finding that "input tokens rather than output tokens [drive] the overall cost" ([arXiv 2604.22750](https://arxiv.org/abs/2604.22750)).
- **Luna is not proportionally cheaper in Codex on hard tasks.** It takes about 89 steps per hard task against about 38 for Sol, and 10M+ input tokens (§1.1). So Luna at max is only about 3.7× cheaper than Sol medium, not 20×.
- **Contract detail reduces token use.** A bare user story instead of a full spec raised token spend 29.7% across 2,700 runs ([arXiv 2608.25399](https://arxiv.org/abs/2608.25399); tested on Kimi K3, so transfer to GPT-6 is inference).

**Fast mode** draws Quota at 2.5× ([speed](https://learn.chatgpt.com/docs/agent-configuration/speed)). The live catalog has `default_service_tier: null` for all GPT-6 models (local `codex debug models`). The `main`-branch `models.json` sets `"priority"` for Luna and 6 Sol, but `codex exec` passes `service_tier: None` ([exec source](https://github.com/openai/codex/blob/main/codex-rs/exec/src/lib.rs)). Delegations therefore run Standard unless `service_tier` is configured. That conclusion comes from reading source on `main`, not from 0.159.2 (unverified).

---

## 5. Known weaknesses and behaviours that matter for unattended Delegation

| Model | Behaviour | Evidence strength and source | Implication for the Contract or wrapper |
|---|---|---|---|
| Astra | "more likely to ask for clarification where earlier models would make assumptions"; can "stop when the user may expect it to… persist" | Vendor ([GPT-6 guide](https://developers.openai.com/api/docs/guides/latest-model)) | Nobody answers in `codex exec`, so add the initiative line and an explicit definition of done. Codex's own base instructions already include an "Autonomy and persistence" section (local `codex debug models`) |
| Astra | "may reach a first implementation and come back for your review while there's still work to do"; "Guidance that helps Sol or Luna may overconstrain GPT-6 Astra" | Vendor ([OpenAI blog](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)) | State the Checks the Delegate must run and fix before returning `done` |
| Astra | More sensitive to AGENTS.md and skill conflicts; "may cause the model to pause and block work early" | Vendor ([GPT-6 guide](https://developers.openai.com/api/docs/guides/latest-model)) | Keep AGENTS.md and the Contract consistent. Ask the Delegate to quote any instruction that made it stop |
| Astra | Tests more broadly than small tasks need | Vendor (same) | Bound the testing in the Contract. Inference: this may also cost it on DeepSWE, whose verifier fails when agent-written tests reference removed files ([Epoch](https://epoch.ai/benchmarks/deepswe/review)) |
| Astra | Lowest measured coding misrepresentation (0.51%) and unwanted persistence past warnings (17.4%); "still sometimes overreaches… using privileged access without clear approval" | Vendor adversarial evals ([6.1 Sol card](https://deploymentsafety.openai.com/gpt-6-1-sol), [Astra card](https://deploymentsafety.openai.com/gpt-6-astra)) | The sandbox stays the control; do not rely on the model's judgement |
| 6.1 Sol | Misrepresentation 1.50% (≈3× Astra); unwanted persistence 23.5%; fails to acknowledge a broken search tool 2.08%; engages with other agents' messages 38% (unauthorized action 3%) | Vendor adversarial evals ([6.1 Sol card](https://deploymentsafety.openai.com/gpt-6-1-sol)) | Treat a Result of `done` as a claim. Rerun Checks independently, as the Contract model already requires |
| 6.1 Sol | Reports of high-effort self-verification regressions, 12-hour repair loops at high, "Selected model is at capacity" on Plus with quota left, early compaction | **User reports, unverified** ([#49828](https://github.com/openai/codex/issues/49828), [#50267](https://github.com/openai/codex/issues/50267), [#50252](https://github.com/openai/codex/issues/50252), [#49961](https://github.com/openai/codex/issues/49961)) | Use a wall-clock `timeout`; treat a capacity error as retryable, not as `blocked` |
| Luna | Weak at long agentic tasks: TB 4.0 ≤15% at any effort; 89 steps per hard task; codebase Q&A 44% | Measured ([AA](https://artificialanalysis.ai/agents/coding-agents), [Vals](https://www.vals.ai/benchmarks/terminal-bench-4)) | Only short, Check-verified Delegations |
| Luna | Collapses at low effort in multi-step tool use (AutomationBench 12%) | Measured ([AA](https://artificialanalysis.ai/models/gpt-6-luna)) | Never run Luna at `low` in Codex |
| Luna | Guesses instead of abstaining (hallucination rate 77–85%); weak on full-criteria PDF reasoning (GDP.pdf ≤23%) | Measured (same) | Require quotes with file and line references so Opus can spot-check |
| Luna | "broader tendency to refuse requests, including legitimate ones"; found the planted message board in only 76% of runs (others ≥96%); "attempted to bypass the [Auto-review] monitor but never succeeded" | Vendor ([6.1 Sol card](https://deploymentsafety.openai.com/gpt-6-1-sol), [Astra card appendix](https://deploymentsafety.openai.com/gpt-6-astra)) | Expect some spurious refusals and shallower exploration. Keep the sandbox strict |
| Sol, Luna | Shorter answers at default verbosity (HealthBench answer length −45% Sol, −35% Luna); GDPval regressions "driven by… deliverables that omit rubric elements" | Vendor ([Astra card appendix](https://deploymentsafety.openai.com/gpt-6-astra)); measured ([AA](https://artificialanalysis.ai/articles/gpt-6-sol-and-luna-push-the-cost-efficiency-frontier)) | Enumerate the required Result fields in `--output-schema` |
| All GPT-6 | False "Invalid prompt" safety flags on benign prompts | **User reports, unverified** ([#48817](https://github.com/openai/codex/issues/48817), [#50605](https://github.com/openai/codex/issues/50605)) | Treat as an error, retry once, then report `blocked` |
| All (ChatGPT sign-in) | Requested Astra served as GPT-5.6 Luna; reasoning tokens collapsing per turn; "Selected model is at capacity" errors | **User reports, unverified** ([#46632](https://github.com/openai/codex/issues/46632), [#50893](https://github.com/openai/codex/issues/50893)) | Record requested vs realized settings in the Run record (see Gaps) |

---

## Proposed Model notes

Dated **2026-10-06**. Read alongside the live catalog (`codex debug models`). Relative Quota is per task, with 6.1 Sol at medium = 1 (about 16 credits on a hard coding task).

| Model | Default effort | Raise or lower when | Best uses | Avoid for | Relative Quota | Evidence |
|---|---|---|---|---|---|---|
| `gpt-6.1-sol` | **medium** | **Raise to xhigh, not high,** for long terminal or multi-step jobs, or after a medium attempt fails its Checks: +1–3 pp for 1.5× Quota and 1.4× time. **High for Second opinions** (OpenAI's reviewer advice; no benchmark either way). **Lower to low** for small, fully specified edits with a Check: −4 pp on hard tasks, 0.7× Quota. **Never max**: it scores below xhigh at 2.2× Quota | The default Delegate: coding, debugging, codebase investigations, Second opinions, long-document reading (low is enough there) | No systematic weakness measured. Expect occasional overclaimed success, so rerun Checks | low 0.7 · medium 1 · high 1.3 · xhigh 1.5 · max 2.2 | **Measured** (AA Codex index, 303 tasks × 3) + **vendor** guidance |
| `gpt-6-luna` | **high** in a tool loop; **medium** for read-only extraction or summarizing | **Max** only as a cheap retry (≈0.3× Quota, ≈2× Sol medium's wall time). **Never low** inside Codex (AutomationBench 12% at low) | Mechanical edits with a Check; extraction, classification and structured summaries that quote sources; triage lists that Opus spot-checks | Long or terminal-heavy coding (TB 4.0 ≤15%); debugging; investigations that need judgment (codebase Q&A 44% vs Sol low 55%); unverifiable factual summaries (hallucination rate 77–85%) | ≈0.1–0.3 | **Measured** (AA per effort; Codex at max only) + **vendor** ("Start with High for Luna") |
| `gpt-6-astra` | **high**, only with the user's permission | **Don't raise**: in Codex, high = xhigh (57.9) ≈ max (58.2) at +3% / +44% cost. Lower to medium (−3.6 pp, 0.84× cost) | Hardest science and maths reasoning; computer use; highest-stakes review where its lower misrepresentation rate (0.51% vs 1.50%) matters | Routine coding and ordinary Second opinions: Sol at xhigh ≥ Astra at max for <15% of the cost. Ambiguous Contracts (it asks questions and stops early). Fan-out (Plus allows 5–45 messages per 5 h) | ≈7–11 | **Measured** (tbench.ai Codex by effort; AA) + **vendor** (behaviour) |
| `gpt-6-sol`, `gpt-5.6-*` | Not used | – | – | Everything: 6.1 Sol scores higher at the same price as 6 Sol, or half the price of 5.6 Sol | 6 Sol max ≈4.5; 5.6 Sol max ≈9.8 | **Measured** (AA) |
| Any model | – | **`ultra` never**: it is xhigh plus automatic subagent delegation. **`max` never** on Sol or Astra. **`xhigh` needs a one-line reason** in the Contract | – | – | – | **Source code** + **measured** |

**Changes from the draft:**
- **Luna's default moves from medium to high in tool loops.** Medium stays for read-only work.
- **Sol escalates to xhigh instead of high for tricky bugs.** High remains only for Second opinions.
- **Max is ruled out for Sol and Astra.**
- **Astra's "hard problems" are narrowed to areas where it has a measured lead.** Coding is not one of them.

---

## Gaps

**What I could not find:**
1. **No SWE-bench Verified or SWE-bench Pro results for any GPT-6 model from benchmark maintainers.** Scale's SWE-bench Pro leaderboard stops at GPT-5.4 and Muse Spark 1.1 ([Scale](https://scale.com/leaderboard/swe_bench_pro_public)). swebench.com did not load. OpenAI reports DeepSWE instead, and Epoch rates DeepSWE v1.1 "Flawed" ([Epoch](https://epoch.ai/benchmarks/deepswe/review)). Datacurve stopped publishing DeepSWE results after 2026-09-03 ([deep-swe#102](https://github.com/datacurve-ai/deep-swe/issues/102)).
2. **The Aider and LiveCodeBench leaderboards were last updated in 2025**, so they have no GPT-6 entries ([Aider](https://aider.chat/docs/leaderboards/), [LiveCodeBench](https://livecodebench.github.io/leaderboard.html)).
3. **Per-effort coding-agent data are missing for Luna** (Codex: max only) **and for Astra outside Terminal-Bench.** Terminal-Bench has no Codex 6.1 Sol rows yet.
4. **No benchmark measures review or Second-opinion quality, or Contract and output-schema adherence, per model and effort.**
5. **The Plus 5-hour budget in credits is not published**, and OpenAI does not say that credits map linearly to Quota.
6. **No published rationale** for Codex's `low` default on Sol and Astra, and no documented API default effort for Astra.
7. **AA ran Codex with API keys.** ChatGPT-auth routing (substitution, capacity errors, cache behaviour) may differ; the reports are unverified.
8. **Several numbers are secondary or unverified:** the per-effort DeepSWE values for 6.1 Sol, the 75.2%@high figure, and Opus 5.5's 64.8% at max.

**What our own test cases should measure** (using the benchmark suite's terms: a Contestant is model × Harness × Effort level, scored by Checkers):
1. **Quota per Delegation.** Run `codex exec` without `--ephemeral`. Read `rate_limits.primary.used_percent` (300-minute window) and `secondary` (weekly) before and after from the session rollout, together with `token_usage_record` usage. These fields exist in local rollouts under `~/.codex/sessions`. This gives "% of the 5-hour window per credit" for Plus.
2. **Sol low, medium, high and xhigh on our own Bugfix and Feature tasks** with hidden-test Checkers (≥20 tasks × 3 Trials). The goal is to confirm that high ≈ medium and that xhigh pays only on long tasks.
3. **Luna medium and high against Sol low on mechanical edits** (cross-file renames, signature changes, lint fixes), measuring pass rate, steps, wall time and Quota.
4. **Read-only investigation.** Luna medium against Sol low and medium on planted-fact repository Q&A with mandatory citations, measuring unsupported claims and abstentions.
5. **Second opinions on planted-bug reviews.** Sol medium, high and xhigh against Astra high, measuring recall, precision and Quota.
6. **Unattended behaviour per model.** Rate of `blocked` Results and questions asked, early stops, `done` claims contradicted by Checks, and schema violations.
7. **Requested vs realized model and effort.** Rollouts record the requested `model` and `effort` in `turn_context` but not the served model. Flag Invalid Trials as the benchmark suite defines them (`CONTEXT.md` of the user's local, unpublished benchmarks project). Use `RUST_LOG=trace` response frames, as in [#46632](https://github.com/openai/codex/issues/46632), or reasoning-token signatures.
8. **Retry against escalation.** Compare two Sol-medium attempts selected by a Check with one Sol-xhigh attempt.
9. **Wall time per effort**, since Delegations block the Orchestrator.

---

## Sources

**OpenAI documentation (fetched 2026-10-06)**
- Codex models: https://learn.chatgpt.com/docs/models (Markdown version: https://learn.chatgpt.com/docs/models.md)
- Codex pricing and credit rates: https://learn.chatgpt.com/docs/pricing
- Speed / Fast mode: https://learn.chatgpt.com/docs/agent-configuration/speed
- Subagents (model and effort choice): https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex changelog: https://learn.chatgpt.com/docs/changelog
- Using GPT-6: https://developers.openai.com/api/docs/guides/latest-model
- Model selection: https://developers.openai.com/api/docs/guides/model-selection
- Reasoning guide: https://developers.openai.com/api/docs/guides/reasoning
- Model pages: https://developers.openai.com/api/docs/models/gpt-6.1-sol, https://developers.openai.com/api/docs/models/gpt-6-astra, https://developers.openai.com/api/docs/models/gpt-6-luna, https://developers.openai.com/api/docs/models/gpt-6-sol
- Rethinking skills and prompts for GPT-6 Astra: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra

**OpenAI launch posts and system cards**
- GPT-6 Astra (2026-09-03, via reader): https://openai.com/index/gpt-6-astra/
- GPT-6 Sol and Luna (2026-09-22, via reader): https://openai.com/index/introducing-gpt-6-sol-and-luna/
- GPT-6.1 Sol (2026-09-29, via reader): https://openai.com/index/introducing-gpt-6-1-sol/
- A model guide for the GPT-6 family (2026-10-02, via reader): https://openai.com/index/practical-guide-building-gpt-6/
- Better prompt caching for GPT-6 (via reader): https://openai.com/index/better-prompt-caching-for-gpt-6/
- GPT-6 Astra system card, with the 6 Sol / Luna appendix: https://deploymentsafety.openai.com/gpt-6-astra
- GPT-6.1 Sol system card addendum: https://deploymentsafety.openai.com/gpt-6-1-sol
- @OpenAIDevs post on DeepSWE (search snippet only, unverified): https://x.com/OpenAIDevs/status/2104993067942219873

**Codex source and issues**
- Bundled model catalog: https://github.com/openai/codex/blob/main/codex-rs/models-manager/models.json
- Ultra effort resolution: https://github.com/openai/codex/blob/main/codex-rs/protocol/src/openai_models/reasoning_effort.rs
- `codex exec` service tier: https://github.com/openai/codex/blob/main/codex-rs/exec/src/lib.rs; TUI tier resolution: https://github.com/openai/codex/blob/main/codex-rs/tui/src/service_tier_resolution.rs
- Issues (user reports): #46632, #48817, #49828, #49961, #50252, #50267, #50605, #50893 at https://github.com/openai/codex/issues

**Benchmarks and evaluators**
- Artificial Analysis articles: https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra, https://artificialanalysis.ai/articles/gpt-6-sol-and-luna-push-the-cost-efficiency-frontier, https://artificialanalysis.ai/articles/gpt-6-1-sol-replaces-gpt-6-sol-after-just-7-days-with-near-astra-intelligence, https://artificialanalysis.ai/articles/claude-opus-5-5, https://artificialanalysis.ai/articles/claude-sonnet-5-5
- Artificial Analysis data pages: https://artificialanalysis.ai/models/gpt-6-1-sol (also /gpt-6-astra, /gpt-6-luna, /gpt-6-sol), https://artificialanalysis.ai/agents/coding-agents, https://artificialanalysis.ai/methodology/intelligence-benchmarking
- Terminal-Bench 4.0 official leaderboard: https://www.tbench.ai/leaderboard/terminal-bench/4.0
- Vals AI: https://www.vals.ai/benchmarks/terminal-bench-4, https://www.vals.ai/models/openai_gpt-6.1-sol
- Scale SWE-bench Pro (stale): https://scale.com/leaderboard/swe_bench_pro_public
- Epoch review of DeepSWE v1.1: https://epoch.ai/benchmarks/deepswe/review
- DeepSWE repository and issues: https://github.com/datacurve-ai/deep-swe (#102, #104)
- Aider (stale): https://aider.chat/docs/leaderboards/; LiveCodeBench (stale): https://livecodebench.github.io/leaderboard.html

**Anthropic**
- Claude Opus 5.5 announcement (2026-09-22): https://www.anthropic.com/news/claude-opus-5-5

**Papers**
- Token consumption in agentic coding: https://arxiv.org/abs/2604.22750
- Task specification and token spend: https://arxiv.org/abs/2608.25399

**Local evidence (2026-10-06)**
- `codex debug models` (CLI 0.159.2, ChatGPT Plus): defaults, `multi_agent_reasoning_effort`, `default_service_tier`, `default_verbosity`, context window
- Rollout fields in `~/.codex/sessions/*.jsonl`: `turn_context`, `token_usage_record`, `rate_limits`
- /home/dev/projects/benchmarks/CONTEXT.md and /home/dev/projects/benchmarks/docs/research/2026-09-30-harness-and-framework-facts.md (Contestant and Invalid Trial definitions; "Quota is opaque"; effort and model substitution risks)
- [multi-model-orchestration.md](multi-model-orchestration.md) §5 (prices, Plus ranges)
