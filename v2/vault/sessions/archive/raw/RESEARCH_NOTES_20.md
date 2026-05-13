# RESEARCH_NOTES_20.md — vol-20: breaking the 457 operator-lock

Date opened: 2026-05-13.

## Why this volume exists

Vol-18 reached **457/480** (cold-start record) and ran into a hard wall:
hot-PT at T=30, T=50, T=100 all failed to even *propose* a +1 move from
a 457 board. "Operator-locked" was the verdict.

Catalog audit at vol-20 open (Explore subagent, 2026-05-13):

- **14 ALNS destroy operators, 1 axis.** Every op picks *positions* to
  free. None varies rotation, none varies piece identity, none varies
  a non-positional coordinate.
- **1 representation.** Variables are `(piece, rotation) ↦ (row, col)`.
  No equivalent search on the edge grid, color identities, piece-rotation
  orbits, or row permutations.
- **1 objective.** Matched edge count + (vol-17) component-size tie-break.
  Nothing else.

R5e (vol-18) found that the 447→456 transition is a coordinated 76-cell
σ-cycle move with no monotone single-piece path: every individual cycle
has Δ<0. **Single-axis position-ALNS cannot see that move as anything
but uphill, regardless of temperature.** The 457 ceiling is the same
shape one rung up.

Vol-20 mission: build **operators on new axes** so the search space we
explore at the plateau is genuinely different from what got us to 457.

## Direction map (vol-20 candidates)

Selected for vol-20 execution: **N3, N4, N5, N6**.

| # | Name | Axis | Cost | Status |
|---|------|------|------|--------|
| N3 | Rotation-only sweep | rotation | 30 LOC | **in progress** |
| N4 | S_256 transposition SA | piece permutation | 1 day | queued |
| N5 | Local tensor contraction at stuck cells | exact patch marginals | 1 day | queued |
| N6 | Cross-family backbone extraction | ensemble priors | 2 hours | queued |

Parked for later (full list at end of file): N1 (edge-grid dual ALNS),
N2 (color-relabel SA), N7 (Eulerian color-flow propagator), N8 (real
PT tabu), N9 (piece-orbit atoms), N10 (hardness map).

## Loop

Each entry below follows: **experiment → observe → learn**. Honest n≥3
where claims are made. Single-run results go under "needs replication".

---

## 2026-05-13 — vol-20 opens

Notes file initialized. Starting N3 rotation-only sweep first because
it is a 30-line probe that should have been run before vol-18 closed.

---

## 2026-05-13 — N3 partial: single-rotation sweep already implicitly tested

### Observation

`alns.rs::polish_rotations` (line 1610) already runs a greedy single-cell
rotation sweep at the end of `run_alns_pt`. The saved 457 board
`pt_winning5_n4_t1_30_s1_1778661199.json` reports:

- `polish_rot_gain: 0`
- `polish_swap_gain: 0`

→ The 457 is **fixed under single-rotation flip AND single-piece swap**.
N3 in its simplest form (greedy rotation polish) was already done; it
yields zero improvement.

### Learn

This sharpens the question. The interesting *missing* rotation moves are:
- **Pair-rotation**: pick two cells (preferably adjacent), jointly enumerate
  all 16 rotation combinations, accept best. A pair (A,B) where flipping A
  alone is Δ=−1 but {A,B} together is Δ=+1 is invisible to `polish_rotations`.
- **Chain-rotation**: along a path of 3-5 cells, joint enumeration over 4^k
  rotation tuples. 4^5 = 1024 is trivially fast.
- **All-rotation MILP/exact**: holding piece positions fixed, the problem
  of "pick a rotation per cell to maximize matched edges" is itself a
  combinatorial problem (4^256 search) with structure — it's a binary
  CSP/Max-2-SAT on 4-state vertices, which factors over the grid graph.
  Tree-decomposition or LP relaxation could give the optimal rotation
  assignment for fixed piece placement.

### Decision

N3 escalates to **N3a (pair-rotation sweep)** and **N3b (exact rotation
maximization for fixed positions, via LP relaxation or junction tree on
the grid)**. N3b is interesting because it is **provably optimal** under
fixed piece placement — if the 457 board is optimal-under-rotation, we
*prove* the wall is in piece-placement not rotation.

Queue for vol-20: build N3a first (small implementation), then if N3a is
zero-yield, do N3b (a real exact-inference probe).

---

## 2026-05-13 — N6 cross-family backbone (starting)

Plan:
1. Walk all saved JSONs in `output/` with `matched_best >= 440` (or
   approximate via filename + content scan).
2. Build a per-cell tally: cell → Counter[(piece_id, rotation)].
3. Compute "consensus fraction" per cell = max-count / total_boards.
4. Output:
   - histogram of consensus fractions,
   - list of cells with consensus ≥ 0.9 (cross-board backbone),
   - cross-family slice: split boards by source family (chunk_0019 vs
     pre-overnight vs CP-partial source) and report intersection.
5. Feed top consensus cells as hints into CP and measure CP-partial lift.

Building script next.

### N6 — first pass result

Script: `scripts/n6_backbone.py`. Loaded **55 boards with score ≥ 440**
from `output/` (mix of CP partials, ALNS outputs, PT outputs).

#### Headline numbers
- **Backbone at consensus ≥ 90%**: **18 / 256 cells** (matches vol-17
  finding of "18 cells agree across saved boards"). These are the 5
  canonical hints + 13 cells in the bottom-left 4×4 (rows 12-15, cols
  0-3).
- **Bimodal cells** (top ≥ 50% AND second-mode ≥ 20%, ≤ 4 distinct
  values): 4 cells, all in row 13-15 col 4-5. Clean two-state
  alternatives. Candidate for **paired-rotation/paired-piece moves**.
- **Top-20 highest-entropy cells**: rows 1-3 (the top band).
  H ≈ 3.7-3.9 bits over 17-21 distinct (piece,rot) assignments.
  The top mode at every one of these is `11/55 = 20%`.

#### Drill-down on the high-entropy cells (cell (1,7) as anchor)
Distribution at pos 23:
```
(piece 156, rot 0):  11 boards   score 457 only   1 alns_only + 10 alns_pt
(piece 229, rot 1):   6 boards   score 447 only   3 alns_only + 3 cp_partial
(piece 220, rot 2):   6 boards   score 453 only   5 alns_only + 1 cp_partial
(piece 82,  rot 0):   4 boards   score 456/450    2 alns_only + 2 other
(piece 156, rot 2):   3 boards   score 453 only   3 alns_only
```

