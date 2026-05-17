---
name: vol-124-roaming
description: "Vol-124 supplementary: literature roam after retiring W11 as a primary engine. Surveyed 7 distinct research directions (Sep-Dec 2025 + ICALP 2025 + arxiv 2024-2025). Three high-EV ideas surfaced for E2 attack."
metadata:
  type: session
---

# Vol-124 — literature roam (post-W11-retirement)

User directive: *"let's roam on the internet to explore and potentially
find new ideas like if we were exploring a library or a science school."*

## Ground state of the literature (as of May 2026)

- **E2 record (community)**: 468 matched edges, 2020 (no improvement
  since). Wikipedia agrees.
- **No 480 solution publicly known**: only Selby & Riordan reportedly
  have one.
- **Two-phase Selby-Riordan algorithm** confirmed as the historical
  state-of-the-art (~META 2010): set up "favorable state" of the most
  awkward pieces first, then exhaustively search the easy region.

## Seven ideas surfaced

### 1. AlphaMapleSAT (Vajda et al. 2024, arxiv 2401.13770) — HIGH EV

**MCTS-based cube-and-conquer SAT.** MCTS *picks the variables to cube
on* using deductive feedback from short CDCL runs as reward. Achieves
1.6-7.6× wall-clock speedup vs March's lookahead cubing on Ramsey,
Kochen-Specker, Murty-Simon — the closest analog problems to E2 in the
SAT literature.

**Fit to E2**: our 1h kissat run on canonical E2 (167k vars, 5.8M
clauses) makes no decision. CnC partitions the search space into
disjoint cubes (partial assignments), parallel-solves each. MCTS picks
*which variables to split on*, guided by which splits actually reduce
the work. Speedup is wall-clock real, not just theoretical.

**Action**: build a CnC wrapper around our existing kissat encoding.
Split on the 4 corner pieces' placements + the 5 hint-adjacent pieces.
That gives 24 × ~9 = ~216 cubes, each ~7s SAT call. Total ~25 min ×
8 cores = 3 min wall-clock vs 1h kissat solo. If still no decision,
deepen cubes by another layer.

### 2. ~~SAT Modulo Symmetries~~ — RETRACTED 2026-05-17 by user

**Initial proposal**: pin TL corner piece+rotation as a unit clause for
96× search-space cut. **Wrong on this puzzle.**

User correctly noted (see [[E2_KNOWN_FACTS]] and [[INVENTIONS_BACKLOG]]
item D1 marked `wont-do (vol-27) DO NOT REVISIT`):

- Canonical Selby-Riordan E2 has **0 rotation-symmetric pieces** (all
  256 piece orbits are size 4).
- The 5 canonical hints at positions {135, 210, 34, 221, 45} are
  **not 4-fold-symmetric** — they fix the board's absolute orientation
  and break any rotation pseudo-symmetry the unhinted puzzle might
  appear to have.
- Therefore: there is no "24 corner perms equivalent up to TL fixing"
  quotient. Each of the 4 corner pieces has a unique correct position
  in the hint-oriented frame; pinning TL is just an arbitrary 4-way
  branch the CDCL solver handles cheaply.

**Lesson**: symmetry-breaking is a major SAT trick on *random* or
*generic* CSPs, but Selby-Riordan deliberately designed canonical E2
to be **maximally asymmetric** (vol-65). Standard textbook tricks from
the symmetry-breaking literature **do not apply** here.

This is the kind of mistake the vault is supposed to prevent —
re-discovering "no symmetries" after vol-27, vol-65, and vol-118 all
established it. Logging here so the next vol catches it.

### 3. PI-GNN / Physics-Inspired Graph Coloring (arxiv 2408.01503) — MEDIUM EV

Statistical-mechanics-trained GNN solves graph coloring near the
*dynamical phase transition* (the theoretical hard regime). Generalizes
from small to large graphs.

**Fit to E2**: limited. E2's domain at each cell is ~700 piece-rotations,
not k=4 colors. PI-GNN was for k-coloring; adapting to "k=700-domain"
isn't direct, but the *training methodology* (planting + symmetry-
breaking reg + noise-annealing) is borrowable.

**Action**: defer. Worth a follow-up vol if we get an instance-encoding
match.

### 4. TNMCMC (arxiv 2509.23945, Sep 2025) — LOW EV for E2

Tensor-network proposals + Metropolis acceptance. Works on 3D lattices
with spatial locality. **E2 doesn't have 3D structure; constraints are
2D adjacency**. Geometric mismatch.

