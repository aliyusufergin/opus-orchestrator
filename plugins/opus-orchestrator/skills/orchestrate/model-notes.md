---
date: 2026-10-06
---

# Model notes

What each OpenAI model is good for, what it costs in Quota and which reasoning effort to give it. Read them alongside Codex's live catalog, which `start-run` lists. The catalog says which models exist; these notes say when to use them. The evidence is in the plugin repository's model-routing research note, `docs/research/openai-model-routing-data.md`.

The `date` above is when the notes were last checked. `start-run` warns when it is more than 30 days old, or when the catalog lists a model that has no row here.

| Model | Default effort | Change when | Use for | Avoid for | Relative Quota per task (6.1 Sol at medium = 1) |
|---|---|---|---|---|---|
| `gpt-6.1-sol` | medium | **xhigh, not high,** for long multi-step work or after a failed Check. **High** for Second opinions. **Low** for small, fully specified edits that have a Check | The default Delegate: coding, debugging, investigations, Second opinions, long-document reading (low is enough there) | — | low 0.7 · medium 1 · high 1.3 · xhigh 1.5 |
| `gpt-6-luna` | **high** in a tool loop; medium for read-only extraction or summaries | Never low | Mechanical edits that have a Check; extraction, classification, summaries that quote their sources | Agentic coding, debugging, investigations that need judgement, unverifiable summaries | ≈0.1–0.3 |
| `gpt-6-astra` | high, and only with the user's permission | Don't raise it (high ≈ max) | Hardest reasoning; highest-stakes review | Routine coding, ordinary Second opinions, ambiguous Contracts, fan-out | ≈7–11 |
| `gpt-6-sol`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` | Not used | — | — | Everything: 6.1 Sol scores higher for the same Quota or less | — |
| All models | — | `ultra` never; `max` never on Sol or Astra; `xhigh` needs a one-line reason | — | — | — |

The wrapper refuses `ultra`, because it adds automatic subagent delegation, and any model or effort missing from the live catalog.