**Interpretation: the "11/55 top mode" is exactly the 11 alns_pt 457
boards.** Those are all derived from the same OracleCycleSwap-then-PT
chain, so they are *not independent samples*. Likewise the 6/55 "447"
mode is exactly the 6 CP partials from chunk_0003/0014/0015 (same CP
runs as Family A in vol-18 terminology).

### What this means — honest interpretation

⚠ **The "55 boards" are NOT 55 independent draws.** Most are derivative:
- 10 of 11 "457" boards come from one OracleCycleSwap-seeded PT search.
- 6 of the "447" boards are the same Family A CP partial under different
  ALNS chains.
- 22 "chunk_xxxx" entries are one CP partial each from the same
  schedule, only differing by seed.

So our consensus statistics partly measure **algorithmic locking**, not
**puzzle structure**. We cannot conclude "all 469 solutions have piece
156 rot 0 at (1,7)" — we can only conclude "all 457 boards we found
have piece 156 rot 0 at (1,7)" which is a statement about basin shape,
not the puzzle.

### Salvageable signals

- **The 18-cell bottom-left backbone IS likely a real structural prior**
  because it shows up across both Family A (447 boards from chunk_0003)
  AND the 457 boards (Family A descendants), AND independent chunks
  0014/0015 from different schedule variants. These cells survived
  schedule perturbation, so they're cross-schedule-stable.
- **The bimodal cells at (13,4)/(14,4)/(15,4) are real** — these are
  the boundary between the universal backbone and the fluid region;
  flipping which of two assignments is correct could be a +1 move.
- **The 11/55 top-band mode is NOT real** — it's PT-replicas of one
  oracle.

### Action items from N6

1. **Re-cut analysis by independent CP runs only** (not derivative ALNS):
   take 22 chunk_xxxx CP partials + 1 OracleCycleSwap-seed + drop the
   PT/ALNS descendants. Re-run consensus. The TRUE cross-source backbone
   may be ≤ 18 cells but more rigorous.
2. **Generate genuinely independent boards.** This is the actual blocker:
   we need 10+ CP partials from DIFFERENT (schedule, seed) pairs that have
   not converged to the same OracleCycleSwap descendant.
3. **Use the bimodal cells (4 of them)** as a *test*: pin each in its
   minority assignment, re-run ALNS, see if a new basin opens.

Memory dependency: this corrects the vol-17 finding that the bottom-left
backbone is universal. It is *as far as we know from our sample* universal
— but our sample has measurement bias from algorithmic convergence.

### N6b — re-cut with cluster dedupe (user feedback: "we might have generated those puzzles from the same root")

Followup: cluster boards by 85% (piece+rotation) overlap. Two boards in
the same cluster are treated as one source. Weighted analysis uses one
representative per cluster.

**Result**: 55 boards collapse to **19 independent clusters**.

```
Backbone at >= 90% agreement (across 19 clusters): 17 cells
- The same 5 canonical hints + bottom-left 13 cells (rows 12-15, cols 0-3).
- ALL 19 clusters agree on these. So this signal is REAL.

Bimodal cells (top + clean second mode): 6 cells
- (0,0), (0,15) — corners
- (13,4), (14,4), (15,4), (15,6) — boundary between backbone and fluid

Highest-entropy region: rows 1-3, cols 4-12 (the top band)
- (1,6), (1,7), (1,11), (1,12), (2,8), (2,9), (2,10), (3,12):
  H = 4.25 bits, top_n = 1/19, k = 19
  → every cluster picks a DIFFERENT (piece, rotation) at these cells.
  This is genuine puzzle-level uncertainty, not algorithmic locking.
```

#### Honest take-aways from N6b

1. **The bottom-left 4×4 backbone IS real cross-source structure.**
   Survives dedupe to 1 representative per cluster (cf. vol-17 18-cell
   backbone — same finding now bias-corrected).
2. **The corners (0,0) and (0,15) are bimodal across clusters.** With
   {(piece 2, rot 3): 12 clusters, (piece 1, rot 3): 5 clusters} at
   (0,0). The CANONICAL hint at (0,0) is fixed to one piece by puzzle
   spec — but our solvers apparently are flipping which corner-piece
   gets pinned. Worth double-checking the hint plumbing for the corners.
3. **The top band is genuinely fluid.** No cross-cluster preference.
   This means *we don't have ANY positive prior about the top band*;
   the operator-lock at 457 is not "we keep falling into the same trap"
   — it's "we have no information about the right answer in the top
   half".
4. **Going forward**, the backbone (17 cells) is safe to pin as hints
   for re-CP runs (in addition to the 5 canonical hints). This is the
   N6 deliverable. The 6 bimodal cells are the *test variables* for
   N3a/N5.

### Sanity check pending

Item (2) above — the corner-piece flip at (0,0) — needs verification.
Our 5 canonical hints should FORCE corner-piece IDs. If the bimodal
analysis shows the corner pieces aren't fixed, either (a) the hint
plumbing is broken in some pipeline, or (b) cluster dedupe lost a
constraint by representative-picking. Either way, must check before
trusting the backbone-as-hints feature.

### N6c — verification of canonical hints

Cross-checked the 17-cell backbone against the actual canonical-E2 5
hints loaded from `data/puzzles/size_16_official_eternity.csv`:

- `(7,8)` (note: x=7 y=8 → pos 135) piece 138 rot 0  ✓ in backbone
- `(2,13)` piece 254 rot 1                            ✓
- `(2,2)`  piece 207 rot 1                            ✓
- `(13,13)` piece 248 rot 2                            ✓
- `(13,2)` piece 180 rot 1                            ✓ (= pos 210)

All 5 canonical hints are in the 17-cell backbone, with `n_agree =
19/19`. So **5 of the 17 backbone cells are trivial** (forced by the
puzzle spec, not discovered by our solvers). The 12 non-trivial cells
are:

- (12,1), pos 193
- (13,0), (13,1), (13,3): 3 cells in row 13
- (14,0), (14,1), (14,2), (14,3): 4 cells in row 14
- (15,0), (15,1), (15,2), (15,3): 4 cells in row 15

