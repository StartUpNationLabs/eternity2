# REMINDER — binding user directives (2026-05-17)

These were issued during vol-122 after vol-121 saturated "anchor on existing basin" approaches. Any autonomous run reading this BEFORE starting work must respect them.

## Directive 1 — STOP mixing previous 459 / 469 basins

> "STOP trying to just mix our previous 459 and 469!!! Really stop."

Forbidden patterns:
- ALNS on McGavin / vol-60 459 / vol-32 458 / bseed9 460 / vol-121 458 / any existing high-score board hoping to lift it
- MIP region-of-existing-basin (cluster repair, halo-N joint, top-N rows)
- Corpus-mix MIP (vol-112 / vol-119 T5 paradigm)
- σ-cycle subset application between existing basins
- "Add basin X to corpus, re-run vol-XYZ MIP, hope for Δ>0"

These were all exhaustively tried in vol-44 / vol-83-100 / vol-119 / vol-120 / vol-121. They all return Δ=0. They are **proven dead ends**.

## Directive 2 — Engineering/inventor mode for a MONTH

> "Go into engineering / inventor mode again. You have month of time!"
> "Even if you spend 5 days on an inveiton is is ok, you have 1 month !"

Operating rules:
- Spending 5 days on a single invention is OK and expected.
- Don't pre-estimate "too long" or "weeks-long" and skip; CLAUDE.md no-limiting-thoughts rule applies.
- Don't fall back to "comfort lottery" (more seeds, more parallel, more budget on the same operator class). That's the anti-pattern vol-43-reframing called out.

## What to do instead

Read `vault/plans/INVENTIONS_BACKLOG.md`. Pick the topmost `unbuilt` or `partial` invention (bias to `partial` for momentum). Build it. Take 1-5 days. Document as you go (per CLAUDE.md "take research notes AS YOU GO").

## Audit checklist for the autonomous run

Before starting any task, ask:
1. **Does this task ANCHOR on an existing 459/469 board?** If yes, it violates directive 1. Pick something else.
2. **Is this comfort-lottery (same operator + more seeds/budget)?** If yes, pick something else.
3. **Is this from INVENTIONS_BACKLOG.md (or a genuine new invention I'm logging there)?** If yes, proceed.

A 6-hour cron job is also scheduled in-session to re-surface this reminder. If you don't see cron-fired reminders, re-check by reading this file directly.

## Last updated

2026-05-17 (vol-122 opening).
