---
name: mosaic-window-maxsat
description: MOSAIC (vol-206) — a new constructive E2 solver that composes EXACT window-MaxSAT block solutions into a full board, with scarcity-aware piece reservation to fight piece-theft. From-scratch (no warm start, no ALNS) reaches 448/480; hints enforceable as hard pins (strict-canonical compatible).
status: built
metadata:
  type: concept
---

# MOSAIC — window-MaxSAT block composition (vol-206)

**Status**: `built` (Python PoC, 2026-06-09). From-scratch **448/480** with no
warm start / no ALNS / no community seed. Rust port is the next perf step.

**Origin**: vol-206, user-chosen from the "compose exact sub-solutions" frame
after the vol-203/204/205 results showed E2 has no exploitable local structure
but **sub-regions solve to optimality fast** (Anjou's tractable-window finding +
our own validation).

**Files**: `scripts/v206_mosaic/` — `window_maxsat.py` (primitive), `mosaic_soft.py`
(composition engine, the working one), `mosaic_bt.py` (block-backtracking,
perfect-block variant), `mosaic_io.py` (timestamped JSON + Bucas URL + history.csv
persistence; Bucas encoder verified vs McGavin 469). `RESULTS.md`.

## The algorithm

Tile the 16×16 board into BS×BS blocks (default 4×4 → 16 blocks), process
row-major. For each block, solve a weighted-partial MaxSAT (pysat RC2):
- vars `x[cell,piece,rot]`; hard: one placement/cell, each available piece ≤once,
  board-border respected, **canonical hints pinned** (optional, hard).
- **boundary matches are SOFT** (the key design): a block's sides facing
  already-placed neighbors are soft targets, NOT hard constraints — so a block
  NEVER goes infeasible; it pays for mismatches. This makes it a true MaxScore
  composition that always completes.
- soft: internal + boundary edge matches (weight 1 each).
- **scarcity reservation**: withhold the globally-scarcest pieces from each
  non-final block's pool (the vol-204 piece-theft fix), so later blocks aren't
  starved of the pieces their boundary demands need.

## What we measured (vol-206)