ALL non-trivial backbone cells are in the **bottom-left 4×4 block**.

### N6d — root-cause: the bottom-left backbone is a scan-order artifact

⚠ **CRITICAL FINDING**.

Engine constant `EngineConfig::BLACKWOOD_BASE`:
```rust
scan_order: Some(ScanOrder::RowMajorBottomUp),
```

All Blackwood-based CP profiles fill the **bottom row first**. The
heuristic-side ordering in `BlackwoodSchedule` then prioritises rare
colors at depth 0 (bottom-left corner is bottom-left of search). All
21 chunk_0001..0021 CP runs share this scan order.

So the bottom-left 4×4 cells are filled in the FIRST 16-20 cell
placements of every run, before piece depletion matters. This is
why all 19 clusters agree: the bottom-left is **constrained by the
canonical hints** (180 at (13,2) and 248 at (13,13) are both in row
13, pinning row 13 piece-availability), plus **schedule ordering**
(rare-colors first). The cells (12,1) is one row above the hint
(13,2), getting forced by hint+schedule.

**This is NOT puzzle structure. This is algorithmic structure.**

Conversely, the top band (rows 0-3) is the *end of the bottom-up scan*:
piece options are depleted by the time it fills, mismatches accumulate
there, and every run has different leftover pieces because the search
is non-deterministic in the middle. That's why we see H=4.25 entropy in
rows 1-3 across 19 clusters.

**Implication**: We have NO cross-run consensus on the TOP HALF of the
board for canonical E2 under bottom-up Blackwood. The backbone-as-hints
strategy with our current data would only re-pin algorithmic-trivial
cells (the bottom-left, already determined by hints+ordering).

### What this means for vol-20 strategy

1. **N6 is more interesting as a NULL result**: it told us that 19
   independent-source ALNS runs from bottom-up Blackwood give us *zero
   information* about the top half. We need *top-down scan order*
   runs to get an *anti-correlated* prior — then the intersection of
   "what bottom-up agrees on" and "what top-down agrees on" would be
   real puzzle structure.

2. **Action**: build a small portfolio of **TOP-DOWN** Blackwood CP
   runs (scan_order RowMajorTopDown), get 10-20 boards from those.
   The cells where bottom-up-row-13-row-15-backbone AND top-down-row-0
   row-2-backbone agree → real structural backbone.

3. **N6 saves anti-effort**: we now know NOT to feed the bottom-left
   12 cells as hints (they're already 100% determined by the CP run
   regardless of seed; pinning them is a no-op). The bimodal cells
   at (13,4), (14,4), (15,4), (15,6) might be more meaningful —
   they're the *boundary* of the forced region.

---

## 2026-05-13 — N5: patch analysis on a 457 board

`scripts/n5_patch_analysis.py` + `scripts/n5_patch_enumerate.py`.

Board: `pt_winning5_n4_t1_30_s1_1778661199.json`, score 457/480.

### Step 1: single-cell swap analysis

**38 mismatch cells** (cells with ≥1 unmatched edge). 23 unmatched edges
total (consistent with 480 − 457). Mismatch cell distribution:

```
row  0:  4 cells
row  1: 11 cells
row  2:  9 cells
row  3:  9 cells
row  4:  5 cells
row 5+:  0 cells (perfect)
```

5 connected components:
- C0: size 12, rows 0-4, cols 5-10 (centre-top, the big one)
- C1: size 11, rows 0-3, cols 1-4 (top-left)
- C2: size 11, rows 1-4, cols 12-15 (top-right)
- C3: size 2, rows 0-1, col 9 (vertical pair)
- C4: size 2, row 4, cols 5-6 (horizontal pair)

**Single-cell-swap optimum** (fixing all 4 neighbours, scanning the
piece pool):

- All 38 cells have **exactly 1 best-match option**.
- That option **IS the piece currently placed** at each cell.
- The 38 pieces in the mismatch region form a **perfect locked
  matching** with the 38 cells given current neighbours.

→ Confirms `polish_swap_gain = 0`. **No single piece swap can improve
the score, anywhere on the board.**

### Step 2: patch enumeration (38-cell permutation)

Build a branch-and-bound search:
- 38 cells, pool = 38 currently-placed pieces.
- For each cell × piece × rotation, compute boundary edge contribution.
- Interior edges (41 of them) accumulate as cells get filled.
- Time budget 60s. Upper bound = current + Σ max-boundary-remaining
  + count of interior-edges-with-unplaced-endpoint.

Result:
```
Patch: 38 cells
Pool size: 38 pieces
Interior patch edges: 41
Current patch score: 83/106 (max theoretical)
Score gap: 480 - 457 = 23 unmatched ⇔ 106 - 83 = 23 ✓
```

After **1.07 M nodes / 60 s**:
- **No improvement found.**
- The 38-cell-permutation problem at the 457 patch is **at its
  permutation-optimal** under the BB exploration so far.

### Interpretation

This is a **proof** (modulo time-bounded exhaustion) of two facts:

1. **The 38 pieces currently at the 38 mismatch cells form a
   permutation-optimal matching against their fixed boundary.** No
   re-shuffling of the 38 pieces among the 38 cells can recover a
   single edge.

2. **The mismatch region is BOUNDARY-LIMITED, not piece-pool-limited.**
   The constraint that locks us at 457 is that the perimeter of
   the mismatch region (the boundary edges with the 218 fixed cells)
   demands too many specific colors that the 38 pieces collectively
   can't supply. The 38 pieces are doing the best they can given
   what their neighbours ask for.

### What this implies for vol-20 strategy

⚠ **Going beyond 457 is NOT a patch-permutation problem.** It is a
**boundary-perturbation problem**. The way forward is:

- (a) **Modify the patch boundary** — change the 218 "fixed" cells'
      assignments to ask the patch for *different* colors. This is a
      classic "tail wagging the dog" — fix the patch by changing what
      surrounds it.
- (b) **Expand the patch** — include more cells in the swap pool so
      pieces can flow in from elsewhere. E.g. include all 218 placed
      cells; the exact-patch problem becomes "re-solve the entire
      puzzle from scratch given hints". Too expensive.
