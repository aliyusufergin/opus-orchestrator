# Writing Delegations run in wrapper-made worktrees from a Snapshot, and the wrapper produces their evidence

Codex's own `--worktree` starts from `HEAD`, drops uncommitted and untracked changes, does not report its path in `--json` events, and is left behind after the run (local probe, Codex CLI 0.159.2). So the wrapper records a Snapshot of the working tree as an unreferenced commit, starts each writing Delegation in its own worktree from it with writes limited to that worktree, and afterwards takes the diff against the Snapshot, flags any change outside the Write scope, runs the Contract's Checks again itself, and removes the worktree. The Orchestrator reads that evidence, not the Delegate's claims, and applies the diff to the main working tree. Runs do not commit unless the user asks, since the Snapshot already gives Delegations a starting point independent of commits.

## Considered Options

- Codex `--worktree`: rejected for the reasons above, and because finding its path through `git worktree list` races with concurrent Delegations.
- Writing Delegations in sequence on the main working tree: rejected because it gives up parallel writes and lets a Delegate touch files outside its Write scope unseen.
- The Orchestrator commits every integrated piece, as the sibling codex-orchestration project does: rejected because commits stay the user's decision, as in Claude Code generally.

## Consequences

The Orchestrator applies a diff through the wrapper's `apply` command rather than with `git apply --3way` directly. A Snapshot usually holds uncommitted work, and plain `git apply --3way` refuses every file whose working tree differs from the index and stages what it applies into the user's index (local probe, Git 2.53). `apply` runs the three-way apply against a temporary index built from the working tree, so it works over uncommitted changes and leaves the user's index alone. Conflicts are left as conflict markers in the working tree and reported with exit code 3; a diff that doesn't apply changes nothing.
