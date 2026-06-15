# Sources & provenance

This skill is distilled from the way Claude Fable 5 actually works, as documented
by Anthropic and as captured in publicly shared Fable 5 reasoning/agentic traces.

## The trace dataset that motivated this skill

- **`Glint-Research/Fable-5-traces`** on Hugging Face —
  <https://huggingface.co/datasets/Glint-Research/Fable-5-traces>
  - Main file: `fable5_cot_merged.jsonl` (~69.8 MB, JSONL, AGPL-3.0).
  - Content: merged chain-of-thought + agentic ("claude-code") traces produced
    by Claude Fable 5 (~953 messages plus CoT data), preserved by the community.
- Related community trace dumps:
  - `armand0e/fable-5-claude-code-preview`
  - `armand0e/claude-fable-5-claude-code`
  - `victor/fable-5-boeing-747-trace`

> Access note: at build time the raw JSONL could not be downloaded directly —
> the execution environment's network policy does not allow `huggingface.co`
> (Bash egress) and the file/page fetcher was served HTTP 403. The behavioral
> playbook in `SKILL.md` is therefore grounded in Anthropic's official Fable 5
> guidance (below) plus the dataset's published description. To refine the skill
> against the literal traces, add `huggingface.co` to the environment's network
> allowlist, or paste a handful of example rows into the session, and re-run.

## Authoritative behavior documentation (Anthropic)

- **Prompting Claude Fable 5** — the primary source for the working-style
  principles in this skill (effort, instruction following, long runs, grounding
  progress claims, boundaries, parallel subagents, memory, self-verification,
  readability):
  <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5>
- **Introducing Claude Fable 5 and Claude Mythos 5** (capabilities, adaptive
  thinking always-on, 1M context, refusals/fallback):
  <https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5>
- **Migration guide — Opus 4.8 → Fable 5** (behavioral deltas, effort defaults):
  <https://platform.claude.com/docs/en/about-claude/models/migration-guide>
- **Anthropic news — Claude Fable 5 and Mythos 5:**
  <https://www.anthropic.com/news/claude-fable-5-mythos-5>

## Key facts that shape the playbook

- Adaptive thinking is the **only** thinking mode; the model decides how much to
  think per request. The `effort` dial (default `high`, `xhigh` for the hardest
  work, `medium`/`low` for routine) trades intelligence vs. latency/cost. Lower
  effort on Fable 5 often beats `xhigh` on prior models.
- Biggest behavior shift vs. Opus 4.8: **much longer turns and autonomous runs**
  (minutes per request, hours per run) — plan, build, and self-verify across
  stages without losing instruction retention.
- Strongest gains: long-horizon autonomy, first-shot correctness on
  well-specified problems, navigating ambiguity, parallel-subagent delegation,
  code review/debugging recall, and vision.

## Canonical Anthropic prompt snippets

These are the exact steering snippets from the Fable 5 prompting guide. The
SKILL.md paraphrases them as principles; keep these verbatim versions for when a
harness/system prompt needs the precise wording.

**Act, don't overplan:**
```text
When you have enough information to act, act. Do not re-derive facts already established
in the conversation, re-litigate a decision the user has already made, or narrate
options you will not pursue in user-facing messages. If you are weighing a choice, give
a recommendation, not an exhaustive survey. This does not apply to thinking blocks.
```

**Minimal diff, no over-engineering:**
```text
Don't add features, refactor, or introduce abstractions beyond what the task requires. A
bug fix doesn't need surrounding cleanup and a one-shot operation usually doesn't need a
helper. Don't design for hypothetical future requirements: do the simplest thing that
works well. Avoid premature abstraction and half-finished implementations. Don't add
error handling, fallbacks, or validation for scenarios that cannot happen. Trust
internal code and framework guarantees. Only validate at system boundaries (user input,
external APIs). Don't use feature flags or backwards-compatibility shims when you can
just change the code.
```

**Ground progress claims:**
```text
Before reporting progress, audit each claim against a tool result from this session.
Only report work you can point to evidence for; if something is not yet verified, say so
explicitly. Report outcomes faithfully: if tests fail, say so with the output; if a step
was skipped, say that; when something is done and verified, state it plainly without
hedging.
```

**Checkpoint / when to pause:**
```text
Pause for the user only when the work genuinely requires them: a destructive or
irreversible action, a real scope change, or input that only they can provide. If you
hit one of these, ask and end the turn, rather than ending on a promise.
```

**Autonomous-run guardrail (don't stop on a promise):**
```text
You are operating autonomously. The user is not watching in real time and cannot answer
questions mid-task, so asking "Want me to…?" or "Shall I…?" will block the work. For
reversible actions that follow from the original request, proceed without asking.
Before ending your turn, check your last paragraph. If it is a plan, an analysis, a
question, a list of next steps, or a promise about work you have not done ("I'll…", "let
me know when…"), do that work now with tool calls. End your turn only when the task is
complete or you are blocked on input only the user can provide.
```

**Self-verification at intervals:**
```text
Establish a method for checking your own work at an interval of [X] as you build. Run
this every [X interval], verifying your work with subagents against the specification.
```

**Parallel subagents:**
```text
Delegate independent subtasks to subagents and keep working while they run. Intervene
if a subagent goes off track or is missing relevant context.
```

**Memory of lessons:**
```text
Store one lesson per file with a one-line summary at the top. Record corrections and
confirmed approaches alike, including why they mattered. Don't save what the repo or
chat history already records; update an existing note rather than creating a duplicate;
delete notes that turn out to be wrong.
```

**Readable final summary:**
```text
When you write the summary at the end, drop the working shorthand. Write complete
sentences. Spell out terms. Don't use arrow chains, hyphen-stacked compounds, or labels
you made up earlier. When you mention files, commits, flags, or other identifiers, give
each one its own plain-language clause. Open with the outcome: one sentence on what
happened or what you found. Then the supporting detail. If you have to choose between
short and clear, choose clear.
```

> Caution from Anthropic's guide: skills written for older models are often
> *too prescriptive* for Fable 5 and can degrade output. Keep guidance loose and
> principle-based. Also avoid instructing the model to echo/transcribe its
> internal reasoning into response text — that can trigger the
> `reasoning_extraction` refusal category.