Window primitive solves blocks to OPTIMUM: 4×4→24/24 in 32s, 3×3→12/12 in 11s
(confirms Anjou's tractability). Full-board composition, from scratch:

| variant | matched / 480 |
|---|---:|
| greedy single-descent (vol-205, for reference) | ~385 |
| MOSAIC-soft, no reservation | 443 |
| MOSAIC-soft, reservation rf=0.05 | 447 |
| **MOSAIC-soft, reservation rf=0.08** | **448** |
| MOSAIC-soft, reservation rf=0.12 / 0.15 | 440 / 441 |

Degradation is **localized to the last ~3 blocks** (bottom-right corner) where the
pool depletes — exactly the piece-theft mechanism. Reservation sweet spot ≈ 0.08.

**Hints**: enforceable as hard pins (pin the hint cell to its (piece,rot), remove
hint pieces from all pools). Unlike Blackwood (which evicts hints by design →
V190 got 0/5000 strict partials), MOSAIC holds all 5 hints rigidly. Strict-
canonical compatible. [Hinted run result pending at time of writing.]

## Why this is genuinely new for E2

- Not piece-DFS (plateaus ~403 edge-strict, ~460 with ALNS): MOSAIC searches over
  **exact block fills**, a coarser unit.
- Not Anjou's scaffold-fill (plateaued 462, pool-depletion): adds **scarcity
  reservation** + **soft boundaries** (never-dies). The vol-204 piece-theft
  diagnosis is what justifies the reservation.
- Not a bound (PARQUET capped at 480): it's constructive.
- Earlier perfect-block backtracking (`mosaic_bt`) hit the SAME depth-157 wall as
  edge-strict DFS (block 39/64) — because requiring perfect blocks ≡ edge-strict.
  SOFT boundaries (MaxScore) is what breaks past it.

## What's open / next

1. **Block-level backtracking on the last 3 blocks** (where degradation lives) —
   cheap, localized; should lift 448 → higher.
2. **Better block order** (spiral, hardest-region-last) and block size sweep.
3. **Rust port** (user-endorsed): a fast custom block-solver (blocks are tiny —
   exhaustive or a lean SAT) + block-backtracking would run orders of magnitude
   more nodes, making full-search MOSAIC practical and enabling long runs.
4. **Then ALNS post-step**: 448 from-scratch + ALNS could reach the 458-460 class
   (the existing pipelines lift +10-15 from a good seed).

## Linked
- [[watershed-frontier-flow]] — the scarcity / piece-theft diagnosis it exploits
- [[streamlining-for-e2]] — parent technique frame
- [[parquet-overlapping-patch]] — the bound side (capped); MOSAIC is the search side
- [[lague-rubik-transfer-ideas]] — compose-exact-subsolutions inspiration
- `reference_anjou_experiments_2026_06_09` (memory) — window-MaxSAT tractability

## Defect structure of the 447 board (vol-206, answers "better paths?")

Mismatch distribution of the from-scratch 447 board (33 mismatched edges),
by 4×4 block region top→bottom:
```
 row 0:  0 0 1 0      row 2:  2 2 4 2
 row 1:  0 0 1 2      row 3:  3 3 6 7  (bottom-right corner)
```
The top ~10 rows are nearly perfect; defects form a monotonic gradient into the
LAST-filled (bottom-right) corner. This is the piece-theft signature: greedy
row-major composition depletes the pool, the corner inherits incompatible pieces.

**Interpretation:** exact-block composition produces genuinely high-quality
structure over ~3/4 of the board (a *better partial* than greedy/DFS, which
scatter mismatches). The 33 mismatches are a LOCALIZED, fixable resource-
allocation defect — not a quality ceiling. Confirms the cost buys real structure;
the remaining gap is exactly what block-backtracking / reservation / better order
target. Open: does MOSAIC+ALNS beat the from-scratch 460 ceiling? (test running).

## MOSAIC-447 + ALNS = 448 (PLATEAU) — seed-for-ALNS route refuted (vol-206, 2026-06-10)

Fed the from-scratch 447 board to `alns_only --ops basic --seed 42`, 5min ALNS:
- iter 0: 447 → iter 5: **448** → then PLATEAU (200 iters, every op 100% accept =
  iso-score random walk, no further improvement). σ-lock signature.

**Verdict:** MOSAIC seed + ALNS (448) does NOT beat the existing from-scratch
pipelines (V155/KEYRING reach 460). The MOSAIC seed lands in a LOWER basin and
ALNS can't escape it. The bottom-right corner defect creates a basin ALNS is
σ-locked in. **The "MOSAIC as ALNS seed" route is refuted as record-competitive.**

MOSAIC's remaining potential value (if any):
- Does its 448 basin differ structurally (high Hamming) from known 460s? If yes,
  it explores NEW territory and block-backtracking there might find a 460+.
- Constructive corner-fix (block-backtracking) to raise the from-scratch number
  directly, NOT via ALNS.
Otherwise MOSAIC is a clean from-scratch constructor that plateaus below SOTA —
a documented method, not a record-mover. Honest assessment per the rigor rules.

## ★ MOSAIC reaches STRUCTURALLY NOVEL basins (vol-206, 2026-06-10) — the real value

Hamming distance (cells with different piece) of the from-scratch 447 board to
every known high basin:
- vs McGavin 469: **255/256** differ (essentially disjoint)
- vs vol-60 459: 250/256 ; vs V181 460: 243/256 ; vs V155 460: 252/256 ; vs V129 463: 254/256

**MOSAIC's basin is 95-99% disjoint from ALL known high basins** across 200+ vols.
It explores genuinely NEW territory — answering "does it find better paths?":
yes, STRUCTURALLY different ones. Its corner-perm is (0,3,1,2) = V181's cp (the
one cp that reached 460 via KEYRING).

**Reframe:** MOSAIC is not a worse-ALNS-seed; it's a **novel-basin generator**.
The known pipelines keep re-finding the SAME σ-locked basins (458-463). MOSAIC
lands in fresh basins that may NOT be σ-locked at the same ceiling. Highest-EV
use: MOSAIC with seed-diversity → many distinct new basins → ALNS-lift within
each. A new basin is the only thing that could exceed the saturated known plateau
(per the whole project's σ-lock finding). THIS is the experiment to run next.
