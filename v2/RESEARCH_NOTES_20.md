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


