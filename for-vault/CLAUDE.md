# Newsletter Synthesis Instructions

## Task

Read all files in `Newsletters/YYYY-MM-DD/` for today's date and write a synthesis brief to `Briefs/YYYY-MM-DD.md`.

Your job is **synthesis, not summary**. When the same story appears across multiple sources, collapse it into one attributed item. Surface only what matters. Do not pad.

## What to keep

- Reinforcement learning (algorithms, papers, benchmarks)
- Agentic AI and agent design (memory, planning, tool use, multi-agent systems)
- ML research: LLMs, diffusion models, unlearning, alignment, training techniques, evals
- Anthropic news (models, policy, research, org)
- AI startup and funding news
- Significant model releases or capability jumps from any lab

## What to skip

- Crypto and web3
- Trivial product updates: rate-limit increases, support-tier extensions, minor pricing tweaks, UI polish
- Pure business fluff: earnings calls with no technical substance, generic "AI will change everything" takes
- Anything without a concrete technical or strategic angle

## Voice and format

- Dry, technical, no jargon explanations — assume the reader knows the field
- Lead with the most important item
- Attribute every item to its source newsletter(s)
- One brief paragraph per item, or a tight bullet if the item is minor
- No intro sentence ("Here is today's brief"), no outro ("That's all for today")

## Output format

```markdown
# YYYY-MM-DD

**[Story headline]** ([Source])
One to three sentences. What happened, why it matters, any numbers worth knowing.

**[Story headline]** ([Source 1], [Source 2])
Collapsed from two sources. Lead with the unique angle each added.

- **[Minor item]** ([Source]) — one line.
```

Create `Briefs/` if it does not exist.
