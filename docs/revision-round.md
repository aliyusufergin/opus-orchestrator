# Revision round

Test cases 1, 3 and 5 (`bug-fix`, `investigation`, `parallel-feature`) in the `skill` configuration, with the [orchestrate skill](../plugins/opus-orchestrator/skills/orchestrate/SKILL.md) as revised from the [skill round](skill-round.md)'s gaps, for issue #36. The runs are `skill` lines of [results.jsonl](../plugins/opus-orchestrator/test-cases/results.jsonl) recorded on 2026-10-13, compared with the [baseline round](baseline-round.md)'s `alone` and `pointer` runs. [docs/orchestrate-skill.md](orchestrate-skill.md) traces each revision to its gap.

The verdict follows the same rule as the skill round: at least as many tasks passed as both baselines, and less Claude Quota than Opus alone.

**Verdict: not established.** The second revision (commit `61f6ada`) passed all three tasks, as both baselines did, with 45% fewer Claude tokens and 34% lower Claude cost than Opus alone. But its account of the earlier failure named the test case's own failing case, and the Orchestrator passed that case on to the Delegate. A third run with the account worded generically (commit `ab4d071`) passed one task of three: `parallel-feature` failed on the same acceptance test as the skill round, and `bug-fix` failed on a fix that went beyond the prompt. So the second run's pass rests on the hint, and the revision doesn't reliably meet the rule. A first attempt with the first revision is recorded too; its `parallel-feature` run ran out of ChatGPT Quota and isn't counted.

## Setup

As in the skill round: `--effort medium`, the two `n8n-custom-ytdlp` runs at the same time, then `parallel-feature` on its own, with nothing else running on the machine.

The counted runs started at 23:04 local time, just after the ChatGPT Quota's five-hour window reset.

## Results

The counted runs are the three `skill` lines recorded from 2026-10-13T20:04. Claude's cost is Claude Code's list-price `costUSD`, a proxy for Claude Quota, as in the earlier rounds. All runs used only `claude-opus-5-5`, with no Subagents.

| Task | Config | Passed | Wall time | Claude turns | Claude tokens | Claude cost | Delegations | Codex tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bug-fix | alone | yes | 39 s | 6 | 178K | $0.33 | — | — |
| bug-fix | pointer | yes | 89 s | 4 | 375K | $0.46 | 1 | 71K in, 771 out |
| bug-fix | skill | yes | 36 s | 4 | 152K | $0.35 | none | — |
| investigation | alone | yes¹ | 37 s | 5 | 170K | $0.35 | — | — |
| investigation | pointer | yes¹ | 292 s | 3 | 377K | $0.51 | 1, read-only | 287K in, 8,030 out |
| investigation | skill | yes¹ | 35 s | 5 | 156K | $0.39 | none | — |
| parallel-feature | alone | yes | 669 s | 58 | 5,782K | $3.21 | — | — |
| parallel-feature | pointer | yes | 1,087 s | 9 | 1,057K | $1.02 | 1 | 3.52M in, 28,390 out |
| parallel-feature | skill | yes | 1,740 s | 18 | 3,081K | $1.80 | 2 at once, then again²: gpt-6.1-sol xhigh, core and its tests, `partial`, 747 s; gpt-6.1-sol medium, Android, `partial`, 552 s; both `NETWORK` | 5.37M in (5.16M cached), 34,411 out² |

| Config | Passed | Claude tokens | Claude cost | Wall time | Codex input tokens |
| --- | --- | --- | --- | --- | --- |
| alone | 3 of 3 | 6.13M | $3.88 | 745 s | — |
| pointer | 3 of 3 | 1.81M | $1.99 | 1,468 s | 3.88M |
| skill, revised | 3 of 3 | 3.39M (−45% against alone, +87% against pointer) | $2.55 (−34% against alone, +28% against pointer) | 1,811 s | at least 5.37M² |

Per task, the skill's Claude cost against `alone` and `pointer`: `bug-fix` +7% and −24%, `investigation` +13% and −23%, `parallel-feature` −44% and +76%. In Claude tokens, the skill used less than `alone` on every task: −14%, −8% and −47%.

¹ Known-answer task, recorded ungraded because the runner had no terminal to ask on. Claude graded it and marked it passed in results.jsonl, as in the earlier rounds. The final message makes every point of the known answer, except that the HEAD request is anonymous, which no earlier answer said either. The run changed no files.

² The first two Delegations, d1 and d2, were stopped by Claude Code after 600 s, with no Result or evidence, and Opus started them again as d3 and d4 with the same task parts. The Codex tokens are d3's and d4's only; d1's and d2's ten minutes each aren't counted. See "The background time limit".

### `parallel-feature`, step by step

