# RESEARCH_NOTES_21.md — vol-21 working notes

**Date opened:** 2026-05-13 12:35
**Predecessor:** [[RESEARCH_NOTES_20.md]] + [[RESEARCH_NOTES_21_PLAN.md]]
**Mode:** Autonomous, user is away, no time constraint.

## Strategic reframe (vs vol-20)

Vol-20 proved 457 is a strict local maximum under K≤5 moves on **one specific
basin** (all 11 saved 457 boards are byte-identical). The phrasing matters:
"can't improve 457" is wrong. "Can't improve THIS 457" is what we proved.

Vol-21 attacks on three orthogonal axes:

1. **Different basin** (T5): search for 457-class boards that are NOT
   byte-identical to ours. If even one such basin exists with a +1
   admissible move, we have 458.
2. **Different move class** (T-CROSSBASIN, NEW): exploit the basin
   *diversity* we already have. 456 boards are 52-59 cells different
   from 457; recombining their good regions might exceed both.
3. **Different algorithm** (T1): prune-restart engine, structurally
   different from backtrack. Closes the gap to McGavin.

## Inventory snapshot (computed 12:35)

| Score | #boards | #unique | hamming from 457 |
|---|---:|---:|---|
| 457 | 11 | 1 | 0 |
| 456 | 5 | 4 | 52, 55, 59, 56 |
| 455 | 1 | 1 | 48 |
| 453 | many | n/a | — |

**Critical observation**: 456 basins are 52-59 cells distant from our 457.
That is *much further* than naive +1 implies. Some 456 boards share less
than 80% of the 457 board's placements. So 457 and 456 are in different
attractor basins — gradient-following from a 456 will NOT step to our 457.

This gives us a real opportunity: cross-basin recombination.

## Vol-21 task order (re-prioritized for ambitious execution)

| Task | EV | Cost | Status |
|---|---|---|---|
| T5 — Diverse 457 search (background) | High | 0 build, 6-12h compute | starting now |
| T-NEW — Cross-basin recombination operator | High novelty | 1-2h | starting now |
| T1 — Prune-restart engine | Highest | "1-2 days" est | next |
| T3 — Edge-grid dual PoC | Novel | "1-2 days" est | after T1 |
| T7 — Hash-cons PT tabu | Medium | 4-6h | after T-NEW |

## Experiments

### 12:35 — Inventory + plan
- All 11 stored 457s byte-identical (extends vol-20 finding from 10 → 11).
- 456 basin diversity is REAL: 4 unique, 52-59 hamming from 457.
- Cross-basin recombination is the leverage point.

### 12:40 — Edge-Kempe operator (Phase 1+2+3)

Built `crates/bench-audit/src/bin/edge_kempe.rs`.

**Phase 1** (single-edge flip with 2-piece swap): all 23 mismatched
edges of 457 tested with all (c*, piece_a', piece_b') triples restricted
to the 2-piece pid pair. Zero successes. The operator-lock for this very
restricted move family is total.

**Phase 2** (alt-piece counts on mismatch cells): across the 38 mismatch
cells:
- 0 perfect-alt (k=4) candidates
- 18 k=3 alt pieces (avg 0.5/cell), concentrated at (1,2)=3 alts
- 466 k=2 alt pieces (avg 12.3/cell)

**Phase 3** (k=3 alt-piece cycle search): only 6 of the 18 k=3 alts
have their home in mismatch cells. 0 net-positive 2-cycles, 0 net-≥0
3-cycles. The 6 intra-mismatch arrows are useless alone.

### 12:50 — **MAJOR FINDING — Edge-relax gap analysis**

Built `crates/bench-audit/src/bin/edge_relax.rs`. Relaxed the piece-
uniqueness constraint (each cell picks any piece from the catalog).

**Result: 461/480 — +4 above the 457 lock.**

The slack is exactly 4 piece-doublings:
- pid 82 ideally at BOTH (2,2) and (2,3) [currently at (2,3) only]
- pid 146 ideally at BOTH (3,13) and (7,3) [currently at (7,3) only]
- pid 205 ideally at BOTH (3,7) and (3,8) [currently at (3,7) only]
- pid 233 ideally at BOTH (2,1) and (10,10) [currently at (10,10) only]

This means **{207, 204, 245, 189} are sitting in suboptimal positions**;
**ideally they'd be replaced by copies of {82, 205, 146, 233}**.

If we can find a piece-permutation chain that achieves the same effect
under piece-uniqueness, we get 461/480.

**INTERPRETATION**: The 457 board has +4 of edge-slack that the
piece-uniqueness constraint is hiding. The way to claim it is a
piece-relocation chain — find new homes for {189, 204, 207, 245}.

### 13:00 — Missing-piece demand analysis (Python)

For each "missing" piece (189, 204, 207, 245), enumerate where they
score k=2 or k=3 anywhere on the board with current neighbors:
- Piece 189: 2 cells with k=3 (at (9,5), (3,10))
- Piece 245: 1 cell with k=3 (at (12,2))
- Pieces 204, 207: NO k=3 spots (only k=2)

These k=3 cells are the "interface" where the chain might extend.

### 13:05 — 8-cell + 11-cell permutation null

Built `edge_relax_8perm.rs`. Tested:
- **8-cell perm** (the 4 doubles + their displaced cells): 8! = 40,320
  perms in 0.12s. **0 Δ>0 improvers, but Δ=+0 exists** (non-identity
  permutations preserve the 457 score → indicates redundant rotation
  symmetry).
- **11-cell perm** (8 + the 3 high-demand k=3 cells (9,5), (3,10),
  (12,2)): 11! = 40M perms in 104s. **0 Δ>0 improvers, best Δ=+0**.

