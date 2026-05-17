---
name: j1-hinted-v2-corner-color-bug
description: "J1-hinted v2 fails at band 14 NOT due to piece supply randomness but due to a STRUCTURAL constraint: row 14 corner-adjacent bottoms must match the unique color of the remaining row-15 corner pieces. v3 fix: reserve corner-color constraints upstream."
metadata:
  type: project
---

# J1-hinted v2 — Corner-color structural failure

## Discovery (2026-05-17 evening)

J1-hinted v2 reaches 240/256 placed (rows 0-14 filled) but band 14 (row 15)
"NO STATES" at col 0 (or col 15). Root cause is NOT random piece-supply
exhaustion; it is a STRUCTURAL constraint that J1 doesn't model.

(User caught a Python-parser bug in initial discovery — the canonical
loader confirms 4 distinct corners. Corrected analysis below uses Rust
loader output.)

## The constraint (corrected)

Canonical E2 has 4 DISTINCT corner pieces (via Rust loader):
- pid=0: edges (T,R,B,L) = (0, 0, 1, 3)
- pid=1: edges (T,R,B,L) = (0, 0, 1, 4)
- pid=2: edges (T,R,B,L) = (0, 0, 2, 3)
- pid=3: edges (T,R,B,L) = (0, 0, 3, 2)

When J1 places the top border (row 0), it uses 2 of the 4 corners (positions
(0,0) and (0,15)). The remaining 2 corners go to row 15 corners (15,0) and
(15,15).

But J1 has FREEDOM to choose WHICH 2 corners go to row 0 — and which to
leave for row 15.

If J1 picks pids 2 and 3 (both have bottom=2) for the row-15 corners,
then row 15 col 0 needs top color **2** (matching one of these corner's
top-side color in its rotated form).

That top color is the bottom edge of row 14 col 0 (= the vertical match
between row 14 and row 15 at col 0). The J1-hinted v2 board has this =
**1**. Mismatch: needed 2, got 1.

## Why J1's band 14 fails at col 0 (or col 15)

Beam search at band 14:
- Top constraint: row 14 was just placed at band 13 → fixed_top has row
  14 cells.
- Bot must satisfy: bottom=0 (border row), top=row14[c].bottom.
- For col 0: bot must also have left=0. Only corners with bot=0,left=0
  qualify, but they need top=row14[0].bottom = 1. **No remaining corner has
  top=1 when in BL orientation**.

## Fix (v3)

In J1's band 0 (top row), reserve which corners go to row 15 BEFORE
solving. Constraint: the 2 corners chosen for row 0 must be those whose
bottom-color matches what J1 can produce as row 1 top. Equivalently: the
2 corners reserved for row 15 must have a known "needed-top" color that
J1 can construct as row 14's bottom in band 13.

Simpler heuristic: **pre-commit the corner assignments to (0,0), (0,15),
(15,0), (15,15) in advance**. Run J1 with these 4 hint-like constraints
PLUS the 5 canonical hints. This is 9 forced cells.

Concrete commit choice:
- (0,0): pid 0 rot 0 (orig edges (0,0,1,2); rotated to (T=0, R=2, B=1, L=0)
  via rot 3 → wait that's rot 3 not 0). Let's just say "one of pids
  0/1/2/3 rotated to have T=L=0".
- (0,15): one of remaining 3 corners rotated to T=R=0.
- (15,0): one of remaining 2 corners rotated to B=L=0.
- (15,15): the last corner rotated to B=R=0.

The choice between pids {0,1} vs pids {2,3} for top vs bottom determines
which vertical constraints (corners' top color in BL/BR orientation)
must match row 14's bottom at cols 0 and 15.

Optimal assignment (combinatorially):
- Row 15 BL corner: pid 2 or 3, top=2.
- Row 15 BR corner: pid 2 or 3, top=2.
  (Both 2 and 3 have edges (0,0,2,2). In BL orientation, top=2 and right=2.
  In BR orientation, top=2 and left=2.)
- Row 0 TL/TR corners: pids 0, 1. In TL orientation: (T=0, R=2 or 3, B=2, L=0).
  In TR orientation: (T=0, R=0, B=1, L=2 or 3).

So:
- Row 14 col 0 bottom must be **2**.
- Row 14 col 15 bottom must be **2**.

For perfect band 14 row 15 verticals: also row 15 col 1 left must match
row 15 col 0 right = 2. And col 14 right must match col 15 left = 2.

## Implementation

Add a constructor in J1-hinted that PRE-PLACES corner pieces and runs
J1 with the 9-cell forced set. The corner-bottom-color constraint
(row 14 must have specific bottoms at cols 0, 15) is inherited through
band-by-band propagation since each band's bot row becomes next band's
top fixed row. As long as we reserve pids 2 and 3 from being used
elsewhere (already done in v2), and PRE-COMMIT row 15 corners as
fixed_bot in band 14, the constraint cascades.

## Cost prediction

- Cleaner band 14: should now succeed.
- Cost: some upstream J1 chains might fail to find row 14 bottoms with
  =2 at cols 0, 15. Beam might need to be larger.

## Deeper structural finding (after dump_free_pieces)

The 16 free pieces in J1-hinted v2 have origin top=0 (i.e., they're all
EDGE-FACING when rot=0). When rotated to put bottom=0 (for row 15),
their tops become the orig BOTTOM color.

The 16 free pieces' orig bottom colors:
{1=0, 2=1, 3=1, 6=3, 7=3, 8=1, 11=0, 13=1, 14=1, 15=1, 17=1, 18=2, 19=1, 20=1, 21=1, 22=1}

Row 15 needs tops (from row 14 bottoms):
{1=1, 4=1, 6=3, 7=3, 8=1, 11=1, 14=1, 16=2, 17=1, 18=1, 22=1}

Mismatch:
- needed but not supplied: color 4 (1 needed, 0 supplied), color 11 (1 needed,
  0 supplied), color 16 (2 needed, 0 supplied), color 1 (1 needed, 0 supplied).
- supplied but not needed: color 13, 15, 19, 20, 21 (all have 1 each).

**5 row-15 cells (cols 0, 1, 4, 6, 15) have ZERO feasible candidates.**
The mismatch is COMBINATORIAL, not local.

## Implication

J1-hinted v3 needs to constrain the chain such that the row 14 bottom
multiset is a SUBSET of the row-15 piece's top-color multiset (when those
pieces are rotated for bottom-border). This is a MULTISET-MATCHING
constraint that propagates back to band 13's piece-choice freedom.

This is exactly the SP/NS-1 deficit invariant ([[../concepts/ns1-deficit-invariant]])
applied at the row-14/15 interface.

## v3 fix sketch

For each band r (in reverse), pre-compute the multiset constraint of
needed-tops at row r+1 by analyzing the colors available for the FUTURE
row r+2 boundary. This is a backward-induction constraint that strict
top-down J1 doesn't capture.

Simpler heuristic v3: **add a band-N forward-look**: at each band r,
penalize states whose bottom-row color multiset doesn't match the
known/projected piece pool at row r+1.

## Status

`bug-discovered + deeper-multiset-matching-needed` → `v3-design-in-progress`.

## Linked

- [[j1-chain-hinted-v2-fix]]
- [[j1-hinted-v2-band-score-decomp]]
- [[j1-rust-beam100k-first-complete-board]]
