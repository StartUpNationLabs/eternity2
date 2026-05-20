---
name: concentric-annular-solving
description: known E2 literature. Named today.
status: unbuilt
metadata:
  type: concept
---
# Concentric Annular Solving (CAS) — vol-74 design

**Status**: `design` — vol-74 (2026-05-15).
**Type**: NEW INVENTED ALGORITHM per user directive. Not in any
known E2 literature. Named today.
**Inventor**: this autonomous run.

## The name

**Concentric Annular Solving** (CAS) — solves the puzzle in
concentric layers from outside in. Each layer is an ANNULUS
(ring of cells at a fixed shell-distance from the frame).

## Why this is new

Standard E2 algorithms:
- ALNS: destroy + repair small regions
- CP: depth-first piece-by-piece in some scan order
- PT: parallel-tempering across replicas
- Blackwood: scheduled break-index allowance

NONE solve as concentric annuli. The closest related idea:
border-first scan order (visit frame first, then inward) — but
that's still depth-first piece-by-piece, not solving the ENTIRE
annulus as one MIP.

## Layer decomposition

Canonical 16×16 board has 8 concentric shells:

| shell | cells | piece kind |
|---|---|---|
| 0 (frame) | 60 | 4 corners + 56 edges |
| 1 | 52 | interior, frame-adjacent |
| 2 | 44 | interior |
| 3 | 36 | interior |
| 4 | 28 | interior |
| 5 | 20 | interior |
| 6 | 12 | interior |
| 7 (center 2×2) | 4 | interior |

Total: 60+52+44+36+28+20+12+4 = 256 ✓.

## The algorithm

```
def CAS():
    # Solve shell 0 (frame): MIP with corners at corners, edges at edges.
    shell_0 = solve_frame_mip()  # 60 cells, ~10 sec

    # For shell 1 onwards:
    placement = shell_0
    for shell in range(1, 8):
        annulus_cells = cells_at_shell(shell)
        # MIP: place interior pieces at annulus_cells, with:
        # - Outer-side color must match: piece at cell (r, c) has its
        #   "outward" side equal to neighbor's "inward" side from shell-1.
        # - Inner-side color: free (will be constrained by shell+1).
        # - Use any UNUSED interior piece.
        # - Maximize matched edges within the annulus AND from annulus
        #   to shell-1.
        annulus_placement = solve_annulus_mip(shell, annulus_cells, placement)
        placement.update(annulus_placement)

    return placement
```

## Why this might work

1. **Each MIP is smaller**. Shell 0 = 60 cells (manageable).
   Shell 1 = 52 cells (manageable).
2. **Annular ordering exploits the frame** as a strong constraint
   on shell 1, which then constrains shell 2, etc.
3. **MIP solves each annulus to optimum** locally, accumulating
   optimal-per-annulus structure.
4. **Frame's color profile is fixed** (border pieces have
   border-color sides facing outward). This propagates inward,
   giving each annulus a tight outward-color constraint.

## Why this might NOT work

- **Greedy-annular ≠ global optimum**. Optimal shell-0 may not
  extend to optimal shell-1. Local annular optimality doesn't
  compose.
- **MIP at shell 0 (60 cells with 60 pieces, ~60 binary x's per
  cell × 60 cells = 3600 vars, plus edge matches) might still be
  slow**. HiGHS could take minutes.
- **Piece-uniqueness across annuli**: each shell uses pieces
  consumed by previous. The MIP at shell k must pick from
  remaining 256 - (already-placed) pieces.

## Variant: CAS-BACKTRACK

If a shell fails (no valid completion), backtrack to previous
shell and try a different solution. This makes CAS a tree search
with annular nodes, not greedy.

## Build plan

### Day 1
- Write `vol74_cas_frame.py`: solve shell 0 alone via MIP.
  - Variables: x[piece, cell, rotation] for corner pieces at
    corner cells + edge pieces at edge cells.
  - Constraints: piece-uniqueness, cell-coverage, frame-respect,
    edge-color-matching between adjacent frame cells.
  - Objective: maximize matched edges (within shell 0).
- Run; get a frame placement.
- Score the frame matched edges (out of 60).

### Day 2
- Extend to shell 1: same MIP with shell-0 fixed as constraints.

### Day 3
- Iterate through all 8 shells.
- Compare final score to standard ALNS pipeline.

## Expected behavior

- Shell 0 MIP gives ~60/60 matched (frame is fully solvable —
  60 border-edge matches between 60 cells with 60 specific pieces).
- Shell 1 MIP gives close to 52/52 internal matches + 52/52
  matches to shell 0 = 104/104. Maybe minus a few from piece-supply
  conflict.
- Shells 2-7: progressively harder; some annuli may yield only
  partial matches.

Predicted final: 440-460 (similar to ALNS). If higher (469+),
CAS bears fruit. If lower (≤ 440), CAS adds nothing.

## Linked

- [[piece-side-matching]] (parent — uses similar piece-side analysis)
- [[vol-74]] (TBD)
- vol-62: cluster_repair MIP infrastructure (reusable)
