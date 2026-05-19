# Current Volume — Vol-148

**Theme**: Multi-basin compute campaign Tier-1A — scale V129-T12's proven
recipe to all 18 basin families × 3 seeds × 2 ops × 4h budget.

V147 closed in day 1 (forbidden-2×2 post-placement DFS pruner refuted
by edge-strict-implies-feasibility analysis). Pivot to compute, which
is the only attack class with a proven record-breaking precedent
in this autonomous arc (V129-T12 → 463).

## Why this vol

V129-T12 found **463** via 18 × 30min ALNS basic seed=42 on different
basins. Three knobs untried:

1. **Longer budget per job** (30min → 4h, 8× compute per attempt).
2. **Multiple seeds** (s=1, s=7, s=42 — V125-T19 showed
   different seeds reach different ceilings, and 42 was just lucky).
3. **LKH-chain ops** (`basic_lkh` from W4, never deep-tested per basin).

Total: 18 basins × 3 seeds × 2 ops = 108 jobs × 4h = 432 CPU-hr.
On 7 cores: ~62 wallclock hours ≈ 2.6 days.

Kill-criterion: any new ≥464 record → record + analyze + commit.
At minimum: distribution of (basin, seed, ops) final scores —
a structural map of what each basin can reach under longer compute.

## Binding items (3 max)

1. **Build basin manifest**: 18 boards from V129-T11 clustering.
   Generate `scripts/v148_basin_sweep/manifest.json` with paths +
   corner-perm + init score.
2. **Sweep driver**: bash launcher that runs 7-job batches under
   `parallel` or sequential `&` with wait-for-N. Logs each to a
   timestamped subdir.
3. **Result analyzer**: per (basin, seed, ops), report
   (init, max, time-to-max). Aggregate: # ≥460, # ≥463, any ≥464.

## Kill-criterion

- Time-budget cap: 4 wallclock days. If by then no ≥464, accept the
  sweep result as a distributional finding (not a record-break) and
  move to V149.
- Any ≥464 → record + commit + reorient remaining sweep around the
  new basin.

## Days budget

4 wallclock days. Mostly compute; the driver + analyzer are <1 day.

## Linked

- [[../sessions/vol-148]] (to be created)
- [[../sessions/vol-147]] (closed)
- [[../concepts/forbidden-patch-theorem-2026-05-19]]
- [[MULTI_VOL_PLAN_2026-05-19]]
- [[../basins/basin-463]] (to be created with sweep results)
