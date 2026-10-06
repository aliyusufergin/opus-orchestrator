# Second opinions are evidence, not gates

A Second opinion from an OpenAI model on the Orchestrator's own plan or change returns Findings that the Orchestrator reproduces before acting on them; it never blocks or approves anything, and the Orchestrator decides when to ask for one. The best available evidence is asymmetric: in one study, Claude reviewing GPT-written code raised pass rates from 71.6% to 89.7%, while GPT reviewing Claude-written code lowered them from 91.4% to 82.8% ([arXiv 2607.21656](https://arxiv.org/abs/2607.21656)), and errors across providers are correlated, so agreement is not proof. GPT-written changes are reviewed in the other direction, by the Orchestrator or a Claude Subagent.

## Considered Options

- A Stop-hook review gate, as in OpenAI's Claude Code plugin: rejected because it can veto on opinion, loops and drains Quota (the plugin's own README warns of this).
- An automatic Second opinion on every Orchestrator change: rejected for Quota and for the evidence above.
- Parallel panels or multi-round debate between models: rejected because majority voting explains most of debate's gains and mixing models can lower quality ([multi-model orchestration research](../research/multi-model-orchestration.md)).