- **0–2 min:** Opus read the core toggle code, the widget, the Calendar card, the filter and the Android callers (eight commands), wrote `ListHabitsBehavior.onToggle(habit, date, shownValue, x, y): Int` as a stub with `TODO("tap cycle")`, and wrote two task parts: core, meaning the setting's removal, every tap cycle, the filter and their tests (Write scope `uhabits-core`, xhigh), and Android (`uhabits-android`, medium).
- **2–12 min:** both Delegations ran. Claude Code stopped both background commands at 600 s, both Delegates in their final checks.
- **12–25 min:** Opus started both again, this time with a one-hour Bash timeout. Android came back after 552 s and core after 747 s, both `partial`. The core Delegate's full suite hit the read-only `/tmp`, and the wrapper's rerun passed. The Android Delegate's own grep Check matched translated strings it had rightly left alone, and its compile Check's rerun passed. Opus applied Android, put back the two English strings the Delegate had deleted, which other translations still use, and waited for core.
- **25–29 min:** Opus applied core, reverted a Calendar colour change the user hadn't asked for together with its test, ran the core tests, ktlint and the Android compiles in the merged tree, fixed two import-order violations the Delegate had introduced, and listed the reference images a human must review.

The core task part named the case both failed runs had missed: "a Rest day is shown as a Rest day (computed `YES_AUTO`) even when its stored entry is Unanswered or No, and tapping it must behave the same in the list, the Calendar card and the widget. Cover a Rest-day tap in tests for all three." The Delegate's widget code moves on from the computed entry.

## How the revision changed behaviour

Against the skill round's gaps, in the counted runs:

- **Gap 1, production code written after a short read: closed.** Before the Delegations, Opus wrote one signature with a stub body and nothing else, and the core behaviour went to a Delegation together with its tests. But see the limits: the skill's own account of the failure names the case.
- **Gap 2, tests of the Orchestrator's account: closed.** The tests came from the Delegate that wrote the behaviour, against criteria the task part gave "verbatim where possible".
- **Gap 3, a small investigation delegated: closed,** in both attempts. Opus answered from one 370-line file in 35–37 s, as `alone` did.
- **Gap 4, a split that didn't shorten the Run: not closed.** Opus's own share was short this time, two minutes before the Delegations and four after, but the longest Delegation, core at xhigh, took 747 s. Without the 620 s between starting the first Delegations and starting them again, the Run would have taken about 1,120 s, about as long as `pointer`'s 1,087 s and still longer than `alone`'s 669 s. The guidance stays: it is still true and cheap. Shortening the Run needs a smaller longest part, which this split didn't find.
- **Gap 5, the skill's own cost without a Delegation: smaller, within run-to-run noise.** Neither n8n run called `report`. `bug-fix` took 4 turns and cost 7% more than `alone` (29% in the skill round). The first attempt's `bug-fix`, with the same guidance, took 9 turns and cost 31% more, so one run per task can't separate the revision from variation. On both n8n tasks the skill used fewer Claude tokens than `alone`, yet cost more, because its cache writes, which cost more per token, were larger.

## The background time limit (a new failure)

Claude Code stops a background Bash command when its timeout runs out, ten minutes when the call gives none. Every earlier `parallel-feature` run had given its `delegate` calls a timeout of 40 to 120 minutes. This run's first two calls gave none, and both were stopped at 600 s while their Delegates were in their final checks. The first revision had cut "A Delegation takes minutes" from the skill's line about running in the background, which may have removed the cue.

The wrapper was stopped with its command, so it wrote no Result, evidence or token usage for d1 and d2, and `report` lists them as "no evidence: still running, or the wrapper failed". That leaves a gap in the Run record, which is meant to hold every Delegation's token usage. The wrapper ought to record what it can when it is stopped. That is a wrapper change, not a Gotcha, and isn't part of this issue.

## Third run: the example worded generically

After the second run, the skill's account of the earlier failure was reworded without the test case's specifics: no widget, no Rest day, no `true`. The wrapper also gained the `stopped` failure kind, which keeps a stopped Delegation's diff so it can be resumed. The three tasks ran again on 2026-10-14 from 09:56 local time, as before, on commit `ab4d071`.

| Task | Passed | Wall time | Claude turns | Claude tokens | Claude cost | Against `alone` | Delegations | Codex tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bug-fix | **no** | 108 s | 11 | 375K | $0.62 | +88% | none | — |
| investigation | yes³ | 50 s | 5 | 197K | $0.40 | +16% | none | — |
| parallel-feature | **no** | 1,289 s | 10 | 1,531K | $1.29 | −60% | 2 at once: gpt-6.1-sol medium, core and its tests, `done`, 490 s; gpt-6.1-sol xhigh, Android, `done`, 967 s | 3.71M in (3.51M cached), 32,946 out |

Together: one of three passed, 2.10M Claude tokens (−66% against `alone`), $2.31 (−41%) and 1,446 s.