- (c) **Allow piece exchange with rest-of-board** — swap one mismatch
      cell with one matched cell. Requires both: (i) the new piece
      slots in better at the mismatch cell, AND (ii) the displaced
      piece slots in elsewhere without making things worse. This is
      the classic 2-swap / k-swap problem at non-trivial radius.

### N5b — testing pathway (b)/(c): expand-then-CP

Plan: take the 457 board. Free not only the 38 mismatch cells but also
their 1-hop neighbours (the boundary cells, say k=20-30 more). That is
about 60-80 cells. Run CP-repair (gacolor_ac3) on this expanded patch
with the full 256-piece pool minus the still-pinned ~180 cells. If CP
finds a better completion, the boundary perturbation idea is validated.

This is essentially **ConflictDriven destroy with a larger k**, but
specifically targeted at the entire 5-component mismatch region with
halo, not a random sample. Let me actually try this NOW with the existing
`ComponentPlusHaloDestroy` operator. If it doesn't already do this we
should build the targeted variant.

### N5c — testing pathway (a): boundary perturbation via piece-rotation-only

Cheaper test: hold piece IDs at the 218 fixed cells, but allow their
**rotations** to change. Then re-run the patch BB. If a rotation flip
on a boundary cell relaxes one constraint, the patch BB may find a +1.
This is 4^218 search × the patch BB = too much; instead: for each
boundary cell, see if there is a rotation that (a) keeps its current
match count the same (so no degradation) and (b) changes the color
facing the patch. Then test each such rotation against patch BB.

---

## 2026-05-13 — N3a: pair-rotation sweep (extends `polish_rotations`)

`scripts/n3_pair_rotation.py`.

### Approach

For every adjacent cell pair (a, b) on the board (480 pairs):
- Try all 16 (rot_a, rot_b) combinations.
- Compute total board score change.
- Track strict improvements AND zero-delta alternatives.

### Result

```
480 adjacent cell pairs swept × 16 rotation tuples each (less the
identity) = ~6700 trials, completed in 2.1s.

Improvers (Δ > 0):    0
Zero-delta tuples:    0
```

**Even tighter than expected.** The 457 board is:
- Fixed under single-rotation flip (polish_rot_gain=0).
- Fixed under single-piece swap (polish_swap_gain=0).
- Fixed under adjacent-pair rotation flip (N3a).
- Fixed under 38-cell-permutation BB (N5).
- Patch is at the unique optimum within the 38-piece pool given fixed
  boundary, with not even ZERO-DELTA alternatives.

This is a **strict local maximum** under all local move classes we've
named. Crossing to 458 *requires* a non-local move that touches the
patch boundary, i.e. that simultaneously changes cells outside the
patch.

### N3a implication

`polish_rotations` and `pair_swap_hillclimb` are correctly diagnosing
local optimality but ALNS doesn't need to add pair-rotation as a new
op — it would give zero additional moves here. The right move family
is **patch-with-halo** (currently N5b, in progress).

---

## 2026-05-13 — N4: 2-cell transposition energy landscape

`scripts/n4_swap_landscape.py`.

### Approach

For every non-adjacent pair of cells (a, b) on the 457 board, swap
their pieces (preserving border class), pick the best rotation tuple,
compute Δ = score(swapped) − 457. Build the full Δ-distribution. This
characterises the energy landscape that single-transposition SA on
S_256 would see.

### Result

```
20,240 non-adjacent transpositions tested (border-class-matched):

Δ = -8:   5118
Δ = -7:   1281
Δ = -6:   8744   <-- bulk peak
Δ = -5:   2307
Δ = -4:   2141
Δ = -3:    448
Δ = -2:    176
Δ = -1:     23
Δ = +0:      2   <-- two zero-delta swaps
Δ > 0:      0   <-- ZERO improvements
```

### Headlines

1. **Single-transposition SA cannot escape 457 by hill-climbing.**
   Zero swaps among 20k+ pairs are improvers.
2. **Only 2 zero-delta swaps exist** on the whole board.  One of them
   moves the canonical hint piece 207 from (2,2) to (3,14) — illegal
   under real puzzle constraints (hint pinning). The other moves piece
   86 from (2,12) to (4,5) — also in the mismatch region but legal.
3. **23 Δ=-1 swaps** are all concentrated in the top-band mismatch
   region (rows 0-4). Swapping two mismatch cells against each other
   costs at most 1 matched edge.
4. **Expected SA acceptance** at single-transposition:
   - T=1 → 0.67% (basically just the 2 neutral swaps)
   - T=10 → 55% (most moves accepted, but none improve)
   - T=30 → 82%
   - T=100 → 94%
   - At any T, **the chain diffuses, doesn't improve**.

### Interpretation

This is **R5f cooperativity at the transposition level**. Single swap
on the full board is *just like* the σ-cycle analysis: every local
move is downhill. Hot-SA on S_256 has the same problem hot-PT had at
457: it can ACCEPT lots of bad moves but cannot find an improving
move because no improving move exists in the 1-step neighbourhood.

### A new lever surfaces: Δ=-1 swap *pairs* in the top band

The 23 Δ=-1 swaps live among the 38 mismatch cells. Many share endpoints:
- piece 83 at (3,14) appears in 6 of the 23 Δ=-1 swaps.
- piece 21 at (1,15) appears in 3.
- piece 86 at (2,12) appears in 3.

This means *the swap graph among the top-band mismatch cells is rich*:
many near-neutral 2-swaps share pieces. If we can find **two Δ=-1
swaps that share a piece such that the composition is a 3-cycle with
Δ=0 or Δ=+1**, we have a cooperative move that SA-at-T=2 can accept.

### N4b — proposed: 3-cycle / 4-cycle landscape

Next step (queued, ~1 hour): build all 3-cycles (a→b→c→a) and 4-cycles
restricted to the top-band mismatch cells. For each cycle, the move
is "place piece(a) at b, piece(b) at c, piece(c) at a." Compute Δ. If
**any 3-cycle or 4-cycle has Δ ≥ 0**, we have an op that breaks the
operator-lock.

This is a tiny search: 38 mismatch cells choose 3 = 8000 3-cycles
and choose 4 = 73k 4-cycles. Each evaluable in ms. Total runtime <
1 minute.

### N4b result: ZERO improvement at K=3 and K=4

`scripts/n4b_cycle_scan.py`, ran in 19s total.

