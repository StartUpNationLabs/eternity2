---
tags: [concept, structural-invariant, generator]
status: built
origin-vol: 5
---

# Rare-color rule (opposite-edge invariant)

**Status**: `built` (vol-5 invariant, vol-7 generator rule, vol-13 geography)
**Origin**: vol-5 (100% matched invariant), vol-7 (Selby-Riordan opposite-edge rule), vol-13 (border-ring exclusivity)

## Statement 1: 100% matched invariant (vol-5)

In every plateau board (score ≥ 440) examined across 29 boards from 6 independent solver families: **all rare-color edges (colors 1–5, 24 edges each) are matched.** Every mismatch in plateau boards is on an **abundant color** (6–22, 48–50 edges each).

This is empirical not theoretical, but extremely robust. The "30-mismatch budget" identified in vol-5 lives entirely in the abundant subspace.

## Statement 2: Opposite-edge rule (vol-7, generator rule)

In the Selby-Riordan generator (the canonical E2 piece set): **rare colors {1–5} never appear adjacent within a single piece.** A piece carrying a rare color carries it only on edges that face *opposite* the piece's other rare color (if any) — never adjacent.

This is a **generator design choice** by Selby & Riordan (2000), not in the published community knowledge (vol-8 corpus mining). The rule has propagator implications:
- A piece placed with a rare color on (say) the north edge constrains its south edge by 22/23 vs 1/5.
- Stripe-extension propagators based on this rule are **logically vacuous** on canonical E2 (vol-13): interior pieces have 0 rare edges by Statement 3 below.

## Statement 3: Border-ring exclusivity (vol-13)

All **120 rare-color edges** live on the **60-piece border ring's INTERNAL matchings** (edges between border pieces).

- 196 interior pieces have **0** rare edges.
- 56 edge pieces have 2 rare edges each (E + W).
- 4 corner pieces have 2 rare edges each.

→ The rare-color matching sub-problem is **entirely on the border ring**. Interior search never sees a rare color.

## Why this is a key structural finding

- Rare colors are matched 100% in all plateau boards (vol-5).
- Rare colors only appear on the border (vol-13).
- → **The border is "easy"** (or at least: solved by every plateau solver). The 30-mismatch budget that prevents 480 lives entirely in interior abundant-color matchings.

This sharpens the search target: **focus repair on interior abundant-color mismatches**. Vol-17's WorstBand / ComponentDestroy ALNS operators implicitly do this; the rule explains why they work.

## Linked concepts

- [[selby-riordan-generator]] — the generator with this rule baked in
- [[boundary-mps]] — discovered the border-ring exclusivity as side effect
- [[alns]] — the operators that exploit this implicitly

## Linked memory

- `project_e2_rare_opposite_rule`
- `project_e2_rare_color_geography`
