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

