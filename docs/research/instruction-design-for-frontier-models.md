# Instruction design for frontier models: how prescriptive should skills, plugins, and delegation briefs be?

Researched 2026-10-05 for the opus-orchestrator design, in which Claude Opus 5.5 orchestrates and delegates subtasks to OpenAI models.

**Scope and currency.** Vendor guidance below is the version live on 2026-10-05: Anthropic's prompting docs cover Claude Opus 5.5 and the Fable 5.x and Mythos 5.x models ([Anthropic, prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)). OpenAI's docs cover GPT-5.5 ([OpenAI, Using GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)) and the GPT-6 family. OpenAI's "latest model" page now leads with GPT-6 Astra, GPT-6.1 Sol and GPT-6 Luna ([OpenAI, Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model)), and Codex now recommends `gpt-6.1-sol` as its default model ([Codex subagents docs](https://learn.chatgpt.com/docs/agent-configuration/subagents)). The brief said "GPT-5.x / Codex", so the delegate may in practice be a GPT-6.x model. Guidance for both generations is included. Most peer-reviewed results tested 2023–2025 models such as GPT-4o, Claude 3.5–4, o3 and Gemini 2.5. Each one is labelled with the models it tested, because results on those models may not carry over to Opus 5.5 or GPT-6. Multi-model orchestration tooling (CLIs, MCP bridges, SDKs) is covered in a separate research doc and is only mentioned in passing here.

---

## Verdict on the hypothesis

**Supported, with qualifications.** This verdict is closer to "supported" than to "partly supported", but only under a specific meaning of "genuinely necessary".

