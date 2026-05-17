---
name: a5-bidirectional-design
description: "A5 = Bidirectional CSP: solve from corners-in (4 separate fronts) + from center-out simultaneously. Both meet at a 14-cell ring (perimeter of inner 8x8 in canonical 16x16). Designed 2026-05-17."
metadata:
  type: project
---

# A5 — Bidirectional CSP (design)

## Origin

INVENTIONS_BACKLOG.md A5 (unbuilt). After J1-hinted dead-end +
multiset-FLH refutation (vol-122 evening), the user directive is to
move to a completely different invention. A5 is genuinely novel:
all prior CSP/DLX/ALNS searches are unidirectional. Bidirectional
meet-in-the-middle could halve effective depth.

## Architecture

Canonical 16×16. Define:

- **OUTER**: rows {0, 1, 14, 15} ∪ cols {0, 1, 14, 15} = 4-rim ring.
  Contains 4 corners + 56 edge pieces + 60 interior pieces. Total
  cells: $16^2 - 12^2 = 112$.
- **INNER**: rows {2..13} × cols {2..13} = 12×12 = 144 cells. All
  interior pieces.
- **MEET-RING**: the boundary between OUTER and INNER. Specifically,
  the colored edges that cross from a (r, 1)-cell into a (r, 2)-cell
  (and analogous rim-to-inner crossings).

For the OUTER side, the boundary is the **inner edge of the OUTER**:
the right side of col 1 cells (for cols 1-2 crossing), the left side
of col 14 cells, the bottom side of row 1 cells, the top side of row 14
cells.

For the INNER side, the boundary is the OUTER edge of the INNER's
boundary cells.

These 4 "outer-inner edges" × 12 cells × 2 sides = ~48 edges define
the meet-ring's color constraints.

## Algorithm

```
Phase 1: solve OUTER independently.
  - 4 corners forced to fit.
  - 56 edges forced to fit on rim.
  - 52 interior pieces (4×13) wrapping the rim's INSIDE.
  - Hints at (2,2), (2,13), (8,7), (13,2), (13,13) are at INNER-edge
    so partially affect OUTER (if (8,7) and (13,2)/(13,13)? Actually
    (8,7) and (13,*) — let's check: r=2..13 is INNER per definition;
    so all 5 hints are INNER.)
  - Output: a set of OUTER configurations (call it {O_1, O_2, ...}).

Phase 2: For each O_i, the meet-ring boundary colors are determined.
  - Solve INNER given that boundary as 48 color constraints + 5 hints.
  - Output: complete board if INNER admits a satisfying assignment.

Phase 3: enumerate OUTER configs.
  - OUTER has 112 cells, ~4 corners freely assigned + 56 edges with
    rotation + 52 interior pieces. Combinatorial size HUGE.
  - But: many constraints (rim border + corner placement) reduce this.
```

## Tractability check

Vol-119 / A1 showed border-DP enumerates 60-cell rim configurations in
seconds (~50 piece-unique 60-borders).

A5's OUTER is 112 cells (60 rim + 52 inner-of-rim), which is much
larger. May need to enumerate the rim first (60 cells), then for each
rim, run CSP on the 52 inner-of-rim cells.

Size estimate:
- Rim: ~50 piece-unique configs (vol-122 A1).
- Inner-of-rim: 52 cells, ~196 interior pieces minus 5 hint-pieces = 191
  pieces. CSP backtracking on 52 cells likely fast given strong rim
  constraints.

For each (rim, inner-of-rim) pair, the meet-ring is fully colored. Then
INNER (144 cells, 5 hints) needs to be solved.

INNER is a SUB-PUZZLE of canonical E2: smaller but still has the same
piece-uniqueness, rotation freedom, color matching constraints.

## Key technical question

**Is INNER tractable as an independent sub-puzzle?**

INNER = 144 cells = 12×12 puzzle. Vol-14 measurements (testbed analysis):
- 12×12/12 in 90s CP+ALNS reaches 245-252/264 (92.8-95.5%, no full
  solutions in 90s).
- INNER on canonical 16×16 with extra constraints from the meet-ring
  is similar in size but has CONSTRAINTS (the 48 meet-ring colors fixed).

The constraints make INNER STRICTLY HARDER than a free 12×12, because
the boundary is over-determined. But with a "good" rim, the constraints
may FORCE the inner solution → very fast solve.

## Implementation plan

**Day 1 (today)**: Design + write meeting-ring spec.

**Day 2**: Build `outer_dp` bin — enumerate rim + inner-of-rim
configurations using forward DP.

**Day 3**: Build `inner_csp` bin — for each meet-ring boundary, run CSP
on the 144 interior cells with hints.

**Day 4**: Synchronization driver — for each outer config, attempt
inner solve; collect any complete boards.

**Day 5**: Scale + benchmark — measure how many outer configs per
second, how many lead to full inner solves, how many of those reach
≥460 matched.

## Smaller scope variant (1-2 days)

Instead of the full 4-rim, use **2-rim OUTER** (rows {0, 15} ∪ cols {0, 15})
= just the border. INNER = 14×14 = 196 cells.

This is closer to the standard "border-then-interior" but with a key
difference: solve the BORDER as a complete DP (vol-122 A1 has this)
and feed the boundary as constraints.

Actually, this IS exactly A1 with stronger constraint propagation.
Not novel.

## Going broader: TRUE bidirectional from CENTER outward

The full A5 idea: also grow a CENTER frontier outward. Frame:

- Outer frontier: solve concentric rings from rim inward. Levels 0
  (rim), 1 (next ring), 2, 3, ..., 7 (center 2×2).
- Center frontier: solve concentric rings from center outward.
  Levels 0 (center 2×2), 1, 2, ..., 6, 7 (rim).

Meeting at a meet-ring (typically level 3-4).

The center has NO border constraints — only color constraints with
neighbors. Center pieces are all INTERIOR pieces. Center growth is
freer than rim growth.

**Question**: can the center solver find ANY valid 2×2 sub-pattern
with high score? Each 2×2 has 4 inter-cell vertical + 4 horizontal = 4
internal edges. Max-matched: 4. Likely achievable.

Growing from center is symmetric to growing from rim but without
border constraints. The meet-ring is where they must agree.

## Status

`design-complete`. Implementation: phased over 5 days. Vol-122 may
only deliver day 1 + initial day 2.

## Linked

- [[../plans/INVENTIONS_BACKLOG]] (A5 entry)
- [[../concepts/inv3-border-dp-seed]] (A1, related)
- [[../sessions/vol-122]] (current vol)
