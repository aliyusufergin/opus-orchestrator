# Delegates contribute volume; the Orchestrator keeps decisions, integration and commits

The Run's main lever on Claude Quota is moving token-heavy work (reading, testing, iterating) to OpenAI models, so Delegations may write code. They take read-heavy investigation, self-contained implementation pieces with checkable acceptance criteria, mechanical high-volume work, and second opinions. The Orchestrator keeps every exchange with the user, every decision (decomposition, routing, architecture, interfaces), the Contracts, integration, acceptance and every commit. It also does tightly coupled or short work itself, because each Delegation carries about 13.7K tokens of Codex overhead plus the Orchestrator's own cost of writing the Contract and reading the Result. A writing Delegation gets its own worktree and a Write scope no concurrent Delegation shares.

## Considered Options

- Advice and review only (Amp's Oracle pattern, the best-evidenced one): rejected because it saves no Claude Quota.
- Read-only Delegations: rejected for the same reason on implementation-heavy tasks.
- Delegate all bounded work by default, as the sibling codex-orchestration project does: rejected because a cross-provider handoff costs far more than a native spawn.
- Parallel writers on one working tree: rejected because they overwrite each other and make conflicting implicit decisions.
