---
name: schedule-hint-interaction
description: "Vol-117 T1 finding — Blackwood schedule + 5/5 canonical hints interact DESTRUCTIVELY at the calibration used for unhinted runs. v17a schedule (max_heuristic_index=255) wedges at depth 35 (just past first hint). bw469 schedule (max_heuristic_index=160) reaches depth 83-84 in 10-60s. Raw DFS + hints (no schedule) reaches depth 192 in 30s. Vol-118 T5 ROOT-CAUSED this as a conflict-propagation bug at pinned cells; see [[hint-pin-conflict-propagation-fix]]."
metadata:
  type: project
---

# Schedule × hint interaction (vol-117 T1)

**Status**: `superseded` — root cause identified and fixed in vol-118 T5.
See [[hint-pin-conflict-propagation-fix]].

The original framing (schedule's heuristic-edge targets are
incompatible with hint pinning) was WRONG. The actual cause was a
conflict-budget bookkeeping bug at pinned cells.

## Mechanism

Vol-117 T1 added `solve_blackwood_with_hints` →
`solve_blackwood_sized_pinned` to `crates/blackwood-fast/src/lib.rs`,
mirroring the vol-113 T1 pinning pattern but also handling the
schedule (`cum`) and break-index (`conf`) state at pinned cells:

- Pinned cells compute `conf[d] = prev_conf + forced_mismatch_count`
  (not subject to conflict budget — pins are forced placements).
- Pinned cells compute `cum[d] = prev_cum + heur_count_of[pin]` if
  schedule is active.
- Backtrack skips back through pinned cells (mirrors raw variant).

## Empirical results — canonical 5-clue + hints

Bin: `target/release/bf_bw_schedule_hinted --budget-ms B --schedule S`.

| schedule | max_heur_idx | break_idxs | 10s depth/score | 60s depth/score |
|---|---:|---:|:---|:---|
| v17a       | 255 |  12 | 35 / 47    |  (wedged, expected same) |
| bw469      | 160 |  12 | 83 / 139   | 84 / 141 |
| (raw, no schedule, vol-113) | — | — | — | depth 192 / score 350 (30s) |

All outputs `verify_records.sh`: **5/5 hints OK**.

## Why schedules wedge with pins

The v17a schedule's targets at low depths require ~21 heuristic edges
by depth 60 (i.e. cumulative heur_count of placed pieces ≥ 21). When
the first canonical hint is pinned at depth 34, the hint piece
contributes whatever `heur_count` it has (typically 1-4 of 4 sides
classified as heuristic-rare). Combined with unhinted depths 0-33,
the cumulative may already be below `target` AT a candidate-placement
step at depth ≥ 35, with no remaining candidates that satisfy the
schedule. Result: `placed=false` at depth 35, backtrack wave through
unhinted cells 33, 32, ..., 0. The DFS visits all "early-cell"
permutations without ever clearing depth 35 again.

Bw469 has `max_heuristic_index=160` (vs 255 for v17a) — gentler
heuristic constraint. It reaches depth 83-84 but stalls because
the heuristic-target curve still calibrated to unhinted runs.

## Implications

1. **Schedule calibration must include hints as inputs.** The
   community v17 calibration was derived from an UNPINNED 469
   community board, so the targets reflect what an unpinned search
   achieved. With pinning, the heur_count contribution from hints
   is FORCED at those specific depths — the target curve must
   account for that.

2. **For strict-canonical 5/5 record work, the raw DFS + pinning
   path is currently STRONGER than schedule + pinning.** This
   inverts the unhinted relationship (where schedule helps).

3. **A hint-aware schedule recalibration is the natural vol-118+
   experiment.** Take v17a's curve, ADD hint contributions to
   targets at depths ≥ 34/45/135/210/221, RE-AFFINE.

## Code

- `crates/blackwood-fast/src/lib.rs::solve_blackwood_sized_pinned` (new)
- `crates/blackwood-fast/src/lib.rs::solve_blackwood_with_hints` (entry)
- `crates/blackwood-fast/src/bin/bf_bw_schedule_hinted.rs` (test bin)

## Linked

- [[blackwood-fast]] — engine.
- [[blackwood-schedule-calibration]] — origin of v17a/bw469.
- [[hint-compliance-clarification]] — why this matters.
- [[../sessions/vol-117]] — session journal.