- **`parallel-feature`: the rule was followed, and the case was missed anyway.** Opus wrote only the `onToggle` stub, gave the core change and its tests to one Delegation and Android to another, and gave both `delegate` calls a long Bash timeout, so nothing was stopped. But it ran the core Delegation at medium, and its task part listed the user's criteria without singling out a Rest day. The Delegate replaced the widget's setting with `true`, the same line as in both earlier failures, and its tests didn't tap a widget on a Rest day. The check failed on `WidgetBehaviorTest.testOnToggleRepetition_onRestDay`, as in the skill round. The two runs that got this case right had it at xhigh: `pointer`'s single Delegation, and the second run's core Delegation, whose task part also named the case.
- **`bug-fix`: a fix wider than the prompt.** Opus made no Delegation. Besides failing the run when the locked version's tag is gone, it made the updater check the locked version's tags whenever it keeps them for a newer version not pushed yet. It rewrote two existing tests to record those requests. The prompt says "Only a newly planned version whose tag is missing is still skipped for the run", and the reference's tests don't record the extra requests, so three of them failed. Nothing in the skill speaks to how far a fix should go; the other three `skill` runs of this task made the narrow fix.

What the three runs together show about gap 1: limiting what Opus writes before the Delegations works, since Opus wrote only a stub in both runs of the second wording. Keeping a change and its tests together is not enough on its own. The widget's Rest-day case is easy to miss in a mechanical replacement, and it was caught only at xhigh, or when the task part named it. Finding the case belongs to whoever writes the behaviour, so the next revision would have to say how hard that Delegation should think, or what the task part must point at, without naming this test case's answer.

## Gotchas added

- A background `delegate` call needs a Bash timeout longer than the Delegation: the failure above, Delegations d1 and d2 of `parallel-feature`.

The sandbox's read-only `/tmp` showed again, and both Delegates returned `partial` for it, as the existing Gotcha predicts; Opus trusted the wrapper's reruns.

## First attempt: the first revision (not counted)

The first revision (commit `260fb88`) ran all three tasks. Its `parallel-feature` run can't be counted: the ChatGPT Quota ran out two minutes into both Delegations (`quota_exhausted`, "try again at 11:01 PM"), and Opus stopped and asked the user how to go on, as the skill says. The runner has no user, so the Run ended there.

| Task | Passed | Wall time | Claude turns | Claude tokens | Claude cost | Delegations |
| --- | --- | --- | --- | --- | --- | --- |
| bug-fix | yes | 114 s | 9 | 298K | $0.43 | none |
| investigation | yes³ | 37 s | 6 | 186K | $0.37 | none |
| parallel-feature | no (not counted) | 258 s | 2 | 793K | $0.83 | 2, both `quota_exhausted` |

³ Graded by Claude, as in the earlier rounds: the final message makes every point of the known answer except that the HEAD request is anonymous, like every earlier answer.

What it showed:

- **Gap 3 closed.** On `investigation`, Opus wrote "The whole answer is in one 370-line file … so handing it off would have cost more than reading it", and answered in 37 s, as `alone` did.
- **Gap 5 partly.** `bug-fix` skipped the `report` with no Delegations, but spent the turn on an end-to-end run of the updater instead: 9 turns, as before, and $0.43 against `alone`'s $0.33.
- **Gap 1 not closed.** Opus read the core code for under a minute (six commands), then wrote the core change itself, compiled it and delegated the core tests and the Android part. The widget change was the skill round's, line for line: `areQuestionMarksEnabled = preferences.areQuestionMarksEnabled` became `= true`, so a widget tap still moves on from the stored value. The check failed on the same acceptance test, `WidgetBehaviorTest.testOnToggleRepetition_onRestDay`, with the same `expected:<…value=2> but was:<…value=-1>`. The core-tests task part quoted the user's criteria but asked for cycles "starting from Unanswered", and named a Rest day only for the filter.

Defining an interface as a signature and its contract, and allowing the behaviour behind it to be "worked out properly" by Opus, didn't change what Opus did. In both failed runs, Opus wrote a behaviour change and a Delegate wrote its tests; in the passing `pointer` run, one Delegate wrote both against the user's criteria. The second revision says that: before the Delegations, Opus writes only what other parts must compile against, and a behaviour change and its tests go together, to one Delegation or to Opus.

## Limits

- **The second revision named the failing case.** The third run, worded without it, failed the same case, so the second run's pass came from the rule together with the hint.
- One run per configuration and task. Four `skill` runs of `bug-fix` cost +29%, +31%, +7% and +88% against `alone`, and one of them failed, so a single run says little about the skill's cost on small tasks.
- The `investigation` grades are Claude's, as in the earlier rounds.
- Codex's tokens for `parallel-feature` leave out the two stopped Delegations, so they understate its ChatGPT Quota.
- The baselines ran at the user's `medium` setting, and this round at `--effort medium`, as in the skill round.