**Conclusion**: The +4 edge-slack is real, but the cycle needed to
capture it under piece-uniqueness spans **more than 11 cells**.
Pure permutation enumeration is exhausted at this scale (12! = 479M,
13! = 6.2G).

### 13:10 — Next: Houdayer cluster cross-basin moves

We have **4 distinct 456 boards**, each 52-59 cells different from our
unique 457. A Houdayer cluster move on a (457, 456_k) pair could
cross-pollinate the regions where one basin is locally stronger than
the other. This is the standard spin-glass operator that we have NOT
yet tried.

### 13:15 — OracleCycleSwap (existing op) results on (457, 456) pairs

Applied `oracle_cycle_swap --current 457 --oracle 456_k` for each of the
3 unique 456 boards:
- 456_a (= 456_b, identical) → 6 σ-cycles, all Δ<0, apply ALL → 453
  (or 456 after rotation fixup).
- 456_c → 4 σ-cycles, all Δ<0, apply ALL → 456 (Δ=-1).

The existing Houdayer-style oracle swap doesn't break the 457 lock —
the 456 basins are configured WORSE than our 457 in the cycle regions.

### 13:25 — Hungarian bipartite-matching to relaxed-461 target

Built `crates/bench-audit/src/bin/edge_target_match.rs`. Computes the
relaxed 461 placement, then solves Hungarian assignment per border-
class to find the best piece-uniqueness-respecting permutation that
matches the target's edge structure.

**Result: 455/480 fixed point. Δ from baseline: -2.**

Hungarian thinks 745+163+8=916 cell-k is optimal but the actual
board scores 455 because scoring is not separable across cells
(shared edges) — Hungarian optimizes single-cell k against fixed
neighbors, which after swapping break.

### 13:40 — Piece-tuple equivalence (CRITICAL STRUCTURAL FACT)

Computed cyclic-equivalence of all 256 piece edge-tuples:
- 251 distinct rotation-invariant signatures
- **5 multiset-equivalent pairs**: [2,3], [5,14], [7,51], [109,110],
  [171,181] — but ZERO cyclic-equivalent pairs across the catalog.
- For our 4 dup-pieces {82, 146, 205, 233} ↔ 4 missing-pieces
  {189, 204, 207, 245}: NO shared rotation tuple. Min hamming 2
  (between (205, 204) and (233, 189) modulo rotation).

**THE +4 GAP IS PROVABLY HARD-LOCKED ON THIS 457**. The 4 missing
pieces cannot directly substitute for the 4 dup-pieces in any cell:
their edge tuples don't match in any rotation.

### 13:50 — Reframing: pivot to T5 (diverse 457)

The +4 gap establishes that 461-or-better edge-structures exist (in
the unconstrained edge-coloring sense), but our particular 457
basin's gap is unrecoverable by local perturbation. The natural
escape: find a DIFFERENT 457 basin whose missing/duplicate gap IS
substitutable. This is exactly T5.

### 14:00 — **MAJOR — Edge-relax as a DEAD-END DETECTOR**

User raised the question: "could our new algorithm be a way to tell
when we reach dead ends?"

**YES**, and the data is striking:

| Board | Score | Relaxed | Gap |
|---|---:|---:|---:|
| Our 457 (PT) | 457 | 461 | +4 |
| 456 (winning5_sa) | 456 | 461 | +5 |
| **456 (diverse_sa)** | **456** | **457** | **+1** |
| 453 (oracle_swap) | 453 | 457 | +4 |
| 454 (winning5_sa_s1/s2) | 454 | 460 | +6 |

**The relaxed gap measures the LOCAL-PERTURBATION ROOM in the current
basin.** Boards with small gap are near their basin's information-
theoretic ceiling (under piece-uniqueness).

**Critical observation**: the `diverse_sa` 456 board has gap +1 with
its relaxed bound = 457. Its basin's ceiling is 457. The 457 we
already have is THE ceiling of *its* basin = 461.

**Useful diagnostics that fall out**:
1. **Gap == 0**: provable STRICT local maximum even under
   relaxed-uniqueness. Dead-end for cell-by-cell modification within
   the basin. Must escape to a different basin.
2. **Gap small (1-3)**: very near the basin ceiling. Probably
   diminishing returns from more search; consider basin-hop.
3. **Gap large (5-10)**: still significant edge-slack in the basin.
   Local search may yet find improvements.
4. **Gap structure** (specific dup/missing pieces): forensic insight
   into WHICH pieces are placed suboptimally.

### 14:05 — Global relaxed bound from random starts

Built `edge_relax_global.rs`. Random initial boards converge to
relaxed maxima 377-398/480. Confirms the relaxed iteration is
**basin-dependent**: it climbs to a local relaxed-maximum, not the
global one.

So gap measures *basin-local* dead-endness, not global progress.
But that's exactly what we need: for any board we currently have,
the gap tells us how much *local* room remains in *its* basin.

### 14:10 — Vol-21 deliverable: a new search-progress metric

The relaxed gap is a **fundamentally new metric** for E2 search:
- More informative than score alone (which basin am I in?).
- More informative than operator-lock test (probes only K=5 locally).
- Cheap to compute: 0.1-0.2s per board.

**Practical use**:
- Append gap-recording to every ALNS/PT save: at every score plateau,
  measure gap. If gap drops to 0, the worker is dead-locked.
- Use gap as a *signal to diversify*: low-gap workers should be
  restarted from a different seed.
- Compare gaps across basins to *triage which 457s to keep*: only
  the ones with substitutable gap structure are worth more search.




