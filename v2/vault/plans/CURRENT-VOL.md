# Current Volume — Vol-147

**Theme**: INTAGLIO-pruned DFS — deterministic backtracking with
forbidden-patch rejection. First vol of the [[MULTI_VOL_PLAN_2026-05-19]]
arc covering Vols 147–158.

## Why this vol

V138-V142 established the forbidden-patch theorem: 99.72% of random
2×2 patches and 100% of random 2×3 patches are infeasible on canonical
piece set under any rotation. Real boards strongly anti-correlate:

| score regime | median forbidden 2×2/board |
|--------------|----------------------------|
| LOW (<440) | 109 |
| MID (440-459) | 60 |
| HIGH (≥460) | 29 |

V140-V143 tried this as ALNS tiebreak / destroy targeting — all inert.
V145 tried it as constructive-attachment criterion (ICEBERG) — marginal.
**Untried**: as a DFS pruner. A board with 109+ forbidden 2×2 patches
cannot be on the way to a record; pruning at first violation cuts huge
subtrees.

## Binding items (3 max)

1. **Build `v147_intaglio_dfs`** in Rust. Backtracker over (cell,
   piece, rotation) with post-placement check: any complete 2×2 patch
   containing the new cell is checked against the forbidden table.
2. **Measure overhead**: nodes/sec with vs without patch-check. If
   patch-check costs <50% throughput, the pruner pays for itself.
3. **Test on 5×5/c4, 7×7/c5, 10×10/c8** scaling suite. Compare depth
   reached + max-matched against `vanilla_fast` at equal wallclock.

## Kill-criterion

If patch-check costs >2× throughput (i.e., <33% effective nps), refute
as integration-loss-dominant. Document and move to V148 (compute
campaign).

## Days budget

3 days. Day 1: forbidden-2×2 table precompute + DFS scaffold. Day 2:
integration + small-scale measurement. Day 3: canonical 24h compute or
move to V148.

## Linked

- [[../concepts/forbidden-patch-theorem-2026-05-19]]
- [[MULTI_VOL_PLAN_2026-05-19]]
- [[../sessions/vol-146-close]]
- [[STRATEGIC_REVIEW_2026-05-19]] (Tier 4 recommendation)