**Decision**: not pursuing for E2 directly. The *idea* (tensor-network-
informed MCMC proposals) is one we've already touched with W1
PEPS-Lagrangian.

### 5. BP-guided decimation on k-XORSAT (ICALP 2025) — MEDIUM EV

Latest theoretical analysis: BP-decimation succeeds up to clustering
threshold, fails beyond it. **Identifies a hard regime where decimation
provably gets stuck**. We already saw this empirically: W2 BP-decimation
reaches 435/480 then plateaus.

**Implication**: E2 likely lives in the post-condensation regime.
**BP-decimation alone cannot solve it**, but BP marginals + an
escape mechanism (replica-symmetry-breaking / Survey Propagation,
or backtracking on the most-condensed cells) might.

**Action**: re-instrument W2 to detect the cluster-condensation point
during decimation, then switch to backtracking on those cells.

### 6. Projected Model Counting on Bounded Treewidth (Fichte et al. 2023,
arxiv 2305.19212) — MEDIUM EV

**Counts SAT solutions in time O(2^(2k+4) × n²)** where k = treewidth.
For E2's primal graph, treewidth is small in border-only or row-only
sub-puzzles. **A counting algorithm could prove 480 has 0 solutions**
if treewidth is small enough, OR enumerate all 480 solutions.

**Action**: measure treewidth of E2's primal/incidence graph. The
border ring has treewidth ≤ 60; interior has much higher. If we can
*project* away interior variables (compute the number of valid border
configs that admit any 480 interior), the projection is small. This
is what W11 was trying but with kissat instead of a counter. **Use
a real counter** (D4, GANAK, sharpSAT-TD).

### 7. Selby-Riordan generator hint (re-read literature) — UNCERTAIN

Wikipedia confirms: Selby & Riordan reportedly hold a 480 solution but
have never published it. Their hint placement at the 5 canonical cells
is *not* arbitrary — it likely encodes a constraint that biases the
puzzle toward exactly one 480 basin.

**Action**: re-read the original Selby paper if findable. Check whether
the hint placement reveals the algorithm.

## Round 2 — deeper roam (after backlog audit + Wang-tile literature)

### 8. Salassa-Vancroonenburg "MILP + Max-Clique" (arxiv 1709.00252) — UNKNOWN EV

**Max-Clique formulation**: nodes = (tile, position, rotation); edges
between non-conflicting nodes. Solve for clique of size n² (=256 for
E2). Published 2017, provided 3×3 to 9×9 instances as benchmarks but
"larger sizes hard to manage."

**Fit**: this IS the formulation we'd write if we tried max-clique. The
authors said canonical 16×16 was beyond practical clique solvers in
2017. Modern clique solvers (PMC, MoMC, mokas) may have moved the
goalpost. Worth a fresh ablation.

### 9. Heule 2008 SAT encoding + Ansótegui-Sellmann-Tabar — REFERENCE

The encoding we already use IS effectively Heule 2008 / Ansótegui-
Sellmann-Tabar 2008 (the comment in `crates/benchmark/src/bin/sat_e2.rs`
confirms this). So we're at SOTA on the SAT encoding axis already.
Nothing new in the literature on the encoding itself.

### 10. Kovalsky-Glasner "Global approach" (arxiv 1409.5957) — REFUTED ON E2

**Their LP+SDP "Vandermonde" formulation explicitly fails on E2.**
Quote from §5.2.3: *"We haven't had as much success with larger
problems, such as the Eternity II puzzle, which pose a considerable
combinatorial challenge."* They solved 12×12; 16×16 was out of reach.

**Decision**: do NOT pursue W3 (Vandermonde-LP) for canonical E2 —
the authors themselves said it won't work. Task #59 should be marked
`wont-do (vol-124, authors explicit failure on E2)`.

### 11. Bourreau-Stoyan-Pasternak "Variable Transformation to 2×2"
(IEA/AIE 2020) — HIGH EV (NEW IDEA)

**Move the problem from 1×1-cell domain to 2×2-cell domain.** Instead
of "place piece P at cell C with rotation R", solve "place 2×2 block
B at 2×2-cell position B_pos". Each 2×2 block is a 4-tuple of compatible
(piece, rotation) quartets with internal edges already matched.

**Why it works**: when you build the 2×2 alphabet upfront, you've
*precomputed* all 2×2 internal matchings. The resulting search at the
2×2 level has higher arity but **dramatically fewer choices** at each
super-cell. Authors claim "orders of magnitude smaller search spaces"
+ "statistically exploitable features" the 1×1 lacks.

