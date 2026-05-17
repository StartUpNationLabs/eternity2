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

## Top 2 picks by EV (post-retraction)

1. **AlphaMapleSAT-style MCTS-CnC** on our existing kissat encoding.
   Engineering-heavy but addresses the actual bottleneck (kissat alone
   can't decide canonical E2). The reward signal (CDCL conflict-rate
   per cube) is concrete and doesn't depend on any symmetry property.
2. **Projected model counting** (D4 / GANAK) over border variables.
   Asks "how many BORDERS admit any 480 interior" instead of "find
   one". A counter could return 0 (provable unsolvability) or a small
   number (enumerable target list). Treewidth-bounded → in-principle
   tractable for the border ring.

Idea #1 (corner symmetry-break) retracted above. The user-noted lesson:
**don't apply textbook symmetry tricks to a maximally-asymmetric Selby
puzzle without checking the vault**. Any future "factor-K speedup
from breaking [some symmetry]" claim must first verify the symmetry
*actually exists* on canonical E2.

## Linked

- [[w11-border-screen-unviable]] (why we're here)
- [[../plans/INVENTIONS_BACKLOG]] (add W12-W18 entries)
- [[sessions/vol-124]] (sister session page)

## Sources

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
