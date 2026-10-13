# Revision round

Test cases 1, 3 and 5 (`bug-fix`, `investigation`, `parallel-feature`) in the `skill` configuration, with the [orchestrate skill](../plugins/opus-orchestrator/skills/orchestrate/SKILL.md) as revised from the [skill round](skill-round.md)'s gaps, for issue #36. The runs are `skill` lines of [results.jsonl](../plugins/opus-orchestrator/test-cases/results.jsonl) recorded on 2026-10-13, compared with the [baseline round](baseline-round.md)'s `alone` and `pointer` runs. [docs/orchestrate-skill.md](orchestrate-skill.md) traces each revision to its gap.

The verdict follows the same rule as the skill round: at least as many tasks passed as both baselines, and less Claude Quota than Opus alone.

## Setup

As in the skill round: `--effort medium`, the two `n8n-custom-ytdlp` runs at the same time, then `parallel-feature` on its own, with nothing else running on the machine.

## First attempt: the first revision (not counted)

The first revision (commit `260fb88`) ran all three tasks. Its `parallel-feature` run can't be counted: the ChatGPT Quota ran out two minutes into both Delegations (`quota_exhausted`, "try again at 11:01 PM"), and Opus stopped and asked the user how to go on, as the skill says. The runner has no user, so the Run ended there.

| Task | Passed | Wall time | Claude turns | Claude tokens | Claude cost | Delegations |
| --- | --- | --- | --- | --- | --- | --- |
| bug-fix | yes | 114 s | 9 | 298K | $0.43 | none |
| investigation | yes¹ | 37 s | 6 | 186K | $0.37 | none |
| parallel-feature | no (not counted) | 258 s | 2 | 793K | $0.83 | 2, both `quota_exhausted` |

¹ Graded by Claude, as in the earlier rounds: the final message makes every point of the known answer except that the HEAD request is anonymous, like every earlier answer.

What it showed:

- **Gap 3 closed.** On `investigation`, Opus wrote "The whole answer is in one 370-line file … so handing it off would have cost more than reading it", and answered in 37 s, as `alone` did.
- **Gap 5 partly.** `bug-fix` skipped the `report` with no Delegations, but spent the turn on an end-to-end run of the updater instead: 9 turns, as before, and $0.43 against `alone`'s $0.33.
- **Gap 1 not closed.** Opus read the core code for under a minute (six commands), then wrote the core change itself, compiled it and delegated the core tests and the Android part. The widget change was the skill round's, line for line: `areQuestionMarksEnabled = preferences.areQuestionMarksEnabled` became `= true`, so a widget tap still moves on from the stored value. The check failed on the same acceptance test, `WidgetBehaviorTest.testOnToggleRepetition_onRestDay`, with the same `expected:<…value=2> but was:<…value=-1>`. The core-tests task part quoted the user's criteria but asked for cycles "starting from Unanswered", and named a Rest day only for the filter.

Defining an interface as a signature and its contract, and allowing the behaviour behind it to be "worked out properly" by Opus, didn't change what Opus did. In both failed runs, Opus wrote a behaviour change and a Delegate wrote its tests; in the passing `pointer` run, one Delegate wrote both against the user's criteria. The second revision says that: before the Delegations, Opus writes only what other parts must compile against, and a behaviour change and its tests go together, to one Delegation or to Opus.