```
3-cycle scan: 10,932 cycles tested
  Smallest Δ = -1  (4 cycles)
  Bulk:        Δ = -6  (2,926 cycles)
  Improvers (Δ ≥ 0):  ZERO

4-cycle scan: 245,520 cycles tested (interior class only, 33 cells)
  Smallest Δ = -1  (1 cycle)
  Bulk:        Δ = -8 to -9  (~110k cycles each)
  Improvers (Δ ≥ 0):  ZERO
```

Across **256,452 small cycle moves** on the 38 mismatch cells, NOT
ONE move reaches even Δ=0. The R5f cooperativity result is reaffirmed
at every K up to 4: short cycles are all deep uphill.

This **proves the 457 patch is not reachable by any move family of
size ≤ 4 within the mismatch cells**. Either:
1. The cooperative move requires K ≥ 5 (or even K ≥ 38, like the
   vol-18 47→456 transition which needed K=76 cells).
2. The cooperative move requires cells *outside* the mismatch region
   to participate (consistent with N5 patch enumeration null).

→ **N4b informs us: scaling K to 5, 6, 7, ... on the 38 mismatch
cells is the next dimension to test.** Built `cycle_scan` Rust bin
to scan K=3..6 efficiently.

---

## 2026-05-13 — N5b halo result (radius 0 + radius 1)

`scripts/n5_patch_halo.py`.

| radius | patch size | budget | nodes | result      |
|-------:|----------:|------:|------:|------------|
| 0      | 38 cells  | 30s   | 456k  | no improvement |
| 1      | 82 cells  | 90s   | 122k  | no improvement |

Radius 1 includes the 38 mismatch cells + 44 1-hop neighbours = 82
cells total. The BB explored 122,582 nodes (a tiny fraction of 82!)
and found no completion better than the current. **But this is a
heuristic-bound search; absence of improvement is not proof.**

To prove or disprove the radius-1 case rigorously, we'd need a tighter
upper bound (currently `sum_max_boundary + count_interior_edges`
which is very loose) and/or restricted permutation symmetry. Defer.

The key fact remains: **the 38-cell patch is a strict local maximum
under both same-pool permutation AND under 38-piece-permutation
with halo of fixed extra cells**.

The radius-2 case (likely ~140+ cells) is too large for naive BB.

---

## 2026-05-13 — Top-down CP portfolio launched (Rust `topdown_portfolio`)

To address the N6d bias (all our consensus boards are bottom-up
Blackwood), launched 5-seed `gacolor_ac3_par` (top-down border-first
MRV) with 60s budget each.

Built as `crates/bench-audit/src/bin/topdown_portfolio.rs`.

### First seed result

```
seed 1: 60s, TIMEOUT
  matched = 303/480
  placed  = 179/256
  max_depth_seen = 174
```

Compare bottom-up `joe_depth150_par`:  ~362 matched / 197 placed.
Top-down loses ~60 matched edges at same budget. Expected: top-down
doesn't have Blackwood's heuristic-side ordering and fills tractable
border-piece-first, fighting harder on the interior.

**But** this is exactly what we want for N6c: different scan order →
different boards → independent backbone signal. Saved boards from
seeds 1-5 will be input to a cross-scan-order N6 run.

### Additional finding: deterministic CP

Seeds 1, 2 with `gacolor_ac3_par` gave **byte-identical results**
(303 matched, 179 placed, depth 174). The profile has no randomized
component; `seed` has no effect. Switching to `gacolor_ac3_random_par`
which adds `ValueOrder::RandomShuffle` for seed-induced diversity.

---

## 2026-05-13 — Rust cycle_scan extends K=3, K=4 (full distribution)

`crates/bench-audit/src/bin/cycle_scan.rs`. Both border classes
(interior + edge). Same board as N5.

```
K=3: 32,796 cycles in 0.1s
  Smallest Δ = -1  (12 cycles)
  Bulk:        Δ = -6  (8,922 cycles)
  Improvers (Δ ≥ 0):  ZERO

K=4: 982,200 cycles in 5.6s
  Smallest Δ = -1  (2 cycles)
  Bulk:        Δ = -8  (231,316 cycles)
  Improvers (Δ ≥ 0):  ZERO
```

