# Leave the method free, make the interface explicit, enforce invariants in code

Current Claude and OpenAI guidance, and the evidence in [instruction-design research](../research/instruction-design-for-frontier-models.md), agree that prescriptive skills degrade capable models, that compliance falls as instructions and context grow, that conflicting guidance stalls GPT-6-class delegates, and that prose is advisory. So the mechanism has three layers, each with its own degree of prescription:

- **Opus's judgment is short, explanatory prose.** Whether, what and how to delegate, which model, and how hard to check are rules of thumb with their reasons, in a skill of roughly 80–200 lines. It has no step-by-step recipes, no emphatic MUST/CRITICAL wording and no generic self-verification instructions.
- **The interface between Opus and a delegate is explicit.** Every task handed over states its goal, the context the delegate cannot infer, success criteria, scope, output and stop rules. Every result conforms to a JSON schema whose status is `done`, `partial` or `blocked`, so a delegate is never forced to claim success.
- **Invariants live in a wrapper script, not in prose.** Model and reasoning effort are always pinned, Codex's own subagents and its `ultra` effort are off, stdin is closed, a timeout applies, delegates are read-only unless the task grants writes, token usage is logged, and the result arrives as a file.

Instructions are added only to close a gap that a test case shows against a no-skill baseline, and are pruned whenever either side ships a new model.

## Considered Options

- A comprehensive procedural skill, as in the sibling codex-orchestration project (a 1,571-word skill, about 6,600 words of references and a 1,528-line spawn audit): rejected because its length and rule count work against the models it steers, and most of its issues went to maintaining the procedure rather than to outcomes.
- Minimal prose with nothing enforced: rejected because pinning, sandboxing, timeouts and result shape must hold whatever the model decides.

## Consequences

Every new rule has to name its layer. A rule that must always hold goes into the script or a hook. A rule in prose is a heuristic Opus may override with a reason.
