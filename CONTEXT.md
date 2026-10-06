# Opus Orchestrator

A Claude Opus session, started by the user for a task, hands bounded pieces of the work to OpenAI models and stays responsible for the outcome: it decides, integrates, checks and reports.

## Language

### Sessions

**Orchestrator**:
The Opus session that carries out a Run and holds every decision in it.
_Avoid_: Parent, lead, root agent

**Run**:
One use of the orchestrator that the user starts for a task, from the invocation to the final report.
_Avoid_: session

**Delegate**:
An OpenAI model session carrying out one Delegation.
_Avoid_: worker, child, subagent

**Subagent**:
A Claude Code subagent, always a Claude model. The Orchestrator may use subagents as it normally would; they are not Delegates.

### Delegation

**Delegation**:
One piece of work handed to one Delegate under one Contract.
_Avoid_: subagent, job, dispatch

**Contract**:
The text a Delegate receives for a Delegation: a fixed part common to every Delegation, and a task part the Orchestrator writes stating the goal, the context the Delegate cannot infer, success criteria, Write scope, Checks and stop rules.
_Avoid_: brief, handoff, prompt

**Write scope**:
The paths a Delegation may change; `none` makes it read-only.
_Avoid_: allowed paths, file ownership

**Snapshot**:
The state of the working tree, uncommitted and untracked files included, from which a writing Delegation starts and against which its changes are measured.
_Avoid_: base commit, starting revision

**Check**:
A command named in a Contract whose exit code shows whether a success criterion holds. It is run again independently of what the Delegate claims.
_Avoid_: validation, test (too narrow)

**Result**:
What a Delegate returns, in the shape its Contract fixes, with a status of done, partial or blocked.
_Avoid_: output, report, verdict

**Second opinion**:
A read-only Delegation that critiques the Orchestrator's own plan or change.
_Avoid_: review gate, debate, verdict

**Finding**:
A problem a Result reports, which the Orchestrator treats as a hypothesis to reproduce before acting on it.
_Avoid_: issue, comment, verdict

**Run record**:
The Contracts, Results, events and token usage of one Run, kept outside version control.
_Avoid_: log, audit

### Cost and routing

**Quota**:
The share of a subscription's rolling usage limits (the five-hour and weekly windows) that work uses up. A Run spends Claude Quota and ChatGPT Quota.
_Avoid_: cost (too broad), budget, usage limit, credits

**Model notes**:
The dated record of each OpenAI model's relative Quota cost and strengths, read alongside the live model catalog.
_Avoid_: model table, routing table, capability snapshot

## Relationships

- The **Orchestrator** starts every **Delegation**; each **Delegation** has exactly one **Delegate** and one **Contract**.
- A **Delegate** may change only its **Write scope** and never commits; the **Orchestrator** integrates and is the only committer, and commits only when the user asks.
- A writing **Delegation** starts from a **Snapshot**; its changes come back as a diff against that **Snapshot**, and its **Checks** are run again before the **Orchestrator** accepts them.
- A **Result** with status blocked hands a decision back to the **Orchestrator**; a **Delegate** never asks the user.
- A **Second opinion** returns **Findings**, never a decision; the **Orchestrator** reproduces a **Finding** before acting on it.
- A **Run** spends **Quota** on both sides: the **Orchestrator**'s own work spends Claude Quota, every **Delegation** spends ChatGPT Quota.
- Every **Delegation** in a **Run** leaves its **Contract**, **Result** and token usage in the **Run record**.