**This is genuinely orthogonal to anything we've tried.** Our naive
piece-rotation-cell encoding has ~700 options per cell. The 2×2
encoding's super-cells have far fewer (most 2×2 quartets don't form
internally-consistent blocks).

**Action**: build a 2×2-block enumerator for canonical E2. For each
8×8 super-grid cell, list all 2×2 quartets that internally match (≈
piece⁴ × rotation⁴ × matching constraints). Likely ~1000-100000 valid
blocks per super-cell vs the naïve 700 single-cell options — but
each block fixes 4 cells × 4 sides = 8 *external* color matches.
Then encode 2×2-as-CSP and run kissat / SAT.

### 12. "Fast Global Filtering for Eternity II" — UNKNOWN (gated paper)

Title alone suggests a CSP propagator specific to E2 that filters
infeasible (cell, value) pairs globally (not just local AC-3).
Worth tracking down — could integrate with our solver-engine.

## Top 3 picks by EV (post-round-2 roam)

1. **2×2 super-block CSP/SAT encoding** (Bourreau et al. 2020). The
   only genuinely novel encoding axis in the round-2 roam. Builds the
   2×2 alphabet upfront, then solves on an 8×8 super-grid with much
   smaller per-super-cell domains. Orthogonal to everything we've
   tried. Engineering: medium (build alphabet generator + re-encode).
2. **AlphaMapleSAT-style MCTS-CnC** on our existing kissat encoding.
   Engineering-heavy but addresses the actual bottleneck.
3. **Projected model counting** (D4 / GANAK) over border variables.
   Counts solutions over a projection. Returns 0 = unsolvability proof,
   > 0 = enumerable list of candidate borders.

### Refuted by literature this roam (so we don't redo)

- **W3 Vandermonde-LP** (Kovalsky-Glasner 2014) — authors explicitly
  failed on E2. Mark task #59 `wont-do`.
- **Continuous SDP relaxation** generally — same authors confirmed
  SDP "limited scalability dominated by the number and dimension of
  positive definite constraints." Don't reattempt.
- **Symmetry-break corners** — canonical E2 has no symmetries (vol-27
  backlog D1 `wont-do DO NOT REVISIT`).

## Backlog cleanup actions

- Mark W3 (`task #59 Vol-123 W3: Kovalsky-Glasner Vandermonde-LP relaxation`)
  as `wont-do` with reason "authors' own §5.2.3 declared E2 out of reach".
- Add 2×2-block encoding to INVENTIONS_BACKLOG as new item (E4? J8?).

## Linked

- [[w11-border-screen-unviable]] (why we're here)
- [[../plans/INVENTIONS_BACKLOG]] (add W12-W18 entries)
- [[sessions/vol-124]] (sister session page)

## Sources (round 2)

- Bourreau et al. "Variable Transformation to 2×2 Domain Space" (IEA/AIE 2020): link.springer.com/chapter/10.1007/978-3-030-55789-8_19 — gated, abstract only
- Salassa-Vancroonenburg "MILP + Max-Clique for E2": arxiv.org/abs/1709.00252
- Kovalsky-Glasner-Lipman-Basri "Global approach for edge-matching": arxiv.org/abs/1409.5957 (E2 refuted §5.2.3)
- Tyburec-Zeman "Bounded Wang tilings": arxiv.org/abs/2205.02295 + nature.com/articles/s41598-023-31786-3 — gated
- Heule 2008 "SAT for edge-matching": foundational; matches our encoder
- Wikipedia: Wang tile, Edge-matching puzzle, Eternity II puzzle

## Sources (round 1)

- AlphaMapleSAT: arxiv.org/abs/2401.13770
- SAT Modulo Symmetries (cube-comp): arxiv.org/abs/2501.17201
- PI-GNN coloring: arxiv.org/abs/2408.01503
- TNMCMC: arxiv.org/abs/2509.23945
- Projected MC + treewidth: arxiv.org/abs/2305.19212
- BP-decimation on k-XORSAT (ICALP 2025): drops.dagstuhl.de/storage/00lipics/lipics-vol334-icalp2025/LIPIcs.ICALP.2025.47
- D-Wave spin glass benchmark (PRX Research 2025): arxiv.org/abs/2501.01107
- Hardness of edge-matching: arxiv.org/abs/1701.00146
- 2-phase hyperheuristic for E2 (historical): semanticscholar Wauters & Vancroonenburg
- Eternity II Wikipedia / Grokipedia (state-of-the-art as of Nov 2025: 468)
