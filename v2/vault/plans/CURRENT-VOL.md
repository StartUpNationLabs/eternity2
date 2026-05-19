# Current Volume — Vol-150

**Theme**: WEAVING — Two-Axis Consensus Construction. The second
constructive-from-scratch invention from the 6 named on 2026-05-19.

V149 STRATUM (all 3 variants) closed in 1 vol with the universal
lesson: pruners over already-placed state are vacuous in edge-strict
DFS. WEAVING avoids that trap entirely by operating on **completed
boards** (mismatches allowed) and **two coupled construction passes**.

## The invention in one paragraph

Run two independent constructive builders in parallel: ROW-greedy
(build row-by-row, each row maximizing horizontal edge matches) and
COL-greedy (build col-by-col, each column maximizing vertical edge
matches). Both share a piece-inventory abstraction. After both
complete, compute **per-cell tension** = 1 if the two boards
disagree about which piece goes at $(y, x)$, else 0. Iteratively swap
disagreed-on pieces between the two boards, accepting if both scores
stay above a threshold. The output is a single board where row-
evidence and col-evidence AGREE.

## Why genuinely different

- GRAIN (vol-135) is isotropic crystal growth: greedy attach with no
  axis preference. Single greedy path.
- ALNS basic / lkh: local search on a single board, no axis decomposition.
- DFS row-major: uses one axis (rows) implicitly, no consensus.
- WEAVING explicitly maintains two boards optimized for orthogonal
  axes + a consensus mechanism. **Cross-correlation between axes is
  the new signal** nobody has used.

## Binding items (3 max)

1. **Math + design** in [[../concepts/weaving-consensus]] including:
   - Definition of $B_R, B_C$ boards.
   - Tension metric.
   - Convergence criterion.
   - Falsifiable hypothesis: does WEAVING beat GRAIN (373/480) and
     edge-strict row-major DFS (~250-cell-depth at 60s) at equal
     wallclock?
2. **Python PoC** — write it Python first since we have GRAIN's helpers
   and don't yet know whether WEAVING is even tractable at 16×16.
3. **Measure** with variance reporting (5 seeds × 2 board sizes).

## Kill-criteria

- If row-greedy alone scores < 100/240 horizontal matches (or
  col-greedy similar), the individual builders are too weak; refute
  before integration.
- If after tension-swap iteration the merged board scores LESS than
  max(row-board, col-board), the consensus step destroys value.
- If WEAVING < GRAIN at canonical 16×16/22 across all seeds, refute.

## Days budget

Day 1: math + Python PoC of row-greedy + col-greedy individually.
Day 2: tension-swap iteration + measure.
Day 3: write up findings, possibly extend with Rust impl if Day-2
results are promising.

## Linked

- [[../sessions/vol-150]] (to create)
- [[../concepts/weaving-consensus]] (to create)
- [[../sessions/vol-149]] (universal-lesson source)
- [[INVENTION_NAMES_2026-05-19]]
- [[../concepts/grain-polycrystalline]] (V135 baseline)
