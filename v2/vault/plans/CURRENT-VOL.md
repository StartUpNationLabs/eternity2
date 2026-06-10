# Current Volume — Vol-213 — the II-side wall (CLOISTER-III seam scan)

**Status**: drafted at vol-212 close (2026-06-10). Strict track (5/5) bar
unchanged: **461**. Vol-212 proved CLOISTER-II collects IB (48-50) and
saturates at 449-strict; gap anatomy is pure II (339-345 vs witness 350 at
IB≈50). The II search under rim+hint constraints is THE wall.

## Why this

Row-sequential scans dump all leftover-pool damage into the last rows; the
exact tail then optimizes a starved 14-28 piece pool. Vol-211 proved tails
are already optimal given prefixes ("prefix diversity, not endgames, is
the II lever") and vol-212 proved prefix diversity via restarts/LDS/frames
is exhausted at the 444-449 band. The structural move left: **change where
the damage lands** — grow two fronts (rows 0-6 top-down anchored on the
top frame edge; rows 13-7 bottom-up anchored on the bottom frame edge,
both rim-constrained) and close at a middle seam where (a) the remaining
pool is largest mid-search, (b) the closure is a fully-two-sided exact
assignment (stronger than the one-sided tail trigger), (c) both deep hints
(row 12) sit INSIDE the bottom front's early region (cheap), not at its
end (starved).

## Binding items (≤3)

1. **CLOISTER-III seam scan**: generalize `Scan` to two-front orders
   (plans machinery already takes arbitrary permutations; the bottom-up
   front needs S-side Placed constraints — already supported by
   `build_plans`); new `exact_seam` endgame (k ≤ 14 cells with BOTH N and
   S placed + chain: port `exact_tail` with the extra constraint per cell
   — strictly tighter B&B). Gates re-derived for two-front geometry
   (each front has its own wall; measure first: two-front bordered wall,
   8 seeds × 10 s — the cheap decisive number again).
   **Built at vol-212 close (same-day head start)**: `Scan::Seam(s)` +
   `pair_sw` bottom-front tables; `exact_tail` proved scan-generic (seam
   cells get two-sided N+S constraints through plans — no new endgame
   code needed); tests green. ★ Hint geometry under seam:7 — hint 104
   (row 7) falls INSIDE the exact closure row; deep hints (row 12) land
   at scan 113/124, early-bottom-front (the row-major death-at-180
   chokepoint dissolves). Measurement queued behind the 2 h slope run.
2. **Assignment-guided value priors**: per-(cell, piece, rot) prior from a
   relaxation (Hungarian / LP on the 196×196 assignment with edge terms),
   used to order candidate lists instead of uniform shuffles (vol-155
   weaving-prior analogue, now bordered+hinted). Measure II delta at
   30 s × 8 on strict460a.
3. **Discipline**: ≥8 seeds, min/median/max; verify + rescore before any
   claim; timestamped outputs + history.csv; throughput arithmetic before
   any multi-day run; honest negatives to the vault same-day.

## Audit-at-open compliance

- Vol-212 closed same-day with all levers measured; no aged unbuilt items
  added. frame_ub (direct-HiGHS builder) and frame-generator-at-scale go
  to BACKLOG as `partial`/`unbuilt` (only pick up if items 1-2 stall).
- The 2 h slope run lands after close — append its number to
  [[cloister-ii-border-anchored]] when read (expected 451-452; ≥455
  reopens the grind hypothesis).

## Linked

- [[cloister-ii-border-anchored]] (vol-212: saturation + gap anatomy)
- [[cloister-standalone-interior]] (vol-211: rim result, free-rim records)
- session: [[vol-212]]
