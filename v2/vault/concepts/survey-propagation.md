---
tags: [concept, message-passing, refuted]
status: refuted
origin-vol: 11
---

# Survey propagation (1RSB cavity method)

**Status**: `refuted` (vol-11)
**Origin**: vol-11
**Files**: `scripts/v11_sp.py`, `scripts/v11_bp_decimation_v2.py`

## Hypothesis (Mézard-Parisi-Zecchina 2002)

SP extends [[bp-marginals]] with a Parisi parameter `m ∈ [0, 1]` that, in 1RSB-shattered landscapes, sharpens marginals around clusters of solutions. Successful on random k-SAT, q-coloring, NAE-SAT near phase transitions.

## Refutation (vol-11)

### Cavity-method theoretical block (2026-05-11 agent verdict, pre-experiment)
- Cavity method assumes locally-tree-like factor graph.
- E2 is a 2D grid with short cycles in every 2×2 block → cavity ansatz breaks.
- Empirical analog (Edwards-Anderson spin glass on 2D/3D grids) has glassy plateaus; SP famously fails there.
- Zero published successes for SP on Latin squares, sudoku, jigsaw, or any structured combinatorial puzzle.
- Cited: Maneva-Mossel-Wainwright arXiv:cs/0506053.

### Empirical confirmation (vol-11)

m-sweep on canonical E2 (cell encoding):

| m | interior reduction |
|---|---|
| 1.0 (≡ BP) | 8.3% |
| 0.8 | 7.9% |
| 0.5 | 7.5% |
| 0.30 | 7.3% |
| 0.15 | 7.0% |

**Lower m flattens marginals, not sharpens.** REVERSED from random k-SAT. E2 is SAT-regime (≈1 expected solution per McGavin's complex theory), not clustered.

### SP-decimation as solver

Best single shot (sweep_6: damping=0.3, m=0.30, batch=1): **depth 125 / score 211 in 316s** before contradiction. Vs BP-decimation (m=1.0): depth 113 / score 177. SP-y at m=0.30 is the best decimation policy of those tried — *despite* flatter marginals — because clustering parameter discriminates which low-confidence direction to commit. Still well below baseline CP (depth ~174, score ~303 at 5min).

## Verdict

**Do not propose SP/BP for E2 unless someone has a fresh result on grid-structured factor graphs.** This is theorem-level, not "we haven't tuned it enough."

## Linked concepts

- [[bp-marginals]] — the m=1.0 limit, also bounded
- [[boundary-mps]] — vol-13 alternative cross-domain technique, also refuted

## Linked memory

- `project_e2_dead_ends`
- `reference_e2_bp_measurements`
