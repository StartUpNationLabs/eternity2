# V180 INTAGLIO-ATTACK — Lex-ordered ALNS with Forbidden-2x2 Secondary

Status: `partial` — code exists (V140 lex_break_intaglio), CLI wired 2026-05-20.
Origin: vol-180 (this volume)
Files: `crates/localsearch/src/alns.rs::lex_break_intaglio`, `crates/bench-audit/src/bin/alns_only.rs::--lex-intaglio`.
Naming: **INTAGLIO** — Italian "carved" — from V138/V139 forbidden-2x2 analysis.

## Motivation

The 460-attractor basin has been shown to be an *iso-score plateau*: ALNS at k=8-16 returns to score 460 after every destroy+repair, exploring iso-460 states without escape.

V139 INTAGLIO finding (2026-05-19): in 1278-board corpus, score-tier vs median forbidden-2x2 count:

| Score tier | Median forbidden-2x2 |
|---|---|
| <440 | 109 |
| 440-459 | 60 |
| ≥460 | **29** |
| 480 (target) | **0** |

The 461 record has ~29 patches; a hypothetical 480 has 0. Each forbidden patch is 4 pieces in a 2x2 that cannot ALL match locally (color constraints make it provably infeasible). To reach 480, ALL 29 patches must be eliminated.

## Math

For board $b$, define:
- Primary objective: $f_1(b) = \text{matched-edges}(b)$.
- Secondary objective: $f_2(b) = -|\text{forbidden-2x2}(b)|$ (negative because we minimize patches).

Lex-ordered acceptance: when $\Delta f_1 = 0$ (iso-score move), accept iff $\Delta f_2 > 0$ (fewer patches). When $\Delta f_1 > 0$, always accept. When $\Delta f_1 < 0$, fall back to SA-Metropolis.

Mathematically, this is *lexicographic optimization* — the SA random walk explores the iso-score manifold preferentially toward states with fewer forbidden patches. Since 480 boards have 0 patches, this is a *descent direction in the right geometric quantity*.

### Why iso-score moves matter

V169 measured: 30-min ALNS with `basic_lkh + PriorDestroy` made 1100+ moves on a 460 base. All 1100+ were 100% accepted by SA at t=1.0 (since equal-score moves auto-accept). Final board: IDENTICAL to base.

With `--lex-intaglio`, only iso-score moves that REDUCE patches are accepted. The walk becomes a guided descent in forbidden-2x2 count, breaking the symmetric iso-460 random walk into a directed search.

### Hypothesis

If the 460 plateau has a "narrow neck" where some iso-460 boards have fewer patches than others, the lex-walk discovers it. From that lower-patch iso-460, further patches can be reduced by 1-3 score drops at first, but then re-climb the score via standard ALNS as fewer patches make more configurations feasible.

## Implementation

- `lex_break_intaglio` in alns.rs (V140, already there) — checks `count_forbidden_2x2` on iso-score moves.
- `--lex-intaglio` CLI flag on alns_only (added 2026-05-20).
- Used in V169-v2 and V175-LONG-LIFT drivers.

## What's still open

- Triple-lex: (matched, -forbidden_2x2, -mismatch_components)?
- Cost: forbidden-2x2 count costs O(N) per call (256 cells × 2 patches each = 512 lookups). Negligible vs repair cost (~ms).
- Should the LEX_INTAGLIO threshold be: "Accept any iso-score move with fewer OR EQUAL patches"? More permissive.
- Should we ALSO REJECT improving-score moves that INCREASE patches by ≥k? (Pareto-frontier acceptance.)

## What this is NOT

This is NOT a constructive method — it doesn't construct a 480 board. It guides EXPLORATION within the 460 plateau toward forbidden-2x2 minima, hoping that those minima are gateway states to 461+.

If the corpus shows that even 461+ basins have ~29 forbidden patches, then INTAGLIO-ATTACK won't reduce patches below ~29 (the plateau itself has that floor). But it would still find the *minimum-patch* 460 board, which is the best candidate for a basin-hop to 461+.

## Linked

- [[../sessions/vol-180]] (planned)
- [[prior-guided-alns]] (V169 — combined with INTAGLIO-ATTACK in long-lift driver)
- `project_e2_intaglio_2x2_finding` (memory file)
