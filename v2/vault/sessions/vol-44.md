# Vol-44 — LP-relaxation upper bound for border-class enumeration

**Theme**: Build the LP-relaxation UB tool flagged as the highest-EV
unbuilt direction in vol-43-reframing. Measure tightness on canonical
E2 records.

**Status (mid-vol)**: LP tool shipped + working. Initial measurements
in progress.

## What was built

- `crates/bench-audit/src/border_ub.rs` — LP formulation as a library
  function. See `vault/concepts/border-enum-lp-ub.md` for the math.
- `crates/bench-audit/src/bin/lp_smoke.rs` — toolchain smoke test.
- `crates/bench-audit/src/bin/border_lp_ub_small.rs` — validates LP
  on generated 6x6/4 and 8x8/6 puzzles.
- `crates/bench-audit/src/bin/border_lp_ub.rs` — runs LP UB on a
  canonical-E2 board JSON.
- `good_lp + highs-sys` wired into `bench-audit/Cargo.toml`. HiGHS
  built from source (via cmake) at workspace build time.

## What was measured

### Smoke tests (small generated puzzles)

| Puzzle | LP slack at solved optimum | LP solve time |
|---|---|---|
| 6x6 / 4 colors | 0.0 (tight) | 19 ms |
| 8x8 / 6 colors | 0.0 (tight) | 200 ms |

On generated puzzles where the entire board is solvable to max score,
the LP reaches max — tight.

### Canonical E2 16x16 / 22 colors

On the vol-32 458-record board's border (all 4 corners + 56 edges + 5
canonical hints):

| Metric | Value |
|---|---|
| LP variables (x) | 108352 |
| LP variables (y) | 8008 |
| LP constraints | 16413 |
| LP non-zeros | ~664k |
| IPM iterations to convergence | 27 |
| IPM time | 37s |
| Crossover time | 110s |
| **Total LP solve** | **~147s** |
| B-B match count | 60 |
| B-I forced match count | 56 |
| LP interior y-sum | 360.5 |
| **Total LP UB** | **476.5 / 480** |
| Actual integer score | 458 |
| LP-integer gap | 18.5 |

### Interpretation

1. **LP UB is informative**: 476.5 < 480, the LP detects ~3.5 I-I
   edges of structural slack from this specific border. Not 480 (which
   would mean the LP is useless).
2. **LP UB is loose vs integer**: 18.5 gap to the actual achievable
   458. The LP cannot rule out "this border admits 476" — but neither
   can we prove or disprove it from the LP alone.
3. **For B&B filtering at threshold T**:
   - T = 459 (just above the current 458 record): the 458 board's
     border passes (476.5 ≥ 459). Very loose filter.
   - T = 477: the 458 board's border is filtered out. We'd be looking
     for borders structurally better than this one.
4. **Per-LP cost ~2.5 minutes** with current HiGHS pipeline (IPM +
   crossover, 8 threads). Crossover is the slow part; skipping it
   gives the bound in 37s but returns "Unknown" status from good_lp.

## What's running (in-flight)

A multi-record LP UB sweep on all 10 verified canonical-E2 records
(2 × 458, 3 × 457, 2 × 456, 2 × 455, 1 × 454). Estimated 25 minutes
total. Will measure the spread of LP UB values across our basin.

## Open at close

If LP UB varies meaningfully across records (e.g., spread > 5
points), it indicates the LP has discriminative power and the
border-tree B&B is worth building.

If LP UB is uniform across records (e.g., all ≈ 476-477), then the
LP relaxation is mostly insensitive to micro-variations in border and
we'd need either:
- A tighter LP formulation (integer rotations, McCormick lifting)
- A different research direction entirely

## Next steps

Vol-44 continuation (in this session):
1. Wait for 10-record sweep to finish; analyze spread.
2. If spread > 5, build the B&B with LP UB at full borders.
3. If spread < 5, drop the LP B&B; pivot to dual-extraction (per-edge
   stress maps) as a structural diagnostic.

Vol-45 candidates (next session):
- No-good CDCL learning in solver-engine.
- RL self-play for value-order.
- Border-local-search with LP UB as score function.

## Linked concepts

- `vault/concepts/border-enum-lp-ub.md` — full LP math
- `vault/sessions/vol-43-reframing.md` — why we're building this
