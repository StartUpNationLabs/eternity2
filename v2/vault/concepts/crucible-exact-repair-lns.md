---
name: crucible-exact-repair-lns
description: CRUCIBLE (vol-207) — exact-repair LNS with global piece rebalance. Dissolve a region, re-solve it EXACTLY (MaxScore DFS) vs fixed boundary, pulling donor pieces from mismatched cells elsewhere. Result — even exact large-neighborhood repair WITH cross-region piece flow finds ZERO improving OR lateral moves on a 447 board. Strongest form yet of the σ-lock: basins are exact-repair-rigid.
status: refuted
metadata:
  type: concept
---

# CRUCIBLE — exact-repair LNS with global rebalance (vol-207)

**Status**: `refuted` (2026-06-10) as a basin-escape operator. But it produces
the STRONGEST σ-lock result in the vault: local basins are rigid even under
exact large-neighborhood repair with cross-region piece flow.

**Origin**: vol-207. Designed to attack the σ-lock that ALNS (heuristic repair)
and cluster-MaxSAT-repair (fixed-region exact) both hit. The novelty: exact
repair PLUS global piece rebalance (a re-solved region can pull pieces from
mismatched cells elsewhere, so pieces FLOW between regions — the thing
fixed-region repair cannot do).

**Files**: `crates/bench-audit/src/bin/crucible.rs`.

## The operator
1. Pick a w×w window R (random).
2. Add `rebalance` DONOR cells from mismatched cells ELSEWHERE on the board.
3. Re-solve R∪donors EXACTLY (MaxScore DFS+B&B over the cell set, pool = those
   cells' current pieces) maximizing internal + boundary matches.
4. Accept if global score improves; keep if equal (lateral); rollback if worse.

## What we measured (on the MOSAIC-447 novel basin)
- Exact window-repair, NO rebalance: 447 → 447, **0 improving moves** (= the
  cluster-repair refuted result; region is exactly locally optimal).
- Exact window-repair + rebalance=4 (cross-region flow): 447 → 447,
  **0 improving AND 0 lateral-piece-moves** over hundreds of iterations.

**0 lateral-piece-moves is the key finding:** the exact re-solve of every region
(window + donors) returns the SAME placement it started with. Pulling in donor
pieces never even ties the incumbent — donors fit their own cells better than the
window. So the board is locally optimal under EXACT MaxScore re-solve of any
≤13-cell region WITH cross-region piece flow.

## Why this matters — strongest σ-lock statement yet
Prior σ-lock evidence: ALNS plateaus (heuristic repair), cluster-MaxSAT-repair
finds local optima (fixed region). CRUCIBLE shows the lock holds under **exact
repair + global piece flow** — the strongest local operator class. This means the
458-463 plateau is NOT a repair-quality artifact: there is genuinely no improving
or lateral move at the ≤13-cell neighborhood scale, even allowing pieces to
migrate from defective regions. Consistent with and strengthening
[[sigma-cycle-universal-indecomposable]] and the Local Rigidity Theorem.

## What's still open
- Larger exact regions (16+ cells) — but solve cost explodes; the σ-cycle
  theorem predicts ~80+ simultaneous cells are needed (intractable exactly).
- Does the lock hold on a FRESH MOSAIC basin, or are some novel basins softer?
  (Untested; speculative.)
- Accepting WORSE moves (SA-style) to traverse — but ALNS already does iso-score
  walks and plateaus, so unlikely to help.

## Linked
- [[mosaic-window-maxsat]] — the novel basin it was tested on
- [[sigma-cycle-universal-indecomposable]] — the obstruction it strengthens
- [[watershed-frontier-flow]] — piece-theft / scarcity (why donors don't migrate)
- [[parquet-overlapping-patch]], [[lattice-forced-chains]] — companion negatives