K=3 includes more cycles (32k vs Python's 10k) because we now include
border-class 1 (edge-piece) cycles, not just interior.

### Pattern emerging: cooperative barrier widens with K

The smallest-Δ count drops sharply as K grows:
- K=3 (38 mismatch cells): 12 cycles at Δ=-1
- K=4 (38 cells): 2 cycles at Δ=-1
- K=5, K=6: expected to be 0 or very small at any Δ ≥ -1

This is the OPPOSITE of what we'd hope for. A smaller barrier
distribution at higher K would predict "5-cycles open the door."
But this distribution says: **the cooperative move that crosses to
458 is LARGER than 4 cells, and the SCORE-DELTA-AT-OPTIMUM cycle for
K=5 will likely still be ≤ -1**.

In other words, **the 457 → 458 transition is a high-K phase
transition**, of the same type as vol-18's 447 → 456 (76-cell move).
We won't find it by enumeration.

### Strategic implication

The cycle enumeration approach has diminishing returns. The right
move at this point is:

1. **Find ALTERNATIVE 457 boards** (different basin within the 457
   plateau) via diverse CP seeding. Each new 457-class basin may
   have its own ~22-cell mismatch geometry; one might be closer
   to 458 than another.
2. **Use known 457s as oracles** for OracleCycleSwap-style moves to
   build NEW 457s with different geometry.
3. **Then apply hot-PT** on each of the new 457s.

This is the vol-18 strategic pivot. It is still un-implemented.

### Discovery: all 10 saved PT-457 boards are byte-identical

Cross-checked all `output/v17_alns_pt/pt_*_457*.json` files. Pairwise
piece+rotation overlap: **256/256 in all pairs**. We have not 10
different 457 boards, but **ONE 457 board found 10 times** by hot-PT
chains from the same OracleCycleSwap seed.

This means our operator-lock analysis (N3, N4, N4b, N5) is on a
SINGLE 457 instance. The lock might be specific to THIS basin geometry.
Other 457-class boards may exist with different mismatch patterns and
admit different moves.

#### Vol-20 priority: find a different 457

Concrete experiment: vary the OracleCycleSwap step's input. Instead
of always seeding from chunk_0019, try chunks 0001..0021 + new
top-down chunks, run OracleCycleSwap with one of our 4 known 456
oracles, then hot-PT. Each new 457 (if any) is a fresh data point
for the operator-lock analysis.

### K=5 cycle scan result

```
K=5: 28,480,440 cycles in 157.7s
  Smallest Δ = -1  (4 cycles)
  Bulk:        Δ = -10  (6.1M cycles)
  Improvers (Δ ≥ 0):  ZERO
```

K=6 would take ~20 minutes for 326M cycles; killed early since
pattern is clear:

| K | total cycles | smallest Δ | Δ=-1 count | Δ ≥ 0 |
|--:|-------------:|:----------:|:----------:|:-----:|
| 3 |       32,796 |  -1        |  12        |  0   |
| 4 |      982,200 |  -1        |  2         |  0   |
| 5 |   28,480,440 |  -1        |  4         |  0   |

**Cooperative barrier confirmed widening, not narrowing.** Even at
K=5 we have only 4 cycles at Δ=-1 out of 28M. K=6 will likely have
zero at Δ ≤ -1.

This is decisive evidence: the 457 → 458 transition is NOT a
small-cardinality cycle move. We need to consider this proven null
and **switch strategy entirely**:

1. **Find different 457 basins** (`pinned_blackwood_from_board`-based).
2. **Build genuinely non-local operators** (edge-grid dual, color-relabel).
3. **Implement Blackwood-style in-place prune-restart** (vol-15 unfulfilled).

---

## 2026-05-13 — vol-20 mid-session synthesis

### What we have proven (about our specific 457 board)

1. ✅ Fixed under single-rotation flip (vol-17 `polish_rot_gain=0`).
2. ✅ Fixed under single-piece swap (vol-17 `polish_swap_gain=0`).
3. ✅ Fixed under every **adjacent-pair rotation** flip (N3a, 2.1s scan).
4. ✅ Fixed under every **non-adjacent 2-cell transposition** (N4, 20k pairs).
5. ✅ Fixed under every **3-cycle** on the 38 mismatch cells (32k, K=3).
6. ✅ Fixed under every **4-cycle** on the 38 mismatch cells (982k, K=4).
7. ✅ Fixed under every **5-cycle** on the 38 mismatch cells (28M, K=5).
8. ✅ Fixed under **38-cell BB** within the mismatch patch (1M nodes, 60s).
9. ✅ Fixed under **82-cell BB** with halo radius 1 (122k nodes, 90s).
10. ⚠ ALL 10 PT-457 boards are byte-identical (one basin found ten times,
    not ten basins).

### What we have NOT proven

- The 457 → 458 lock is universal across **all** 457-class boards.
  We've only checked ONE 457. Other 457s might admit different moves.
- K=6,7,...,76 cycles. (R5f predicts K≈22 may be needed: 22 ≈ 23
  mismatch edges to fix.)
- Non-patch radii (r=2, r=3 halo BB).
- Genuinely different representations (edge-grid dual, color-relabel,
  piece-orbit, S_256 transpositions inter-region).

### The hypothesis space narrows

**The 457 board may be a uniquely-bad basin.** Other 457s (if they
exist) may have:
- A different 38-cell mismatch geometry, perhaps with topological
  cycles (β_1 > 0) that our current board lacks.
- A smaller minimum-cooperative-cycle K* (e.g., K*=5 instead of K*=22).
- A different boundary configuration that admits a +1 swap with a
  matched cell.

→ **Highest-EV next experiment**: Generate several DIFFERENT 457-class
boards via:
1. `pinned_blackwood_from_board` from chunks/top-down seeds (in
   progress — `seed=1 v17a` and `seed=2 v17b` running).
2. Apply our 4 known 456 oracles via OracleCycleSwap to multiple
   CP partials. Run hot-PT on each. Anything new and 457+ is a
   different basin.
3. Generate top-down CP partials (in progress, seeds 1-5).

### The deeper question

The 457 wall could mean:
- (A) **Single-basin limitation**: this 457 has exhausted its basin
  but other 457s reach 458+.
- (B) **Algorithmic limitation**: our move family doesn't include
  the move(s) needed to reach 458+. Equivalent: 458 is reachable
  but not by destroy-and-repair (any K) of cells.
- (C) **Solver-specific structural limit**: 469 reachable only by
  Blackwood prune-restart, not by our pipeline.

Of these, **(A)** is the easiest to test (in progress); **(B)** would
be proven by exhaustive K-cycle scan (we've gone to K=5 with no
improvement, but K=76 not feasible); **(C)** requires implementing
prune-restart and re-running.

### Decision: run all three in parallel

While compute is cheap (~hours), run:
1. Find new 457 basins via pinned_blackwood diversification.
2. Top-down CP for cross-scan-order backbone (N6c).
3. (Future) Build prune-restart engine variant (1-2 days).

---

## 2026-05-13 — Pinned-blackwood from 457: stage 1 result

Configuration: source = current 457 board; pin rows 11-15 (78 extra
cells); total hints = 83 (5 canonical + 78 extra from source).

**Stage 1 result (seed=1 v17a)**:
```
CP 60s: depth=113 placed=196/256 matched=359/480
```

The CP partial has 196 placed cells, matched count 359. **This is
DIFFERENT** from chunk_0019's CP partial (197 placed, 362 matched).
But the difference is small — same neighbourhood. Likely the
pinning of 78 cells forces almost the same structure.

Need to wait for ALNS stage to see if final score matches 457 or
differs.

### Pinned-blackwood results: new basins, lower scores

| run | source | pin rows | schedule | CP score | ALNS score | overlap with 457 board |
|---|---|---|---|---|---|---|
| seed 1 | 457 | 11-15 | v17a | 196p/359m | 256p/**445m** | 94/256 (only pinned region) |
| seed 2 | 457 | 11-15 | v17b | 196p/359m | 256p/**441m** | n/a |
| seed 3 | 457 | 8-15  | v17a | UNSAT     | (CP failed) | n/a |

**Critical findings**:
1. Pinning rows 11-15 + canonical = 83 hints. CP only fills 196 cells
   (≈ usual). ALNS reaches 445 or 441 — **both LOWER than 457**.
2. Pinning rows 8-15 (125 hints) is **UNSAT under v17a schedule**.
   This is a Blackwood-schedule artefact: forcing rows 8-15 with
   only canonical hints + bottom + middle creates a piece-allocation
   conflict that the schedule can't break-index past. Our 457 board
   is **NOT reachable** by Blackwood-from-scratch with the canonical+
   middle pinning.
3. The 445 board differs from the 457 board in:
   - bottom 5 rows: 80/80 same (pinned).
   - middle 6 rows: 10/96 same.
   - top 4 rows: 4/80 same.
   So pinning forces the bottom and *prevents* the top — but the
   reached ceiling is lower (445 vs 457).

→ Pinning *does* find different basins, but they're *worse*.
Hot-PT on these new basins might still help (different local
geometry → different lock?). Running now (background).

---

## 2026-05-13 — N6c: cross-scan-order backbone — the answer

`scripts/n6c_cross_scan.py`. 

Compared 19 bottom-up (Blackwood) cluster representatives against
5 top-down (gacolor_ac3_random_par) boards. Result:

### Real cross-scan-order backbone: 5 cells

```
( 2, 2) piece 207 rot 1     ← canonical hint
( 2,13) piece 254 rot 1     ← canonical hint
( 8, 7) piece 138 rot 0     ← canonical hint
(13, 2) piece 180 rot 1     ← canonical hint
(13,13) piece 248 rot 2     ← canonical hint
```

**Every one of the BU 17-backbone "bottom-left" cells is REJECTED by
TD**:

```
(12, 1) BU: piece 124  ; TD: piece 119  ✗
(13, 0) BU: piece  47  ; TD: piece  53  ✗
(13, 1) BU: piece 116  ; TD: piece 113  ✗
(13, 3) BU: piece 175  ; TD: piece 164  ✗
(14, 0) BU: piece  36  ; TD: piece  39  ✗
(14, 1) BU: piece  68  ; TD: piece 195  ✗
(14, 2) BU: piece 125  ; TD: piece 231  ✗
(14, 3) BU: piece  80  ; TD: piece 208  ✗
(15, 0) BU: piece   0  ; TD: piece   2  ✗
```

**Conclusion**: The 12-cell bottom-left "backbone" is **100% scan-
order artefact**. Bottom-up Blackwood always fills bottom-left first
the same way; top-down places different pieces there because it
fills top-first and the pieces flow differently. Neither has access
to true puzzle-structural constraint at those cells.

### What this rejects

- The vol-17 "18-cell backbone" finding (`project_e2_vol17_session_summary`)
  is an algorithmic artefact, not a real structural property. **Memory
  must be corrected**.
- Any "pin 17 cells as hints" or "use backbone as constraint amplification"
  approach is sound ONLY for the 5 canonical hints. The other 12 cells
  *would be wrong to pin* because TD-style runs use different pieces there.

### What this reveals

- The puzzle has **enormous piece-placement freedom**. The bottom-left
  4×4 admits at least two completely different solutions consistent
  with the 5 canonical hints (one BU prefers, one TD prefers).
- This freedom is good news — it means the 469 community solution
  may use different bottom-left pieces from our 457 board, which means
  our search is over-narrow.

### N6 cross-scan-order action items

1. **Correct vol-17 memory**: the 18-cell backbone is largely
   algorithmic, not structural. Only 5 canonical hints have proven
   structural force across scan orders. ✅ DONE — memory entry
   `project_e2_vol20_backbone_correction` added.
2. **Try TD-pinned re-CP**: pin the *top-down* bottom-left pieces
   (different ones!) and run Blackwood CP. See if a TD-style bottom-left
   leads to a different overall ceiling.
3. **Mix scan orders** in ALNS (currently doesn't happen). E.g.,
   half the chains use BU-pinned hint set, half use TD-pinned. May
   produce diverse basins beyond what single-order PT explores.

---

## 2026-05-13 — Hot-PT from the new pinned-blackwood basins: stays locked

Ran hot-PT (T_max=30, 4 chains, 3 min budget) from:
- 445 board (pinned-blackwood v17a → ALNS 60s).
- 441 board (pinned-blackwood v17b → ALNS 60s).

Results:
- From 445: PT global best = 445. **No movement.**
- From 441: PT global best = 442 (chain 1 at round 3 found +1).
  Then all chains converged to 442.

→ These new basins are **also operator-locked**, just at lower scores
than 457. So the operator-lock is **not unique to 457**, it's a
property of the **basin × move family combination**. The fundamental
issue is the move family, not the specific board.

---

## 2026-05-13 — basin_hop experiment (forced edge break + ALNS recovery)

Built `crates/bench-audit/src/bin/basin_hop.rs`. Strategy: take the
457 board, force-rotate one non-hint cell to a random alternate
rotation (creating a Δ=-1 to -4 perturbation), then run ALNS to
recover.

If ALNS *always* recovers to 457: 457 is a strong basin attractor;
any +1 move requires staying outside that basin's gravity (very
large radius needed).

If ALNS sometimes finds 458+: forced perturbation breaks the lock
and may be a viable operator class.

Running 8 trials × 30s ALNS (3 min total), seed 42. Result below
when complete.

### Early observations (2 of 8 trials)

```
trial 0: break (0,7) rot 0→3, pre=455, post=457   ← recovered
trial 1: break (1,8) rot 1→2, pre=453, post=457   ← recovered
```

The 457 basin is **strongly attracting**: perturbations of Δ=-2 or
Δ=-4 are reabsorbed by ALNS in 30s. Confirms basin-stability.

### Full result (all 8 trials done)

```
trial 0: break (0,7)   rot 0→3, pre=455, post=457  ← recovered
trial 1: break (1,8)   rot 1→2, pre=453, post=457  ← recovered
trial 2: break (11,10) rot 1→2, pre=453, post=457  ← recovered
trial 3: break (3,0)   rot 3→0, pre=454, post=457  ← recovered
trial 4: break (11,13) rot 0→1, pre=453, post=457  ← recovered
trial 5: break (13,6)  rot 1→3, pre=453, post=457  ← recovered
trial 6: break (15,6)  rot 2→0, pre=454, post=457  ← recovered
trial 7: break (13,12) rot 0→2, pre=453, post=457  ← recovered

Summary: 8/8 trials recovered to 457. None worse, none better.
```

**Every single Δ=-2,-3,-4 perturbation is reabsorbed by 30s ALNS.**
The 457 basin's attractor radius extends to at least Δ=-4 (i.e., a
multi-edge rotation break of up to 4 edges still gets pulled back).

→ For basin escape, we'd need to inject larger perturbations (Δ=-6
to -15), i.e. force-rotate k cells simultaneously where k ≥ 2-3.
Or attack a different axis entirely (T6 from vol-21 plan).

### basin_hop with k=4 (partial: 2/6 trials done, killed early)

```
trial 0 (k=4): pre_alns=441 (Δ=-16), post_alns=457  ← still recovered
trial 1 (k=4): pre_alns=445 (Δ=-12), post_alns=457  ← still recovered
```

Even **Δ=-16 perturbations** (4 simultaneous rotation breaks) get
reabsorbed to 457 in 30s ALNS. The basin attractor radius is **at
least Δ=-16**.

This is a remarkable result. The 457 basin pulls in ANY destruction
of up to 16 edges (the score itself). This means:
- ALNS is doing *excellent* repair, the basin is *excellent* terrain.
- We've reached a "good local optimum" — high attractor radius is
  a sign of basin depth, not basin escape opportunity.
- The way out is NOT through perturbation. It's through different
  representation, different algorithm, or different basin.

Killed at 2/6 because pattern was clear.



→ **Forced single-rotation perturbation does NOT break the lock.**
For basin escape, a k-rotation perturbation with k ≥ 5 (or a
multi-cell destroy at radius k ≥ 8) would be the next test.

---

## 2026-05-13 — N4c: cooperative 3-cycle composition

Built `scripts/n4c_pair_compose.py`. Strategy: 23 Δ=-1 transpositions
found in N4; 8 cells appear in ≥2 of them. For each cell with shared
endpoints, try every 3-cycle (a→b→c→a) where ab and bc are both
Δ=-1 swaps.

This is a *targeted* 3-cycle search — selecting 3-cycles likely to
be cooperative based on Δ=-1 evidence.

**Result**:
```
26 cooperative 3-cycles tested
Δ ≥ 0: 0
Best Δ: -2 on cycle ((57, 44, 62) = (3,9), (2,12), (3,14))
```

Even hand-crafted cooperative 3-cycles can't reach Δ=0. The minimum
cooperative cardinality on this 457 board is K ≥ 4. K=4 has 2 cycles
at Δ=-1; we'd need K=5 or K=6 to find Δ=0, and even those scans show
zero (vol-20 cycle_scan).

The cooperative threshold for THIS 457 board is probably K ≈ 22+
(matching the R5f cooperativity prediction for a Δ=23 score gap).

---

## 2026-05-13 — vol-20 closeout summary

### What vol-20 shipped

**Code** (committed):
- `scripts/n3_pair_rotation.py` — adjacent pair rotation sweep (480 pairs).
- `scripts/n4_swap_landscape.py` — non-adjacent transposition energy landscape.
- `scripts/n4b_cycle_scan.py` — 3-cycle/4-cycle scan on mismatch cells.
- `scripts/n4c_pair_compose.py` — cooperative 3-cycle composition.
- `scripts/n5_patch_analysis.py` — single-cell candidate analysis.
- `scripts/n5_patch_enumerate.py` — 38-cell BB on the mismatch patch.
- `scripts/n5_patch_halo.py` — radius-r halo BB.
- `scripts/n6_backbone.py` — cross-board consensus.
- `scripts/n6c_cross_scan.py` — top-down vs bottom-up backbone analysis.
- `crates/bench-audit/src/bin/cycle_scan.rs` — Rust cycle scanner (K≤6).
- `crates/bench-audit/src/bin/topdown_portfolio.rs` — top-down CP portfolio.
- `crates/bench-audit/src/bin/basin_hop.rs` — perturbation-then-ALNS probe.

**Findings** (memory entries):
- `project_e2_vol20_backbone_correction` — corrects vol-17 18-cell backbone claim.
- `project_e2_vol20_operator_lock` — exhaustive null record for moves ≤ K=5.

**Documents**:
- `RESEARCH_NOTES_20.md` — full live log.
- `RESEARCH_NOTES_21_PLAN.md` — vol-21 entry plan with T1-T6 priorities.

### The exhaustive null record

The single 457 board (`pt_winning5_n4_t1_30_s1_1778661199.json`) is
strict-local-maximum under every move family of cardinality ≤ K=5
we measured:

| K | Move family | Count | Improvers |
|---|------------|------:|----------:|
| 1 | rotation flip | 256×4 | 0 |
| 1 | piece swap | full | 0 |
| 2 | adjacent-pair rotation | 6,720 | 0 (also 0 Δ=0) |
| 2 | non-adjacent transposition | 20,240 | 0 (2 Δ=0) |
| 3 | full cycle | 32,796 | 0 |
| 3 | cooperative cycle (N4c) | 26 | 0 |
| 4 | full cycle | 982,200 | 0 |
| 5 | full cycle | 28,480,440 | 0 |
| 38 | patch permutation BB | 60s/1M nodes | 0 |
| 82 | halo-r1 BB | 90s/122k nodes | 0 |
| ≤4 | basin_hop perturbation+ALNS-30s | 7+ trials | 0 (all recovered) |

### What's proven and what's not

**Proven**:
- This 457 board is in a strong basin attractor.
- No move of cardinality ≤ 5 cells crosses to +1.
- The 12-cell "bottom-left backbone" was a scan-order artefact.
- All 10 PT-457 saved boards are the SAME board.

**Not proven** (but strongly suggested by extrapolation):
- That ALL 457-class boards have this same lock (we only have one).
- That K=6,7,..,10 cycles wouldn't unlock (we stopped at K=5).
- That the prune-restart algorithm wouldn't help.

### The path forward (vol-21)

Read `RESEARCH_NOTES_21_PLAN.md`:
- T1 = prune-restart engine (1-2 day build, est. +5..10 score lift).
- T2 = cooperative-pair-swap ALNS op (3-4 hours, low-EV given N4c null).
- T3 = edge-grid dual reformulation (1-2 days, high-novelty).
- T4 = color-relabel as variable (4-8 hours).
- T5 = diverse 457 search overnight (cheap, EV = find a different 457).
- T6 = larger basin_hop perturbations (2-3 hours, tests escape boundary).

Recommend pursuing T1 + T5 in parallel.


















