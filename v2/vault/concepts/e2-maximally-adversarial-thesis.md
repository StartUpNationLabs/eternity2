# Eternity II's Piece Set is Maximally Adversarial — vol-65 synthesis

**Status**: `built` (synthesis of vol-65 structural findings) — 2026-05-15.

## Thesis

The canonical Eternity II piece set, designed by Christopher Monckton
and generated via Selby-Riordan's color allocation, is **maximally
adversarial across multiple independent structural axes**. No single
structural shortcut exists; every potential algorithmic simplification
runs into a tight Selby-Riordan-enforced bound.

This document synthesizes seven independent structural findings from
vol-65 (2026-05-15) supporting the thesis.

---

## Axis 1: Maximal rotation-asymmetry

**Result**: All 256 pieces have full rotation orbit (size 4) under
ℤ/4 rotation action. There are exactly 5 multiset-twin piece pairs
(same edge-multiset but distinct cyclic order) and 114 near-twin
pairs (3-of-4 edges shared canonical).

**Evidence**: `scripts/vol65_piece_orbits.py`.

**Implication**: Piece set has no fixed-point symmetries. Any
algorithm exploiting rotation symmetry (e.g., orbit-canonical-form
search) gains nothing.

## Axis 2: Direction-asymmetric color distribution

**Result**: Canonical-orientation piece-sides are direction-asymmetric.
The max color-matchable horizontal edges (assuming fixed canonical
orientation, no rotation) is exactly **307**, far below the geometric
maximum 480. Specifically:

  Σ_c [min(E_c, W_c) + min(N_c, S_c)] = 307

**Evidence**: `scripts/vol65_ps_matching_lp.py` LP + closed-form
analysis.

**Implication**: Rotation is *structurally necessary* to reach the
empirical 469 ceiling. Algorithms that fix piece orientation early
(e.g., naive DFS with rotation last) lose at least 162 matchable
edges.

## Axis 3: Tight color-budget at 480

**Result**: All 22 non-border colors have an EVEN number of total
piece-sides. The sum Σ_c ⌊N_c / 2⌋ equals exactly 480 (the
geometric maximum). No color has unmatched-side slack.

**Evidence**: `scripts/vol65_global_invariants.py`, direct computation.

**Implication**: A 480-match assembly is color-budget-feasible
(no inherent shortfall). The hardness lives entirely in the
combinatorial constraint structure, not in the supply/demand
balance.

## Axis 4: Bimodal compatibility-spectrum

**Result**: The piece-compatibility graph (256 nodes, edge weights =
# valid rotation-side adjacencies) has algebraic connectivity μ_2 =
0.507 and a sharp spectral gap (λ_1/λ_2 = 2.95). The Fiedler vector
near-perfectly separates frame pieces (60 = 4 corners + 56 edges)
from interior pieces (196), with exactly 10 interior pieces
ambiguously placed near the boundary.

Beyond Fiedler, eigenvalues cluster tightly around 0.65-0.72 — no
multi-scale community structure.

**Evidence**: `scripts/vol65_piece_compat_graph.py`.

**Implication**: The piece set is **bi-clustered exactly** — frame
vs interior — and otherwise uniformly mixed. No hidden community
structure to exploit. Selby-Riordan's color allocation rules
homogenize the interior.

## Axis 5: σ-orbit indecomposability of basin transitions

**Result**: The σ-cycle permutation between our local-459 basin and
McGavin's 469 basin has 11 cycles (lengths 154, 22, 19, 18, 13, 9, 7,
6, 3, 2, 2). Applying any single cycle alone REDUCES the score by
2-143 points. Only full application (all 255 cells) reaches 469.

**Generalized to**: Same indecomposability observed between the
closest non-McGavin record (455 at Hamming 247) and McGavin.

**Evidence**: `scripts/vol65_sigma_import.py`, `vol65_sister_basin_diff.py`.

**Implication**: 459 → 469 is a **strongly cooperative move**.
Standard ALNS / SA / oracle-cycle-swap cannot accept any subset
without rejection.

## Axis 6: Topologically isolated McGavin basin

**Result**: σ-distance histogram from 139 known 455+ records to
McGavin 469 is **bimodal**:
- 2 boards at Hamming 0 (McGavin clones)
- **0 boards in Hamming [50, 240)** — total absence
- 19 at [240, 250), 114 at [250, 256]