- **Vendor guidance converges on fewer instructions that state the outcome.** Anthropic says skills written for earlier models "are often too prescriptive" for its newest models and "can degrade output quality" ([Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)). It also says to drop "CRITICAL: You MUST…" phrasing, which has caused overtriggering since Opus 4.5 ([Anthropic best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)), and to remove verification instructions on Opus 5 ([Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)). OpenAI says legacy step-by-step prompts "add noise, narrow the model's search space, or lead to overly mechanical answers" on GPT-5.5 ([OpenAI GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)).
- **Independent research finds that every extra instruction and every extra token has a cost.** Compliance falls as the number of instructions and the prompt length grow ([IFScale](https://arxiv.org/abs/2507.11538), [AgentIF](https://arxiv.org/abs/2505.16944), [Levy et al.](https://arxiv.org/abs/2402.14848), [Chroma](https://www.trychroma.com/research/context-rot)). Repository context files raise inference cost by more than 20% without reliably raising success ([Gloaguen et al. 2026](https://arxiv.org/abs/2602.11988)).
- **"Necessary" does not mean "short and vague".** The same sources measure clear gains from being explicit in three cases:
  - **Supplying knowledge the model lacks.** Curated skills added +16.6 percentage points ([SkillsBench](https://arxiv.org/abs/2602.12670)). An 8 KB docs index raised the pass rate from 53% to 100% ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)).
  - **Defining the deliverable, scope and done-criteria.** Explicit delegation briefs prevented duplicated work in Anthropic's multi-agent system ([Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)).
  - **Naming an observed failure mode.** One added sentence measurably improved Opus 5.5 ([Prompting Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)).
- **Newer models take instructions more literally, and they penalize contradictions.** Opus 4.8, Sonnet 5 and GPT-5.5 execute under-specified scope, or a careless qualifier such as "be conservative", exactly as written ([Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8), [GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)). Contradictions burn reasoning tokens on GPT-5 ([GPT-5 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)), and conflicting skill guidance can make GPT-6 Astra stall ([GPT-6](https://developers.openai.com/api/docs/guides/latest-model)).
- **Hard constraints should not depend on prose at all.** Vendors describe prompt instructions as advisory. For invariants they point to hooks, schemas, permissions and caps instead ([Claude Code memory](https://code.claude.com/docs/en/memory), [Claude Code best practices](https://code.claude.com/docs/en/best-practices)).
- **Net:** leave the *path* free. Specify the *destination, boundaries and interface* explicitly. Enforce invariants in code. Add knowledge only where evals show a gap.

---

## Summary

The 15 findings most relevant to the design decision:

1. **Stop shouting at the model.** Opus 4.5 and 4.6 respond more strongly to system prompts. Wording such as "CRITICAL: You MUST use this tool" now causes overtriggering, so write "Use this tool when…" instead ([Anthropic best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
2. **Skills tuned for older models can hurt current ones.** Anthropic says they are "often too prescriptive" and "can degrade output quality", and recommends removing instructions where default performance is better ([Prompting Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)).
3. **Remove self-checking boilerplate on Opus 5.** Verification and "double-check" instructions cause over-verification, so remove them rather than rewording them. Anthropic's Opus 5.5 guide says the Opus 5 patterns "remain a reasonable starting point" ([Prompting Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), [Prompting Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)).
4. **OpenAI's GPT-5.5 guidance is to state the outcome and leave the process.** State the outcome, success criteria and stop rules, cut step-by-step process guidance, and reserve ALWAYS/NEVER for true invariants ([OpenAI GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)).
5. **Contradictions do more damage than missing detail.** GPT-5 "expends reasoning tokens searching for a way to reconcile the contradictions" ([GPT-5 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)). GPT-6 Astra is "more sensitive" to instructions in skills and AGENTS.md and may "pause and block work early" on conflicting guidance ([OpenAI GPT-6](https://developers.openai.com/api/docs/guides/latest-model)).
6. **Literal instruction following means scope has to be stated.** Opus 4.8 and Sonnet 5 do not generalize an instruction from one item to another or infer requests you did not make ([Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8), [Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5)). GPT-5.5 likewise "interprets prompts in a literal and thorough manner" ([GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)).
7. **Instruction count has a measurable cost.**
   - With 500 simultaneous instructions, the best model tested (2025) reached only 68% accuracy. Reasoning models held near-perfect accuracy to about 150 instructions, then declined ([IFScale](https://arxiv.org/abs/2507.11538)).
   - Real agentic system prompts average 1,723 words and 11.9 constraints. The best model satisfied every constraint in only 27.2% of them, and almost none above 6,000 words ([AgentIF](https://arxiv.org/abs/2505.16944)).
8. **Prompt length alone degrades reasoning.**
   - Average accuracy fell from 0.92 to 0.68 by 3,000 tokens of input ([Levy et al., ACL 2024](https://arxiv.org/abs/2402.14848)).
   - Drops of 13.9–85% appeared even with perfect retrieval ([Du et al. 2025](https://arxiv.org/abs/2510.05381)).
   - All 18 models tested degraded as input grew ([Chroma, Context Rot](https://www.trychroma.com/research/context-rot)).
9. **Repository context files did not generally improve success.**
   - Over 20% more cost, LLM-generated files slightly negative, and repo overviews did not help. The instructions in them *were* followed ([Gloaguen et al. 2026](https://arxiv.org/abs/2602.11988)).
   - A July 2026 ablation also found no measurable correctness effect ([Khatri 2026](https://arxiv.org/abs/2607.27250)).
   - One study did measure 28.6% lower median runtime ([Lulla et al. 2026](https://arxiv.org/abs/2601.20404)).
10. **Curated, focused skills help; exhaustive or self-written ones do not.** Curated skills raised the average pass rate from 33.9% to 50.5%. Focused skills with at most three modules beat exhaustive bundles. In v1 of the paper, self-generated skills gave no benefit ([SkillsBench](https://arxiv.org/abs/2602.12670)).
11. **Triggering is the weak link for on-demand skills.** A skill went uninvoked in 56% of eval cases. A compressed, always-loaded 8 KB index in AGENTS.md scored 100%, against 79% for the best skill setup ([Vercel, Jan 2026](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)).
12. **Reasoning models need little step-by-step instruction.**
    - Anthropic: "think thoroughly" often beats a hand-written step plan ([Anthropic best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).
    - OpenAI: keep prompts simple, avoid chain-of-thought prompts, try zero-shot first ([OpenAI reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)).
    - Chain-of-thought can also hurt: o1-preview was up to 36.3 points worse than GPT-4o on some tasks ([Liu et al.](https://arxiv.org/abs/2410.21333)).
13. **Delegation briefs are the place where explicitness pays most.**
    - Each subagent needs "an objective, an output format, guidance on the tools and sources to use, and clear task boundaries" ([Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)).
    - System-design and specification problems are the largest failure category in multi-agent systems, about 44%. Better role specifications added 9.4% and a verification step added 15.6% ([MAST](https://arxiv.org/abs/2503.13657)).
14. **Prose is advisory; enforcement belongs in code.** Claude Code treats CLAUDE.md as "context, not enforced configuration", while hooks "are deterministic" ([memory docs](https://code.claude.com/docs/en/memory), [best practices](https://code.claude.com/docs/en/best-practices)). Opus 5.5's time budget is "advisory" ([Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)). Codex `--output-schema` enforces the result format ([Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)).
15. **Give the whole specification once, up front.** Delivering the same task across several turns cost an average of 39%; giving it all at once recovered 95.1% of single-turn performance ([Laban et al. 2025](https://arxiv.org/abs/2505.06120)). Opus 5 "performs best when given the complete task specification up front and left to run" ([Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)).

---

## 1. Current vendor guidance

### 1.1 Anthropic (Claude Opus 4.5 through Opus 5.5, Fable 5.x)

**Tone down legacy emphasis.** Anthropic says "Claude Opus 4.5 and Claude Opus 4.6 are also more responsive to the system prompt than previous models. If your prompts were designed to reduce undertriggering on tools or skills, these models may now overtrigger. The fix is to dial back any aggressive language." Its example swap is "CRITICAL: You MUST use this tool when..." becoming "Use this tool when..." ([best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)). The same page gives this advice for Opus 4.6:
- "Replace blanket defaults with more targeted instructions."
- "Remove over-prompting… Instructions like 'If in doubt, use [tool]' will cause overtriggering."
- Under migration: "Tune anti-laziness prompting… dial back that guidance."

**Explain the reason; skip the bare rule.** The general principles section contrasts "NEVER use ellipses" with an explanation (output goes to a text-to-speech engine) and concludes "Claude is smart enough to generalize from the explanation" ([best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)). Prompting Claude Fable 5 repeats the point in a section titled "Give the reason, not only the request" ([Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5)).

**Prefer general guidance over prescribed reasoning steps.** "A prompt like 'think thoroughly' often produces better reasoning than a hand-written step-by-step plan. Claude's reasoning frequently exceeds what a human would prescribe" ([best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)). On Opus 5 and later, prompts that ask the model to write its reasoning out in the response "may be declined" with the `reasoning_extraction` refusal category ([Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)). "Show your thinking" instructions in skills are now actively harmful.

**Opus 5 needs fewer quality instructions but more scope control** ([Prompting Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)):
- **Verification.** "If your prompt contains explicit verification instructions… remove them: instructions like these cause over-verification on Claude Opus 5, and removing them reduces wasted tokens with no loss in quality."
- **Re-checks.** "Avoid instructing re-checks it already performs… these compound with the model's own behavior and add cost without improving results."
- **Scope creep.** Opus 5 "can also expand the scope of a task… For narrow tasks, constrain scope explicitly."
- **Delegation.** Opus 5 "delegates to subagents more readily than prior models… give explicit guidance on which scenarios warrant delegation, or set deterministic caps." For Claude Code, the caps are `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` and the SDK's `max_budget_usd`.
- **Full spec up front.** It "performs best when given the complete task specification up front and left to run."

**Opus 5.5 (current Opus).** "Existing Claude Opus 5 prompts should perform well without changes" ([Prompting Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)). The main lever is now an API parameter, not prompt text: "Lowering effort reduces thinking, and with it cost and latency, more reliably than prompt instructions do." In a chat product, removing a "think carefully before answering" line "made replies start sooner, with no clear decline in the quality."

The same page, however, recommends several *specific* added instructions, each with a measured effect:
- **Explore before acting.** One sentence telling the model to explore all relevant apps first meant Opus 5.5 "completed noticeably more of them correctly" on multi-app automation tasks.
- **Avoid early stops.** A long paragraph names four specific ways the model ends turns too early. The doc notes the model "is responsive to instructions that name the specific kinds of early stop you want it to avoid."
- **Frontend style.** Naming concrete patterns to avoid works, whereas "a general instruction such as 'avoid a generic AI look' mostly swaps one default for another."

**Literal instruction following (Opus 4.8, Sonnet 5).** Both "interpret prompts literally and explicitly, particularly at lower effort levels. It does not silently generalize an instruction from one item to another, and it does not infer requests you didn't make… state the scope explicitly" ([Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8), [Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5)). The code-review case shows the risk. A review prompt that says "be conservative" or "only report high-severity issues" makes recall drop, because the model follows the filter faithfully. Anthropic's advice is to "be concrete about where the bar is rather than using qualitative terms like 'important'."

**Fable 5 (Anthropic's top tier).**
- Steer with short instructions: "Instruction-following is improved enough that you can steer most behaviors with a brief instruction rather than enumerating each behavior by name."
- Re-check what is still needed: "Capability improvements at this level are also a good prompt to re-evaluate which instructions, tools, and guardrails are still needed."
- Refactor old skills: "Skills developed for prior models are often too prescriptive for Claude Fable 5 and can degrade output quality. Review and consider removing older instructions if default performance is better." ([Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5))

The same page still prescribes explicit *boundaries* ("State the boundaries") and a progress-audit instruction that "nearly eliminated fabricated status reports."

**Skill authoring best practices** ([platform docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)):
- **Default assumption.** "Claude is already very smart. Only add context Claude doesn't already have." Challenge each paragraph with "Does this paragraph justify its token cost?"
- **Degrees of freedom.** Match specificity "to the task's fragility and variability". Use high freedom (prose heuristics) when "multiple approaches are valid" or "decisions depend on context". Use low freedom (exact scripts) when "operations are fragile and error-prone", "consistency is critical" or "a specific sequence must be followed". The doc's analogy: a narrow bridge with cliffs needs guardrails, while an open field needs only a direction.
- **Size.** Keep the SKILL.md body under 500 lines. Keep references one level deep, and add a table of contents to reference files over 100 lines.
- **Options and scripts.** Avoid offering many options and provide a default instead. Prefer scripts for deterministic operations, and "solve, don't defer" (handle errors in the script rather than leaving them to Claude).
- **Test across models.** "Claude Opus (powerful reasoning): Does the Skill avoid over-explaining?"
- **Evaluation-driven development.** Run Claude without the skill, record the failures, build three evals, and "write minimal instructions… to address the gaps." This makes "necessary" a measurable property.

The open [Agent Skills specification](https://agentskills.io/specification) gives the same budgets: about 100 tokens of metadata, a body under 5,000 tokens recommended, and a SKILL.md under 500 lines.

**Claude Code (CLAUDE.md, skills, subagents):**
- **Size and pruning.** Target "under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Test each line with "Would removing this cause Claude to make mistakes? If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!" Listed as a failure pattern: "The over-specified CLAUDE.md… Claude ignores half of it because important rules get lost in the noise." ([memory](https://code.claude.com/docs/en/memory), [best practices](https://code.claude.com/docs/en/best-practices))
- **Emphasis.** "If Claude keeps skipping one instruction, add emphasis such as 'IMPORTANT' to that line alone. If you emphasize many lines, none of them stands out." ([best practices](https://code.claude.com/docs/en/best-practices))
- **Conflicts.** "If two instructions contradict each other, Claude may pick one arbitrarily." Claude Code now ships `/doctor prompt-audit`, which looks for "instructions written for older models" and contradictions ([memory](https://code.claude.com/docs/en/memory)).
- **Skills stay in context.** "Once a skill loads, its content stays in context across turns, so every line is a recurring token cost." After compaction, Claude Code re-attaches only "the first 5,000 tokens of each" invoked skill, within a combined 25,000-token budget ([skills](https://code.claude.com/docs/en/skills)).

**Engineering blog.**
- **"Right altitude."** "Effective context engineering" (Sep 2025) describes two failure modes: "hardcoding complex, brittle logic in their prompts" versus "vague, high-level guidance that fails to give the LLM concrete signals." The target is "the minimal set of information that fully outlines your expected behavior", and minimal does not necessarily mean short ([Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- **Heuristics over rules.** The multi-agent research post (Jun 2025): "Our prompting strategy focuses on instilling good heuristics rather than rigid rules" ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **Lessons from building Claude Code skills** (Thariq Shihipar; dated Jun 3, 2026 on the blog) ([claude.dev](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)):
  - "Don't state the obvious… A skill that restates what Claude would do by default adds context without adding value."
  - "The highest-signal content in any skill is the Gotchas section."
  - Avoid railroading: "Claude will generally try to stick to your instructions, and because skills are so reusable you'll want to be careful of being too specific." The post contrasts six numbered git steps with "Cherry-pick the commit onto a clean branch. Resolve conflicts preserving intent. If it can't land cleanly, explain why."
- **Harness components age as models improve.** "Every component in a harness encodes an assumption about what the model can't do on its own, and those assumptions are worth stress testing." The sprint decomposition was removed for Opus 4.6. The planner was told to stay on "product context and high level technical design rather than detailed technical implementation" because "errors in the spec would cascade into the downstream implementation" ([Harness design, Mar 2026](https://www.anthropic.com/engineering/harness-design-long-running-apps)).

**Rules versus judgment in Anthropic's framework.** Claude's constitution sets out when rules beat judgment. "Clear rules and decision procedures make the most sense when the costs of errors are severe enough that predictability and evaluability become critical, when there's reason to think individual judgment may be insufficiently robust, or when the absence of firm commitments would create exploitable incentives for manipulation." It adds that rules "can lead to poor outcomes when followed rigidly in circumstances where they don't actually serve their goal" ([Anthropic constitution](https://www.anthropic.com/constitution)). The document is about training, not prompting, but its criteria map cleanly onto the decision table in section 8.

### 1.2 OpenAI (GPT-5 through GPT-6, Codex)

**GPT-5 (launch-era guide)** ([GPT-5 prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)):
- **Precision cuts both ways.** "GPT-5 follows prompt instructions with surgical precision… poorly-constructed prompts containing contradictory or vague instructions can be more damaging to GPT-5 than to other models, as it expends reasoning tokens searching for a way to reconcile the contradictions." Early users who removed contradictions saw it "drastically streamlined and improved their GPT-5 performance."
- **Cursor's experience.** A `<maximize_context_understanding>` block saying "Be THOROUGH" "worked well with older models" but was "counterproductive with GPT-5". On small tasks it caused repetitive search calls. Removing it and "softening the language around thoroughness" fixed this.
- **Evidence that pulls the other way.** Cursor found that "structured XML specs like `<[instruction]_spec>` improved instruction adherence". Adding "more details about product behavior" reduced unnecessary hand-backs to the user. At *minimal* reasoning effort, more prescriptive prompting (planning prompts, persistence reminders, disambiguated tool instructions) matters more. The guide also allows fixed tool-call budgets "if you're willing to be maximally prescriptive."

**GPT-5.1 and 5.2.** GPT-5.1 is "excellent at instruction-following", so check for "conflicting instructions" first ([GPT-5.1 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-1_prompting_guide)). GPT-5.2 "remains prompt-sensitive" and "benefits from explicit scope and verbosity constraints" ([GPT-5.2 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-2_prompting_guide)).

**GPT-5.5** ([OpenAI GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)):
- **Outcome over process.** "GPT-5.5 works best when prompts define the outcome and leave room for the model to choose an efficient solution path."
- **Reduce step-by-step guidance.** "Reduce or remove detailed step-by-step process guidance. Let GPT-5.5 choose the path unless the product requires that path."
- **Retire legacy prompts.** "Legacy prompts often over-specify the process because earlier models needed more help staying on track. With GPT-5.5, that can add noise, narrow the model's search space, or lead to overly mechanical answers."
- **Smallest prompt that keeps the contract.** "Start with the smallest prompt that preserves the product contract."
- **Absolutes only for invariants.** Use ALWAYS/NEVER/must "for true invariants, such as safety rules, required output fields, or actions that should never happen. For judgment calls, such as when to search, ask for clarification, use a tool, or keep iterating, prefer decision rules instead."
- **Keep the explicit parts.** "Define success criteria and stopping rules, especially for long-running, tool-heavy, or evidence-gathering workflows." Also describe "the expected outcome, success criteria, allowed side effects, evidence rules, and output shape."
- **Use APIs for format and tools.** "Remove output schema definitions from the prompt where possible. Use Structured Outputs instead." "Put most tool-specific guidance in the tool descriptions themselves."
- **More effort is not automatically better.** "If the task has conflicting instructions, weak stopping criteria, or open-ended tool access, higher effort can lead to overthinking, unnecessary searching, or output quality regressions."
- **Suggested skeleton:** Role → Personality → Goal → Success criteria → Constraints → Output → Stop rules, with "Keep each section short. Add detail only where it changes behavior."

**GPT-6 Astra (current OpenAI flagship)** ([OpenAI GPT-6](https://developers.openai.com/api/docs/guides/latest-model)):
- **More sensitive to instruction files.** It "can be more sensitive to instructions contained in skills and other files, such as `AGENTS.md`. We **strongly recommend** auditing skills and other files accessible to your model."
- **Conflicts make it stop early.** "Unclear or conflicting guidance in a skill file may cause the model to pause and block work early. Make the priority of user instructions and skills explicit."
- **Defaults to remember.** It is "more likely to ask for clarification where earlier models would make assumptions", "may delegate less often than desired", and tends to test more broadly than small tasks need. Each of these needs an explicit instruction if it matters.

**Reasoning best practices** ([OpenAI](https://developers.openai.com/api/docs/guides/reasoning-best-practices)):
- Keep it simple: "Keep prompts simple and direct", "Avoid chain-of-thought prompts", "Try zero shot first, then few shot if needed".
- Be specific about constraints and goals: "Provide specific guidelines" for constraints, and "Be very specific about your end goal."

**Codex.**
- **Remove legacy progress prompting.** The Codex prompting guide (written for `gpt-5.3-codex`) says to "remove all prompting for the model to communicate an upfront plan, preambles, or other status updates during the rollout, as this can cause the model to stop abruptly before the rollout is complete."
- **AGENTS.md is closely followed.** Its files are injected as user-role messages, and "the model has been trained to closely adhere to these instructions" ([Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).
- **User prompting.** The user-facing guide recommends Goal / Context / Output / Boundaries, "Use only the parts that help", and "Focus on the one or two boundaries that matter most. You don't need to control every step" ([Codex prompting](https://learn.chatgpt.com/docs/prompting)).
- **Skills are more procedural than Anthropic's style.** Codex's skill guidance ("Keep each skill focused on one job… Write imperative steps with explicit inputs and outputs") leans more procedural than Anthropic's ([Codex skills](https://learn.chatgpt.com/docs/build-skills)).
- **Custom agents.** They should be "narrow and opinionated" ([Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)).

### 1.3 Google (Gemini 3)

"Be concise in your input prompts. Gemini 3 responds best to direct, clear instructions." It "may over-analyze verbose or overly complex prompt engineering techniques used for older models" ([Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3)). The same docs, however, offer a fairly long agentic system-instruction template covering reasoning, risk assessment, persistence and "Only take an action after all the above reasoning is completed" ([prompting strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)). Vendor guidance is therefore not uniformly minimalist.

---

## 2. Empirical research: instruction count, prompt length, and context

| Study | Models tested | Finding |
|---|---|---|
| [IFScale](https://arxiv.org/abs/2507.11538) (Jul 2025), 10–500 simultaneous keyword instructions | 20 models incl. o3, Gemini 2.5 Pro, Claude Opus 4, GPT-4.1 | Best model 68% at 500 instructions ([arXiv HTML](https://arxiv.org/html/2507.11538)). Gemini 2.5 Pro and o3 stay near-perfect to about 150, then decline steeply. GPT-4o fell to 15.4%, Claude Opus 4 to 44.6%. Bias toward earlier instructions peaks at 150–200. Errors are mostly omissions. |
| [ManyIFEval / "When Instructions Multiply"](https://arxiv.org/abs/2509.21051) (Sep 2025), up to 10 instructions | 10 LLMs | "Performance consistently degrades as the number of instructions increases." An earlier OpenReview version is titled "Curse of Instructions" (numbers not verified; see verification notes). |
| [AgentIF](https://arxiv.org/abs/2505.16944) (May 2025), 707 real agentic instructions averaging 1,723 words and 11.9 constraints | o1-mini, GPT-4o, Claude 3.5 Sonnet, DeepSeek-R1, and others | Best model (o1-mini) satisfies 59.8% of constraints but follows only 27.2% of instructions completely. Above 6,000 words, full compliance is "nearly 0" for all models. Tool constraints are hardest (~24%) ([HTML](https://arxiv.org/html/2505.16944)). |
| [Same Task, More Tokens](https://arxiv.org/abs/2402.14848) (ACL 2024) | GPT-4, GPT-3.5, Gemini Pro, Mistral | Average accuracy 0.92 → 0.68 when input grows from about 250 to 3,000 tokens. Irrelevant padding hurts more than duplicated relevant text. CoT doesn't mitigate the drop except on GPT-4 ([HTML](https://arxiv.org/html/2402.14848)). |
| [Context Length Alone Hurts](https://arxiv.org/abs/2510.05381) (Oct 2025) | 5 LLMs | 13.9–85% degradation even with perfect retrieval, with whitespace padding, and with irrelevant tokens masked. |
| [Context Rot](https://www.trychroma.com/research/context-rot) (Chroma, Jul 2025) | 18 models incl. Claude Opus 4, o3, GPT-4.1, Gemini 2.5 | Performance falls with input length even on simple tasks. A single distractor already hurts. Focused (~300-token) prompts substantially beat full (~113k-token) prompts on LongMemEval. |
| [Lost in the Middle](https://arxiv.org/abs/2307.03172) (TACL 2023) | 2023-era models | Information placed in the middle of a long context is used much less than information at the start or end. |
| [GSM-IC](https://arxiv.org/abs/2302.00093) (ICML 2023) | 2023-era models | "Model performance is dramatically decreased when irrelevant information is included." |
| [LLMs Get Lost in Multi-Turn Conversation](https://arxiv.org/abs/2505.06120) (May 2025) | 15 incl. GPT-4.1, o3, Claude 3.7 Sonnet, Gemini 2.5 Pro, DeepSeek-R1 | Average drop of 39% when task information arrives over several turns, mostly from unreliability (+112%). Concatenating the same information into one prompt recovers 95.1%. Reasoning models are not immune ([HTML](https://arxiv.org/html/2505.06120)). |
| [Sclar et al.](https://arxiv.org/abs/2310.11324) (ICLR 2024) and [He et al.](https://arxiv.org/abs/2411.10541) (2024) | LLaMA-2, GPT-3.5, GPT-4 | Formatting alone swings accuracy by up to 76 points (LLaMA-2-13B) and up to 40% (GPT-3.5). "Larger models like GPT-4 are more robust," so format sensitivity shrinks with capability. |
| [Control Illusion](https://arxiv.org/abs/2502.15851) (AAAI 2026) | 6 LLMs | Models "struggle with consistent instruction prioritization, even for simple formatting conflicts", and system/user separation is unreliable as a hierarchy. |

**Caveat.** These studies mostly tested pre-2026 models. Anthropic states that on Opus 5's 1M-token window "instruction following, tool calling, and reasoning stay consistent throughout the window" ([Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)). No independent replication on Opus 5.x or GPT-6 was found. The direction of these effects (more instructions and more tokens lead to lower compliance) is consistent across every generation tested. The size of the effect for current models is unknown.

---

## 3. Reasoning models and step-by-step instructions

- **Vendor consensus: fewer instructions about how to think.** OpenAI: chain-of-thought prompts are "unnecessary" for reasoning models, and examples should be tried only after zero-shot ([OpenAI](https://developers.openai.com/api/docs/guides/reasoning-best-practices)). Anthropic prefers general guidance over prescriptive steps ([Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)). DeepSeek: "Few-shot prompting consistently degrades its performance. Therefore, we recommend users directly describe the problem and specify the output format using a zero-shot setting" ([DeepSeek-R1](https://arxiv.org/html/2501.12948)).
- **Chain-of-thought (CoT) gains are narrow.** A meta-analysis of over 100 papers plus 14 models on 20 datasets found that "CoT gives strong performance benefits primarily on tasks involving math or logic, with much smaller gains on other types of tasks" ([Sprague et al., ICLR 2025](https://arxiv.org/abs/2409.12183)). On tasks where deliberation hurts humans, CoT cost up to 36.3 points for o1-preview against GPT-4o ([Liu et al.](https://arxiv.org/abs/2410.21333)).
- **Reasoning can crowd out simple constraints.** Across 15 models, "explicit CoT reasoning can significantly degrade instruction-following accuracy" on IFEval and ComplexBench, because reasoning diverts attention from constraint tokens ([Li et al. 2025](https://arxiv.org/abs/2505.11423)). Hard format and scope constraints should therefore be checkable after the fact, not merely stated.
- **Exception: low reasoning budgets.** At GPT-5 *minimal* reasoning, prompted planning and persistence reminders matter more ([GPT-5 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)). At `low` effort on Opus 4.8 and Sonnet 5, Anthropic suggests a targeted "This task involves multistep reasoning…" line, but prefers raising effort ([Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8)). Explicit procedure is a substitute for a missing reasoning budget, not a complement to a full one.

---

## 4. Direct evidence on agent context files and skills

**AGENTS.md and CLAUDE.md files:**
- [Gloaguen et al. (ETH Zurich / LogicStar), arXiv 2602.11988](https://arxiv.org/abs/2602.11988), latest v3 Sep 2026. Setup: Claude Code with Sonnet 4.5, Codex with GPT-5.2 and GPT-5.1 mini, and Qwen Code, on SWE-bench Lite plus 138 tasks from repos with developer-committed files ([HTML](https://arxiv.org/html/2602.11988)). Results:
  - LLM-generated context files changed resolution by −0.5% and −2% (not significant). Developer-written files added +2.4% (p = 0.21).
  - Cost rose by 20–23% on average, and steps increased in every setting.
  - Instructions *were* followed: `uv` was used 1.6 times per task when mentioned, against under 0.01 when not.
  - Repository overviews did not help agents find relevant files.
  - Authors' recommendation: "Context files should only contain specific additional instructions beyond what is already available in the codebase." The v1 abstract was blunter: "unnecessary requirements from context files make tasks harder, and human-written context files should describe only minimal requirements" ([v1](https://arxiv.org/abs/2602.11988v1)).
- [Khatri 2026](https://arxiv.org/abs/2607.27250): an ablation across Claude Code and Codex with 288 runs. "Context strategy does not measurably move correctness on either agent." Agents fail on "implementation skill… not missing repository knowledge that a context file could supply."
- [Lulla et al. 2026](https://arxiv.org/abs/2601.20404): across 124 PRs with Codex and Claude Code, AGENTS.md was associated with 28.64% lower median runtime and 16.58% fewer output tokens at comparable completion. The file paid for itself in efficiency, not correctness.
- [Probe-and-refine (2026)](https://arxiv.org/abs/2606.20512): guidance files tuned iteratively against failures raised the SWE-bench Verified resolve rate to 33.0%, against 28.3% for static guidance and 25.5% with no guidance. This used a small open model (Qwen3.5-35B-A3B), where more guidance is expected to help.

**Skills:**
- [SkillsBench](https://arxiv.org/abs/2602.12670) (v4, Jun 2026; 87 tasks, 18 model-harness configurations):
  - Curated skills raised the pass rate from 33.9% to 50.5% (+16.6 pp, with configurations ranging from +4.1 to +25.7).
  - "Focused Skills with at most three modules outperform larger or exhaustive bundles."
  - Smaller models with skills can match larger models without them.
  - v1 (86 tasks) also reported that "self-generated Skills provide no benefit on average", that gains ranged from +4.5 pp in software engineering to +51.9 pp in healthcare, and that 16 of 84 tasks got *worse* with curated skills ([v1](https://arxiv.org/abs/2602.12670v1)).
- [SkillJuror](https://arxiv.org/abs/2606.11543) (Jun 2026): putting the same knowledge behind progressive disclosure (a short root file pointing to resources) gave +4.1% verifier-passing trials over a flat layout. It helped most when resources guided implementation or repair, and least when success hinged on "exact output conventions, numerical thresholds".
- [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) (Jan 2026; Next.js 16 APIs absent from training data):
  - Pass rates: 53% with no docs, 53% with the default skill, 79% with the skill plus explicit instructions to use it, and 100% with an AGENTS.md docs index.
  - "In 56% of eval cases, the skill was never invoked."
  - Wording mattered: "You MUST invoke the skill" made agents "anchor on doc patterns" and miss project context, while "Explore project first, then invoke skill" worked better.
  - The index was compressed from 40 KB to 8 KB without losing accuracy.
- **Anthropic skill-creator** (Mar 2026) distinguishes "capability uplift" skills from "encoded preference" skills: "If the base model starts passing your evals *without* the skill loaded, that's a signal the skill's techniques may have been incorporated into the model's default behavior." Description optimization "improved triggering on 5 of 6" document skills ([Anthropic](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)).

**Interfaces beat prose scaffolding:**
- **Tool architecture.** Across 11,700 trajectories, "more structured low-level interfaces improve consistency across repeated attempts by up to 4.7×". In contrast, "lightweight text-based cognitive-scaffolding tools… have limited effect" ([Xu et al. 2026](https://arxiv.org/abs/2608.11386)).
- **Anthropic's tool results (Nov 2025):**
  - Tool use examples raised accuracy "from 72% to 90% on complex parameter handling", because "JSON schemas define what's structurally valid, but can't express usage patterns."
  - Loading tools on demand via tool search raised Opus 4 from 49% to 74%.
  - Source: [Anthropic, advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use).
- **Tool descriptions.** "Even small refinements to tool descriptions can yield dramatic improvements" ([Anthropic, writing tools](https://www.anthropic.com/engineering/writing-tools-for-agents)).

**Synthesis.**
- **What wins:** knowledge the model genuinely lacks, kept compact, available without a retrieval decision when it is critical, and structured where structure is checkable.
- **What does not help:** generic overviews, restatements of default behavior, and procedure the model would derive anyway. These add cost without gains.
- **Weak spot:** for on-demand skills, *triggering* is the most fragile link.

---

## 5. Disconfirming evidence: where more explicit instructions measurably helped

| Case | What was added | Measured effect | Source |
|---|---|---|---|
| Curated skills | Domain procedures and gotchas | +16.6 pp average, up to +25.7 pp per configuration | [SkillsBench](https://arxiv.org/abs/2602.12670) |
| Docs index in AGENTS.md | 8 KB index of post-training APIs | 53% → 100% | [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) |
| Tool use examples | Concrete example calls | 72% → 90% on complex parameters | [Anthropic](https://www.anthropic.com/engineering/advanced-tool-use) |
| Opus 5.5 multi-app tasks | One sentence: explore relevant sources first | "Noticeably more" correct, at medium and max effort | [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) |
| Opus 5.5 silent agentic turns | Harness-injected update reminder | Long silent stretches roughly halved, with no cost change | [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) |
| Fable 5 long runs | Audit-progress-claims instruction | "Nearly eliminated fabricated status reports" | [Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) |
| Multi-agent research | Detailed briefs (objective, format, tools, boundaries) plus effort-scaling rules | Vague briefs caused duplicated work. The post reports no per-change number. | [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system) |
| Multi-agent systems (ChatDev) | Better role specifications; a verification step | +9.4%; +15.6% | [MAST](https://arxiv.org/abs/2503.13657) |
| Evolving playbooks | Detailed, growing context instead of concise summaries ("brevity bias") | +10.6% on agents, +8.6% on finance | [ACE](https://arxiv.org/abs/2510.04618) |
| Guidance tuned to failures | Iteratively refined AGENTS.md (small open model) | 25.5% → 28.3% (static) → 33.0% (refined) | [Probe-and-refine](https://arxiv.org/abs/2606.20512) |
| Generator/evaluator harness | Explicit grading criteria and "sprint contracts" on what done means | The evaluator still caught stubbed features even on Opus 4.6 | [Harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps) |
| Long-running harness | JSON feature list; "It is unacceptable to remove or edit tests…" | The model is "less likely to inappropriately change or overwrite JSON files" than Markdown | [Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
| Code review (Opus 4.8, Sonnet 5) | A concrete severity bar instead of "be conservative" | Recall recovers. The qualitative instruction was executed literally. | [Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8) |
| GPT-5 at Cursor | XML instruction specs; product-behavior details | Better adherence; fewer unnecessary hand-backs | [GPT-5 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide) |

**The common pattern.** Explicitness paid off in four situations:
1. It **supplied knowledge** the model could not infer.
2. It **defined the deliverable, scope, done-criteria or interface**.
3. It **targeted a specific, observed failure mode**, named concretely.
4. It **compensated for a smaller model or a low reasoning budget**.

None of these cases is "dictate the steps of a task the model can already plan." The disconfirming evidence therefore narrows what "necessary" means; it does not contradict the hypothesis. It does refute the naive version ("shorter is always better"). The [ACE](https://arxiv.org/abs/2510.04618) result in particular warns that compressing context into concise summaries can discard the domain insights that matter.

---

## 6. Prose versus enforcement

- **Claude Code treats instruction files as advisory.** "Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook." CLAUDE.md "is delivered as a user message after the system prompt… there's no guarantee of strict compliance." "Settings rules are enforced by the client regardless of what Claude decides to do" ([memory](https://code.claude.com/docs/en/memory)). "Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens" ([best practices](https://code.claude.com/docs/en/best-practices)).
- **Budgets need a hard stop outside the prompt.** Opus 5.5's time budget "is advisory and nothing stops the model at the limit, so if you need a hard stop, keep your own timeout" ([Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)). Subagent caps are deterministic environment and SDK settings ([Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), [subagents](https://code.claude.com/docs/en/sub-agents)).
- **Output contracts can be enforced by the API.**
  - Structured outputs guarantee schema compliance on both platforms ([Anthropic](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs)).
  - `codex exec --output-schema` makes Codex's final response conform to a JSON Schema ([Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)).
  - Caveat from OpenAI: "the model will always try to adhere to the provided schema, which can result in hallucinations if the input is completely unrelated." A schema needs a legitimate "blocked / cannot comply" path.
  - Opus 5.5 no longer supports forced tool use (`tool_choice` any/tool). Anthropic's advice is to "say in the prompt when the tool applies" ([What's new in Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5)).
- **Instruction hierarchies are not a security boundary.** They are unreliable even for formatting conflicts ([Control Illusion](https://arxiv.org/abs/2502.15851)). Anthropic calls its pasted-content tagging "one guardrail alongside other prompt-injection defenses" ([Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)).
- **Emphasis still has a narrow role.** Use one "IMPORTANT" line, not many ([best practices](https://code.claude.com/docs/en/best-practices)). Strong wording is reserved for the single most damaging failure, such as deleting tests ([Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)).

---

## 7. Briefs that one model writes for another

**The delegate starts cold.**
- **Claude Code subagents** receive only their own system prompt, the delegation message and CLAUDE.md. They do not get the parent's conversation, skills or files read. "If a rule must [reach the subagent]… restate it in the prompt you give Claude when delegating" ([subagents](https://code.claude.com/docs/en/sub-agents)).
- **Agent teammates** "don't inherit the lead's conversation history. Include task-specific details in the spawn prompt" ([agent teams](https://code.claude.com/docs/en/agent-teams)).
- **Codex** sees its AGENTS.md chain (as user-role messages it is "trained to closely adhere" to) plus the prompt it is given ([Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)).

**What a brief must contain.**
- **Anthropic.** "Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries." Effort-scaling rules are embedded in the lead prompt: 1 agent with 3–10 tool calls for simple fact-finding, 2–4 subagents for comparisons, more than 10 for complex research. Early versions spawned "50 subagents for simple queries" ([Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **Return size.** Subagents should return "a condensed, distilled summary… (often 1,000-2,000 tokens)" ([context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)), with large outputs persisted as artifacts rather than relayed ([multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **Codex.** "A good subagent prompt should explain how to divide the work, whether Codex should wait for all agents before continuing, and what summary or output to return" ([Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)). OpenAI's GPT-5.5 skeleton (Goal / Success criteria / Constraints / Output / Stop rules) fits a delegation brief directly ([GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)).

**Specify what, not how.** The harness-design planner deliberately avoided granular implementation detail because errors "would cascade into the downstream implementation". Generator and evaluator agreed on what done means ("sprint contracts") before work began ([Harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps)). Anthropic's Claude Code spec advice reads the same way: "name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step" ([best practices](https://code.claude.com/docs/en/best-practices)).

**Write it once and completely.** Underspecified information spread across turns degrades results by 39% on average ([Laban et al.](https://arxiv.org/abs/2505.06120)). Anthropic: "specify the task, intent, and relevant constraints upfront in the first human turn" ([Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8)). After two failed corrections, Anthropic recommends restarting with a better prompt: "A clean session with a better prompt almost always outperforms a long session with accumulated corrections" ([best practices](https://code.claude.com/docs/en/best-practices)).

**Differences between model families that matter for the brief:**

| Dimension | Claude (Opus 5.5) | OpenAI (GPT-5.5 / GPT-6 / Codex) |
|---|---|---|
| Structure | XML tags to separate instructions, context and inputs ([Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)) | Markdown section headers in the GPT-5.5 skeleton; XML-ish spec blocks improved adherence for GPT-5 at Cursor ([GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5), [GPT-5](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide)) |
| Thinking control | `effort` parameter, default `medium`; avoid "think carefully" and "write out your reasoning" lines | `reasoning.effort`, default `medium`; raise only on measured gains; avoid CoT prompts |
| Output length | Prompt for it explicitly; effort doesn't control visible length (Opus 5) | `text.verbosity` parameter, plus prompt guidance |
| Output format | Structured outputs or strict tools | Structured Outputs or `--output-schema`; keep schemas out of prose |
| Absolutes | Avoid aggressive emphasis; explain why | ALWAYS/NEVER only for invariants; decision rules elsewhere |
| Typical default to correct | Opus 5/5.5: delegates readily, may widen scope, over-verifies if told to | GPT-6 Astra: asks clarifying questions, delegates less, over-tests; very sensitive to AGENTS.md and skill conflicts |
| Legacy progress prompting | Remove forced interim summaries (Opus 4.8, Sonnet 5) | Remove "upfront plan / preamble" prompting in Codex: it can cause abrupt stops |

---

## 8. When to constrain and when to leave freedom

| Situation | Constrain explicitly (and, where possible, enforce in code) | Leave to the model's judgment | Basis |
|---|---|---|---|
| Irreversible, destructive or shared-state actions (push, delete, deploy, spend) | Hard rule plus a hook, sandbox or permission. Prose alone is not enough. | — | [Memory docs](https://code.claude.com/docs/en/memory); [constitution criteria](https://www.anthropic.com/constitution); [Control Illusion](https://arxiv.org/abs/2502.15851) |
| Output consumed by code (handoff payloads) | Schema-enforced (structured outputs or `--output-schema`) with an explicit "blocked" path | Wording of free-text fields | [OpenAI SO](https://developers.openai.com/api/docs/guides/structured-outputs); [Codex](https://learn.chatgpt.com/docs/non-interactive-mode) |
| Interface between agents | Objective, boundaries, return format and return size | How the delegate does the work | [Anthropic multi-agent](https://www.anthropic.com/engineering/multi-agent-research-system); [MAST](https://arxiv.org/abs/2503.13657) |
| Definition of done and stopping | Success criteria and stop rules, plus an external check (tests, Stop hook) | Which intermediate checks to run | [GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5); [best practices](https://code.claude.com/docs/en/best-practices) |
| Cost, time and concurrency | Deterministic caps and timeouts | Pacing within the budget (an advisory budget is fine) | [Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5); [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) |
| Scope of change (files, features) | Explicit scope; literal models won't infer it, and Opus 5 may widen it | Routine judgment calls inside the scope | [Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8); [Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |
| Facts the model cannot infer (new APIs, local conventions, commands) | State them compactly; keep them always available if critical | — | [Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals); [Gloaguen](https://arxiv.org/abs/2602.11988) |
| Recurring failure seen in evals | A targeted instruction naming the specific failure (a "gotcha") | — | [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5); [claude.dev skills post](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/) |
| Fragile exact sequences (migrations, release mechanics) | Low freedom: a script with fixed flags | — | [Skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) |
| Approach, search strategy, decomposition, reasoning | — | High freedom plus heuristics and the reason behind them | [GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5); [Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) |
| Tool selection and tool-call counts | Good tool descriptions and examples | When and how often to call; avoid "if in doubt, use X" | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices); [GPT-5](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide) |
| Self-verification depth | Require *evidence* (commands run, outputs) | Don't add "double-check" boilerplate on Opus 5+ | [Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5); [Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) |
| Human-facing prose style | Light guidance with positive examples | Most choices | [Opus 4.8](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8) |
| Small or cheap model, or low or minimal effort | More explicit planning and procedure is acceptable | — | [GPT-5 guide](https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide); [SkillsBench](https://arxiv.org/abs/2602.12670) |
| Untrusted content (web pages, pasted text, tool results) | Mark it as untrusted *and* enforce permissions | — | [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) |

---

## 9. Implications for the opus-orchestrator mechanism

The evidence implies three layers with different degrees of prescription:
- **Opus's judgment** (prose, high freedom): whether, when and what to delegate, and how to decompose the work.
- **The delegation contract** (prose template plus schema, medium freedom): what every brief and every result must contain.
- **Mechanics and invariants** (code, low freedom or none): invocation flags, sandboxing, timeouts, caps, schema validation, logging, destructive-action guards.

### 9.1 Put the hard parts in code (plugin scripts, hooks, settings)

1. **Wrapper script, not prose, for invoking the OpenAI side.** A single `scripts/delegate.*` should:
   - fix the safety-relevant flags (sandbox/approval mode, model, reasoning effort);
   - pass a JSON Schema for the result;
   - enforce a wall-clock timeout;
   - run each delegate in its own worktree or directory, since parallel agents editing the same files overwrite each other ([agent teams](https://code.claude.com/docs/en/agent-teams));
   - write full logs and artifacts to disk;
   - return only a compact result to Opus.

   This is the "low freedom / narrow bridge" case ([skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). Which exact CLI or SDK flags to use is out of scope here (see the orchestration-tooling research).
2. **Schema-validate every returned result.** Include `status: done | partial | blocked` so the delegate is never forced to invent a "done" ([OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)). On invalid output, retry once, then report failure.
3. **Hooks for invariants.**
   - A PreToolUse hook blocks direct calls to the OpenAI CLI that bypass the wrapper, and blocks destructive git or file operations by delegates.
   - A Stop or TaskCompleted hook gates on the project's checks where the task warrants it ([best practices](https://code.claude.com/docs/en/best-practices), [agent teams](https://code.claude.com/docs/en/agent-teams)).
4. **Deterministic caps.** Set maximum concurrent delegations, maximum per-session spend and time, and Claude Code's own `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` and `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` where Claude subagents are involved ([Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)). A time or cost budget mentioned in a brief is advisory only.

### 9.2 The orchestrator skill (read by Opus 5.5): short and explanatory, not procedural

- **Length budget.** Keep the body to about 80–200 lines (roughly 1.5k–3k tokens). The hard ceilings are 500 lines and 5,000 tokens ([spec](https://agentskills.io/specification), [best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). Keep everything essential in the first ~5,000 tokens, because Claude Code re-attaches only that much of each skill after compaction ([skills](https://code.claude.com/docs/en/skills)). Keep the brief template, result schema and gotchas in reference files one level deep.
- **Description.** Write the description as a trigger condition, not a summary ([claude.dev skills post](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)). Front-load the trigger, because Claude Code truncates the description plus `when_to_use` at 1,536 characters ([skills](https://code.claude.com/docs/en/skills)). The spec caps descriptions at 1,024 characters.
  - Because on-demand skills are the fragile link (56% non-invocation in [Vercel's](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) test), add a 2–4 line pointer in CLAUDE.md saying the delegation capability exists and when it applies.
  - Tune the description with eval prompts ([skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)).
- **What the body should contain.**
  - **When delegation pays off,** stated as heuristics with reasons: independent, sizeable, well-specifiable work; tasks where a second model family adds value. Do not delegate work finishable in a handful of tool calls, since Opus 5.x already over-delegates ([Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)).
  - **The brief contract,** described in 9.3.
  - **How to review returns:** check evidence, run the checks yourself, and flag only gaps that affect correctness. Anthropic warns that reviewers "prompted to find gaps will usually report some", which leads to over-engineering ([best practices](https://code.claude.com/docs/en/best-practices)).
  - **A Gotchas section,** grown from observed failures.
- **What to leave out:**
  - "CRITICAL / MUST" emphasis (at most one IMPORTANT line);
  - step-by-step orchestration recipes;
  - "think carefully" and "explain your reasoning" lines;
  - generic self-verification instructions;
  - restatements of what Opus already does.

  Each of these is explicitly discouraged for current Claude models ([best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), [Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5), [Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)).
- **Cross-model review is not self-verification.** Anthropic's "don't use subagents to verify your own work" targets redundant self-checks. Independent review of *another model's* output is the separate-evaluator pattern that keeps catching real gaps ([Harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps)). Make it a deliberate, named mode rather than a reflex.

### 9.3 Delegation briefs to OpenAI models: an outcome-first contract, written once

Give Opus a *default* template (medium freedom: "use this shape; adapt to the task"). It mirrors OpenAI's GPT-5.5 skeleton and Anthropic's four required elements:

```text
# Goal
<1–2 sentences: the outcome, and why it matters / what consumes it>

# Context the delegate cannot infer
- Repo/worktree, entry points, relevant files (paths, not pasted contents)
- Facts, conventions, or decisions already made (do not revisit)

# Success criteria
- <observable conditions>; validation: run `<command>` — done means it passes

# Constraints
- Scope: <files/dirs you may change>; out of scope: <...>
- Invariants (true NEVERs only; also enforced by the sandbox): <...>
- This brief takes precedence over AGENTS.md or skill guidance if they conflict.

# Output
Final message must match the provided JSON schema (status, summary, files_changed,
checks_run with results, assumptions, open_questions).

# Stop rules
- Stop when success criteria are met; don't broaden tests beyond the change.
- Make reasonable assumptions for non-blocking ambiguity and record them.
- If blocked (missing info, destructive step needed), stop with status "blocked"
  and the smallest question that would unblock you.
```

Notes on this template:
- **Scale the brief with the task.** A few hundred words plus file pointers is typical; let the delegate read files itself rather than pasting them. This is a recommendation inferred from the context-length evidence ([Levy et al.](https://arxiv.org/abs/2402.14848), [Chroma](https://www.trychroma.com/research/context-rot)), not a measured optimum.
- **Never send the spec piecemeal.** If a delegate goes off-track twice, re-issue a better brief in a fresh run rather than stacking corrections ([Laban et al.](https://arxiv.org/abs/2505.06120), [best practices](https://code.claude.com/docs/en/best-practices)).
- **No process steps unless the path itself is a requirement** ([GPT-5.5](https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5)).
- **No preamble or plan requests** for Codex models ([Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).
- **Control reasoning effort and verbosity through parameters** set by the wrapper, not through prose.
- **Precedence line.** The explicit statement that the brief overrides AGENTS.md and skill guidance follows OpenAI's GPT-6 advice to "make the priority of user instructions and skills explicit" ([GPT-6](https://developers.openai.com/api/docs/guides/latest-model)). Its effect for AGENTS.md conflicts specifically is untested here; repository AGENTS.md files should be audited so they don't contradict typical briefs.
- **Initiative line for unattended runs.** For GPT-6-class delegates in non-interactive runs, include a short initiative line ("bias toward action; proceed with reversible steps; record assumptions"). Astra otherwise tends to stop and ask questions that nobody is there to answer ([GPT-6](https://developers.openai.com/api/docs/guides/latest-model)).

### 9.4 Length budgets at a glance

| Artifact | Budget | Source |
|---|---|---|
| Skill `description` | ≤1,024 chars (spec); front-load the trigger, since Claude Code truncates at 1,536 combined with `when_to_use`, and Codex shortens descriptions once the skill list exceeds 2% of context or 8,000 chars | [spec](https://agentskills.io/specification), [Claude Code skills](https://code.claude.com/docs/en/skills), [Codex skills](https://learn.chatgpt.com/docs/build-skills) |
| SKILL.md body | Recommended ~80–200 lines; hard ceiling 500 lines and <5,000 tokens; essentials within the first 5,000 tokens | [spec](https://agentskills.io/specification), [Claude Code skills](https://code.claude.com/docs/en/skills) |
| CLAUDE.md / AGENTS.md | <200 lines (Claude Code); Codex caps the combined chain at 32 KiB by default | [memory](https://code.claude.com/docs/en/memory), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |
| Subagent descriptions | Short; Claude Code warns above 15,000 tokens combined | [subagents](https://code.claude.com/docs/en/sub-agents) |
| Delegation brief | One screen for typical tasks (recommendation, not measured) | Inferred from sections 2 and 7 |
| Returned result | ~1,000–2,000-token summary; full logs and diffs on disk | [Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |

### 9.5 Treat instructions as code: evals first, prune on model upgrades

- **Before writing the skill, build at least 3 evals and a no-skill baseline.** Then add only instructions that close a measured gap ([skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). Run them at the effort levels you'll ship, since Opus 5.5 defaults to `medium` ([Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)).
- **On every model upgrade on either side,** re-run the evals with and without each instruction block, and delete what the base model no longer needs ([skill-creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills), [Harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps)). Run `/doctor prompt-audit` to find stale or conflicting instructions ([memory](https://code.claude.com/docs/en/memory)).
- **Log skill invocations** (Anthropic uses a PreToolUse hook for this) to detect under- or over-triggering ([claude.dev skills post](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)).

### 9.6 Open questions to test in this repo (no direct evidence found)

1. Whether an explicit "brief overrides AGENTS.md" precedence line actually changes GPT-6.x or Codex behavior when the two conflict.
2. Whether Codex's "don't prompt for preambles" advice, written for `gpt-5.3-codex`, still holds for GPT-6.x Codex models.
3. The optimal brief length for GPT-6.1 Sol and GPT-6 Luna, and whether Luna (the smaller model) benefits from more procedural briefs, as SkillsBench and the GPT-5 minimal-reasoning guidance suggest for weaker configurations.
4. Whether a CLAUDE.md pointer measurably improves orchestrator-skill triggering for Opus 5.5, as Vercel's result suggests.

---

## Verification notes (claims that could not be fully verified)

- **"Curse of Instructions" (Harada et al., OpenReview 2024):** OpenReview blocked automated access. The per-model numbers circulating for it (e.g., Claude 3.5 Sonnet 44% → 58% with self-refinement; the P(all) = P(one)^n framing) were seen only on secondary sites. The arXiv successor ([2509.21051](https://arxiv.org/abs/2509.21051)) was verified only at abstract level.
- **MAST category shares (~44% / ~32% / ~24%) and per-mode percentages:** read from a model-summarized rendering of the paper's figure, not checked against the original figure. Treat them as approximate. The intervention numbers (+9.4%, +15.6%) come from the same rendering.
- **Gloaguen et al. figures:** the latest version (v3, Sep 2026) reports −0.5% / −2% for LLM-generated files and +2.4% (p = 0.21) for developer-written files. Some secondary sources cite "+4%", which may come from v2. Only v1 and v3 were checked.
- **Release dates:** none found for Claude Opus 5.5 or GPT-6 Astra; the docs pages checked don't state them. The GPT-5 prompting guide page carries no date.
- **Thariq Shihipar's skills post:** dated Jun 3, 2026 on claude.dev, where claude.com redirects. A secondary search result suggests it first appeared on X in March 2026; not verified.
- **"Let Me Speak Freely?":** the result that format restrictions hurt reasoning ([Tam et al. 2024](https://arxiv.org/abs/2408.02442)) is known to be contested by practitioners; the rebuttal was not reviewed. It is not relied on above.
- **Agent-environment claims (whether Claude Code currently injects a delegation instruction, Codex flag names beyond `--output-schema`):** taken from the docs cited and not tested locally.

---

## Sources

**Anthropic: documentation (live 2026-10-05)**
- Prompting best practices (covers Opus 5.5, Fable 5.x and others): https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Prompting Claude Opus 5.5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- Prompting Claude Opus 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- Prompting Claude Opus 4.8: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8
- Prompting Claude Sonnet 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5
- Prompting Claude Fable 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- What's new in Claude Opus 5.5: https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5
- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Claude Code, memory / CLAUDE.md: https://code.claude.com/docs/en/memory
- Claude Code, best practices: https://code.claude.com/docs/en/best-practices
- Claude Code, skills: https://code.claude.com/docs/en/skills
- Claude Code, subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code, agent teams: https://code.claude.com/docs/en/agent-teams
- Agent Skills specification: https://agentskills.io/specification

**Anthropic: engineering and blog posts**
- Building effective agents (Dec 19, 2024): https://www.anthropic.com/engineering/building-effective-agents
- How we built our multi-agent research system (Jun 13, 2025): https://www.anthropic.com/engineering/multi-agent-research-system
- Writing effective tools for agents (Sep 11, 2025): https://www.anthropic.com/engineering/writing-tools-for-agents
- Effective context engineering for AI agents (Sep 29, 2025): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Equipping agents for the real world with Agent Skills (Oct 16, 2025): https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Introducing advanced tool use (Nov 24, 2025): https://www.anthropic.com/engineering/advanced-tool-use
- Effective harnesses for long-running agents (Nov 26, 2025): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Improving skill-creator (Mar 3, 2026): https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills
- Harness design for long-running application development (Mar 24, 2026): https://www.anthropic.com/engineering/harness-design-long-running-apps
- Lessons from building Claude Code: how we use skills (Thariq Shihipar): https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/
- Claude's constitution: https://www.anthropic.com/constitution

**OpenAI**
- GPT-5 prompting guide: https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide
- GPT-5.1 prompting guide: https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-1_prompting_guide
- GPT-5.2 prompting guide: https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-2_prompting_guide
- Using GPT-5.5 (prompt guidance): https://developers.openai.com/api/docs/guides/prompt-guidance?model=gpt-5.5
- Using GPT-6 (latest model): https://developers.openai.com/api/docs/guides/latest-model
- Reasoning best practices: https://developers.openai.com/api/docs/guides/reasoning-best-practices
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Codex prompting guide (gpt-5.3-codex): https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide
- Codex, AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex, prompting: https://learn.chatgpt.com/docs/prompting
- Codex, build skills: https://learn.chatgpt.com/docs/build-skills
- Codex, subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex, non-interactive mode: https://learn.chatgpt.com/docs/non-interactive-mode

**Google**
- Gemini 3 developer guide: https://ai.google.dev/gemini-api/docs/gemini-3
- Prompt design strategies: https://ai.google.dev/gemini-api/docs/prompting-strategies

**Papers and independent studies**
- Jaroslawicz et al., How Many Instructions Can LLMs Follow at Once? (IFScale), 2025: https://arxiv.org/abs/2507.11538
- Harada et al., When Instructions Multiply (ManyIFEval), 2025: https://arxiv.org/abs/2509.21051
- Qi et al., AgentIF, 2025: https://arxiv.org/abs/2505.16944
- Levy, Jacoby, Goldberg, Same Task, More Tokens, ACL 2024: https://arxiv.org/abs/2402.14848
- Du et al., Context Length Alone Hurts LLM Performance Despite Perfect Retrieval, 2025: https://arxiv.org/abs/2510.05381
- Hong, Troynikov, Huber (Chroma), Context Rot, 2025: https://www.trychroma.com/research/context-rot
- Liu et al., Lost in the Middle, TACL 2023: https://arxiv.org/abs/2307.03172
- Shi et al., LLMs Can Be Easily Distracted by Irrelevant Context, ICML 2023: https://arxiv.org/abs/2302.00093
- Laban et al., LLMs Get Lost in Multi-Turn Conversation, 2025: https://arxiv.org/abs/2505.06120
- Sclar et al., Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design, ICLR 2024: https://arxiv.org/abs/2310.11324
- He et al., Does Prompt Formatting Have Any Impact on LLM Performance?, 2024: https://arxiv.org/abs/2411.10541
- Geng et al., Control Illusion: The Failure of Instruction Hierarchies, AAAI 2026: https://arxiv.org/abs/2502.15851
- Sprague et al., To CoT or not to CoT?, ICLR 2025: https://arxiv.org/abs/2409.12183
- Liu et al., Mind Your Step (by Step), 2024: https://arxiv.org/abs/2410.21333
- Li et al., When Thinking Fails, 2025: https://arxiv.org/abs/2505.11423
- DeepSeek-AI, DeepSeek-R1, 2025: https://arxiv.org/abs/2501.12948
- Tam et al., Let Me Speak Freely?, 2024: https://arxiv.org/abs/2408.02442
- Gloaguen et al., Evaluating AGENTS.md, 2026: https://arxiv.org/abs/2602.11988
- Lulla et al., On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents, 2026: https://arxiv.org/abs/2601.20404
- Khatri, Do Context Files Help Coding Agents?, 2026: https://arxiv.org/abs/2607.27250
- Shepard & Albrecht, Probe-and-Refine Tuning of Repository Guidance, 2026: https://arxiv.org/abs/2606.20512
- SkillsBench, 2026: https://arxiv.org/abs/2602.12670
- Chen et al., SkillJuror, 2026: https://arxiv.org/abs/2606.11543
- Xu et al., The Devil Is in the Interface, 2026: https://arxiv.org/abs/2608.11386
- Zhang et al., Agentic Context Engineering (ACE), 2025: https://arxiv.org/abs/2510.04618
- Cemri et al., Why Do Multi-Agent LLM Systems Fail? (MAST), 2025: https://arxiv.org/abs/2503.13657
- Vercel (Jude Gao), AGENTS.md outperforms skills in our agent evals, Jan 27, 2026: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
