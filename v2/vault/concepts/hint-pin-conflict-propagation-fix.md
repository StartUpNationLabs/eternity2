---
name: hint-pin-conflict-propagation-fix
description: "Vol-118 T5 — fixes a bug in vol-117 T1's solve_blackwood_sized_pinned where pinned cells' forced mismatches were propagated into conf[depth], causing depth-35 wedge under any non-trivial schedule with conflicts_allowed[0..200]=0. Fix: carry conf forward unchanged at pinned cells (forced mismatches are structural, not chargeable to the break-index budget). Unlocks the full schedule+pin path. Empirical: v17a max_depth jumps from 35 (wedge) to 192 (full board minus 64)."
metadata:
  type: project
---

# Hint-pin conflict propagation fix (vol-118 T5)

**Status**: `built` — bug found + fixed in solve_blackwood_sized_pinned.

## The bug

Vol-117 T1's `solve_blackwood_sized_pinned` computed at pinned cells:

```rust
let candidate_conf = ((p_top != top_color) as u32) + ((p_left != left_color) as u32);
let prev_conf = conf[depth-1];
let new_conf = prev_conf + candidate_conf;
conf[depth] = new_conf;
```

This propagated the pinned hint's forced mismatches into `conf[depth]`,
which is used at LATER depths for the conflict-budget check:

```rust
let allowed_here = conflicts_allowed[depth];
let prev_conf = conf[depth-1];
let use_relaxed = allowed_here > 0 && prev_conf < allowed_here;
// ...
if new_conf > allowed_here { continue; }
```

The schedule `conflicts_allowed[0..200] = 0` (no break-index activates
before depth 200). So if a pinned hint at depth 34 introduces 1-2
forced mismatches, `conf[34]` becomes 1-2. At depth 35, `prev_conf=2`
and `allowed_here=0`, so EVERY candidate fails `new_conf > 0` → no
candidate placeable → backtrack.

The DFS gets stuck reaching depth 35 from depth 0-33 over and over,
score never exceeds the matches achievable in those 35 cells (~47/480).

## The fix

Pinned cells are FORCED placements. Their mismatches at the pinned
position are STRUCTURAL — they exist regardless of the break-index
budget. So `conf[depth_pinned]` should be `conf[depth_pinned - 1]`
UNCHANGED.

```rust
let new_conf = prev_conf;  // Pinned cells: structural mismatches, not budgeted.
conf[depth] = new_conf;
```

## Empirical impact

10s budget on canonical 16×16 + 5/5 hints:

| variant                                | max_depth | score | hints |
|----------------------------------------|----------:|------:|------:|
| v17a + pin (before fix)                |        35 |    47 |    5/5 |
| v17a + pin (after fix)                 |       192 |   338 |    5/5 |
| v17a_hint + pin (after fix)            |       192 |   338 |    5/5 |
| raw + pin (no schedule, vol-113)       |       192 |   350 |    5/5 |

The schedule path NOW reaches the same depth as raw+pin. Score is
slightly LOWER (338 vs 350) — schedule prunes branches that would
boost raw matched-edges in this regime.

The 192/256 cells = 64 cells short of full placement. This is a
search-time ceiling at 10s; longer budgets should fill more cells.

## verify_records.sh

5/5 hints OK at every pipeline stage.

## Implication

The schedule+pin path is now operational for strict-canonical work.
Future direction: hint-aware schedule recalibration (vol-117 T5
sketch) may further help score density; current evidence shows
the bottleneck is now ALNS recovery from the partial.

## Code

- `crates/blackwood-fast/src/lib.rs::solve_blackwood_sized_pinned`
- `crates/blackwood-fast/src/schedule.rs::blackwood_schedule_calibrated_v17a_hint_aware`

## Linked

- [[schedule-hint-interaction]] — the vol-117 T1 finding this fixes.
- [[blackwood-schedule-calibration]] — schedule origins.
- [[hint-compliance-clarification]] — strict-canonical convention.
- [[../sessions/vol-118]].