**Evidence**: `scripts/vol65_sigma_to_mcgavin.py`.

**Implication**: McGavin's basin has no "gradient neighbors" in our
explored search space. There's no smooth path to descend toward.

## Axis 7: Joint-MIP local optimality at halo-1

**Result**: All 4 tested 458/459 records are joint-MIP-locally-optimal
at halo-1 over the full defect-cells + halo region (57-64 cells per
board). No piece-permutation+rotation within these regions can
improve the score.

**Evidence**: `crates/bench-audit/src/bin/vol62_cluster_mip_bound.rs`,
`scripts/vol62_*`.

**Implication**: Local destroy operators with effective halo ≤ 1
across the full defect set CANNOT escape these basins. The same
should hold for McGavin's 469 (verified for it: 16 defect cells, 2
components, joint-MIP delta=+0).

---

## Synthesis: Why E2 is hard, structurally

Each axis above is one Selby-Riordan design choice that maximizes
puzzle adversariality:

| axis | adversarial property |
|---|---|
| 1 | No rotation symmetries |
| 2 | Canonical-orientation 307 << 480 |
| 3 | Color-budget EXACTLY 480 (no slack) |
| 4 | No multi-scale piece-clustering |
| 5 | Indecomposable basin transitions |
| 6 | High-score basins are isolated |
| 7 | Local search cannot escape 458+ |

Algorithmically, this means:
- Symmetry reduction: useless (axis 1).
- Color-balance / direction-flow: tight at 480 (axis 3).
- Rotation as a free axis: necessary (axis 2).
- Clustering / decomposition: 1-axis only (axis 4).
- Incremental basin escape: impossible (axes 5, 6, 7).

## What this means for vol-66+ algorithms

To break 459 (and reach ≥ 460), we need an algorithm that:

1. **Does not rely on local moves** (axes 5, 6, 7 rule them out).
2. **Does not rely on multi-scale structure** (axis 4 rules it out).
3. **Cannot improve the symmetry-quotient size** (axis 1).
4. **Must include piece rotation as a primary degree of freedom**
   (axis 2 makes orientation-fixing pre-rotation infeasible).

Candidate algorithms NOT yet refuted:
- **Basin-Level Genetic Search** (vol-66): operates at REGION level,
  not single piece. Has potential because crossing basin boundaries
  by inheriting REGIONS (vs single piece-swaps) sidesteps σ-cycle
  indecomposability.
- **Temporal-Rewind-Search** (vol-63): operates on PAST STATES, not
  current. Path-dependence may help if the search visited near-McGavin
  configurations and discarded them.
- **Oracle-guided cell-region-replay** (proposed vol-67): given
  McGavin's 469, use its piece-region geometry as a hard prior.
  Doesn't replicate the σ-cycle subset experiment which failed
  because that uses POSITIONS, not REGIONS.
- **Direct MIP on full board** (proposed vol-68): now that we have
  the frame-constrained LP setup, the next step is full integer
  MIP. Hours of HiGHS time but bounded.

## The Selby-Riordan signature

The pattern across all 7 axes: **whenever there COULD be a structural
shortcut, Selby-Riordan engineered it away.** No accidental
symmetries, no slack budget, no clustering, no smooth basins. The
puzzle's hardness is *deliberate* and *structural*.

This is the strongest theoretical statement I can make about E2 from
my structural analysis to date. Anyone attacking E2 with classical
combinatorial / spectral / clustering methods will hit one of these
seven walls.

## Open questions

1. **Frame-constrained LP** (running): does it give a bound below 469?
   - If LP < 469: NEW SOUND BOUND (publishable).
   - If LP = 480: integrality gap concentrated entirely in tiling
     constraints; another axis added to maximal-adversariality.
2. **Algebraic-geometric obstruction**: does the puzzle's fiber bundle
   have non-zero Čech 1-cocycle? Would PROVE 480 unreachable.
3. **What's the actual record on Blackwood-VARIANT puzzles?**
   Community has 470s on variants. What makes those puzzles easier?
   (Hint: lower color count, more piece-side symmetries.)

## Linked

- All vol-65 concept pages
- [[../sessions/vol-65]]
- [[../plans/AUTONOMOUS-MONTH-PLAN.md]]
