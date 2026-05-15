# Standing 458 record — comprehensive status after vols 54-58

**Status**: stable, locally optimal across many measurements — vol-58.
**Origin**: vol-32 (`vanilla_fast` + ALNS, 2026-05-13).
**Context**: This page consolidates what's been learned about the 458
record across vols 54-58 (one autonomous session, 2026-05-15).

## What the 458 record is

**Score**: 458 matched edges out of 480 (95.4%).
**File**: `output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json`.
**Algorithm**: vanilla_fast (Rust raw-DFS backtracker) → ALNS-5min.
**Canonical compliance**: **3/5 hints obeyed** (pos 34, 45, 135 ✓;
pos 210, 221 displaced).

## What the 458 is NOT

- NOT a strict-canonical record. The strict-canonical (5-hint) record
  is **457**, found by `blackwood_raw + MRV` pipeline (vol-32 + others).
- NOT the community ceiling. Community canonical 5-clue ceiling is
  **469** (McGavin 2020, ~200 cores × days with Blackwood solver).
- NOT byte-identical to any other 458 we've found. Vol-58 lottery
  surfaced ANOTHER matched=458 board with **0/5 hint compliance** and
  agreement with vol-32 458 at only 3/256 cells — a 3rd-distinct
  basin family.

## Local optimality evidence (vols 44, 55, 58)

**The 458 (and all related basins) are locally MIP-optimal across
extensive testing**:

| Vol | Basin tested | Cluster geometries | Result |
|-----|---|---|---|
| 44 | Family A 458 | 196-cell whole interior | MIP = 458 (1h) |
| 55 | Family A 458 | 5×4, 6×3, etc. (4 locations) | MIP = current at every cluster |
| 58 T1 | Family B 457 (blackwood_mrv) | 5×4, 6×3 (2 locations) | MIP = current at every cluster |
| 58 T4 | Family B 457 grid | 5×4 at 9 locations | All MIP = current |
| 58 T5 | McGavin 469 | 5×4 at 9 locations | All MIP = current |

**Total: 22 cluster MIPs across 3 distinct basin families, all
locally optimal**.

## What the LP-MIP gap is and isn't

Vol-54 proved precise mechanism: cell-fractional x via y-min-of-sums
concavity. The LP relaxation has ~3-4 point per-cluster slack from
this mechanism (vol-55 measurements: 5×4 cluster has LP-MIP gap 3.31,
6×3 has 3.41).

**The LP-MIP gap is LP looseness, NOT 458 suboptimality.** Vol-44 and
later confirmed integer optima match the recorded scores at all
tested clusters.

## What CDCL no-good learning offers (vols 56-58)

Vol-56 measured: 96% of canonical-E2 search states have ready-to-fire
clauses post-1-UIP-minimization. Clauses average 5-9 literals.

Vol-57 prototype: Rust `eternity2-cdcl-proto` crate implementing AC-3
with cause tracking + 1-UIP + watch-filtered unit-prop.

Vol-58 T6 scaling tests:
- 5×5/4c: cdcl 3.1× fewer nodes.
- **7×7/6c: cdcl 3.4× FASTER wall-clock + finds where vanilla can't.**
- 8×8/7c: cdcl 15× fewer nodes.

**The CDCL Rust prototype is a real algorithm-level speedup**. The
remaining work is engineering (real 2WL, scale to canonical) — multi-
week effort with strong empirical justification.

## Path to >458 — what's left

After this session, the available record-breaking levers are:

1. **CDCL + 2WL in solver-engine, on canonical 16×16**. Multi-week,
   high-confidence empirical justification, no guaranteed gain.
2. **Different basin family with intrinsically higher MIP cap**. The
   vol-56 basin lottery (running) explores this; vol-58 T5 shows
   McGavin's 469 basin IS such a higher-cap family.
3. **Reach McGavin's pipeline** (Blackwood solver + Joe's prune-restart
   + scheduled relaxations + 200-cores × days). Multi-week multi-machine.

## What's been CLOSED as a record-breaking direction

- **LP tightening**: vol-44 → vol-52 (refuted) → vol-53/54 → vol-55.
  The LP-relaxation arc is fully closed.
- **Imitation learning** (vols 26-29): teacher-ceiling refutation.
- **ES / vanilla RL** (vols 48-49): argmax-invariance refutation.
- **Basin escape recipe at 30-min scale** (vol-22): ALNS-PT
  saturation.
- **Standard search-space pruning** (vols 12-25): incremental wins,
  no record break.

## Process notes

This vol-54-58 session demonstrated:
- The "autonomous research" contract is productive when properly
  framed.
- Memory + vault discipline is essential for continuity.
- 8 hours of compute produces ~5 vol-worth of deliverables.
- Math, measurement, prototype, refutation, discovery all in one
  session.

## Linked

- [[../sessions/vol-54]], [[../sessions/vol-55]], [[../sessions/vol-56]],
  [[../sessions/vol-57]], [[../sessions/vol-58]]
- [[cdcl-no-good-e2]], [[cdcl-engine-integration]]
- [[y-linearisation-cell-fractional-gap]]
- [[lp-integer-gap-anatomy]]
- [[basin-mcgavin-469]]
