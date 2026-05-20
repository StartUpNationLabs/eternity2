---
name: vol122-rcbo-refuted
description: "Vol-122 K1 — Reverse Construction via Boundary-Out (center-out CSP). REFUTED. Across 5×5 through 8×8 puzzles, center-out is 10×–100× SLOWER than border-out, often failing to solve."
metadata:
  type: project
status: refuted
---

# Vol-122 K1 — RCBO refuted

## Refutation

- **Refuted**: vol-122 K1.
- **Evidence**: center-out CSP is 10×–100× SLOWER than border-out across 5×5 through 8×8 puzzles. 5×5/c3 center-out fails entirely (depth 22/25 after 2M nodes); 8×8/c5 center-out times out at 10× the border-out budget.
- **What's refuted**: the "Reverse Construction via Boundary-Out" hypothesis — that starting CSP from the center and building outward would benefit from initial rotation freedom. It doesn't — center cells have lower constraint propagation density; constraints accumulate too slowly to prune effectively.
- **What's NOT refuted**: hybrid strategies that combine center-anchoring with border-anchoring at specific intermediate sizes.

## Idea

Start CSP from puzzle CENTER (a 4×4 sub-grid of interior pieces), build
outward in concentric rings until reaching the border. Hypothesis:
center has more rotation freedom; the constraint accumulation as we
move outward toward the border would force locking, like LIFO basin-filling.

## Result

Tested on 5×5 through 8×8 puzzles with row-major, border-out, and
center-out scan orders. Center-out lost in EVERY case:

| Puzzle | row-major | border-out | center-out |
|---|---|---|---|
| 5×5/c3 | SOLVED 38k | SOLVED 2k | depth 22/25 (2M nodes, FAIL) |
| 5×5/c4 | SOLVED 11k | SOLVED 7k | SOLVED 432k (60× slower) |
| 6×6/c4 | SOLVED 39k | SOLVED 9k | depth 30/36 (FAIL) |
| 6×6/c5 | SOLVED 2k | SOLVED 27k | depth 28/36 (FAIL) |
| 7×7/c4 | depth 46/49 | SOLVED 15k | depth 24/49 (FAIL) |
| 8×8/c5 | depth 60/64 | depth 62/64 | depth 46/64 (worst) |

## Why it fails

Standard CSP benefits from PROPAGATION FROM CONSTRAINTS. The border
provides hard, immediate constraints (BORDER edges = color 0). Without
border anchoring, the center expands with arbitrary color choices and
no way to detect early infeasibility.

Center-out is the WORST scan order tested. The intuition that "interior
has more freedom" is correct but means LESS PROPAGATION, not faster
search.

## Implication

Confirms vol-14 lesson: **border-first MRV is the right scan order**.
Center-out is not a viable invention direction.

## Status

`refuted` (5+ data points across 5×5 through 8×8 sizes).

## Linked

- [[vol-122]]
- [[dead-ends]] (add this entry)
