---
name: vanilla-path-pin-hints-depth-wall
description: "Vol-121 T1a — vanilla_path with --pin-hints + border-first path has a CSP DEPTH WALL at ~86. 30min × 8-thread × ~938G placements stays at depth 86. The cross-machine 459 SOTA recipe must NOT have used --pin-hints (459 record only obeys 4/5 hints anyway)."
metadata:
  type: project
---

# vanilla_path --pin-hints depth wall (vol-121 T1a)

## Measurement

Configuration: `vanilla_path --path-mode border-first --pin-hints
--threads 8 --thread-id-offset 0 --budget-ms 1800000`.

Result: max_depth = 86 across all 8 threads after 938 billion
placements (521M pp/s aggregate). All 30 minutes spent backtracking
within depth ≤ 86.

The depth wall is structural: with hints forced + border-first path,
the CSP can't extend past depth 86 even at SOTA throughput.

## Why

Hint pinning forces specific (piece, rotation) at 5 positions.
Border-first path traverses the perimeter (cells 0-59) first.
By depth 60, border is full. By depth 86, ~26 interior cells are
placed and the CSP has wedged into an infeasible region.

The remaining ~170 interior cells can't be filled without violating
piece-uniqueness or color-matching given the hint anchors + border
already placed.

## Implication

The cross-machine SOTA "vanilla_path border-first × 9 threads × 30min
→ 403 partial" must have used a DIFFERENT configuration. Either:
- NO --pin-hints (allows freedom in hint cells → 4/5 obeying basins).
- DIFFERENT path mode (e.g., not strict border-first).
- DIFFERENT puzzle (vol-110 1-clue variant?).

Vol-121 T1b drops --pin-hints to test.

## Linked

- [[blackwood-layered-depth-wall]] (similar structural wall)
- [[../sessions/vol-121]]
