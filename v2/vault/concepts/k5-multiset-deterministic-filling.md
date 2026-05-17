---
name: k5-multiset-deterministic-filling
description: "K5 = MDF: Multiset-Deterministic Filling. Given a partial board, for each unfilled cell compute its 4-color multiset constraint from filled neighbors. 192/196 interior pieces have UNIQUE multiset — many cells are forced to a single piece. Iteratively fill forced cells. Genuinely new propagator."
metadata:
  type: project
---

# K5 — Multiset-Deterministic Filling (MDF)

## Origin

After J1-hinted dead-ended (vol-122 evening pivot), color-class analysis
revealed a strong structural fact: 192 of 196 interior pieces of
canonical E2 have UNIQUE color multisets (sorted 4-edge tuples). Only
2 multiset-pairs exist among interior pieces.

## Key insight

If a board cell's 4 neighbors are all FILLED, the cell must accept a
piece whose 4-color multiset equals the (sorted) multiset of the 4
required colors. Since 192/196 interior multisets are SINGLETONS, the
cell is forced to a **unique piece** (up to rotation).

For cells with PARTIALLY filled neighbors: the known colors constrain
2 or 3 of the 4 positions in the multiset. The "remaining" colors are
free. But we can still enumerate piece-multiset classes whose known-color
subset matches.

## Algorithm

```
loop until no change:
    for each unfilled cell (r, c):
        known = colors required from filled neighbors
        candidates = pieces whose multiset is compatible with known
        if len(candidates) == 1:
            place that piece (try all rotations consistent with known)
            if a valid rotation exists: commit
    if any commits: continue loop
    else: break
```

Each iteration is $O(\text{cells} \cdot \text{pieces} \cdot |C|)$.
196 × 256 × 22 ≈ $10^6$ ops/iter. Fast.

## Comparison to MRV/AC3

MRV picks the cell with fewest valid pieces. MDF computes a different
constraint: the multiset of REQUIRED colors. MRV says "this cell has 1
piece"; MDF can ALSO say "this cell has multiple pieces but they all
share a unique multiset" → can sometimes commit when MRV doesn't.

Also: MDF works on COLOR MULTISETS, which is rotation-invariant for the
piece. So MDF can commit "piece X must go here" even if it can't yet
determine the rotation. Then later iterations refine.

## What MDF gives us that nothing else does

The 192-singleton structural fact has been DOCUMENTED (vol-65 multiset-twin
finding) but never USED as a propagator. Existing propagators (gacolor,
AC3, NS1, CFCC) work on edge-side compatibility or color-supply LP. MDF
works on PIECE-LEVEL MULTISET MATCHING — a DIFFERENT level of structure.

## What MDF cannot do

- For cells with all 4 neighbors UNFILLED, MDF gives no info (every
  piece-class is compatible).
- For cells with 3-of-4 unfilled, MDF narrows by 1 color but rarely
  uniquely determines.
- The 4 non-singleton classes (2 pairs of pieces) can't be MDF-resolved
  except via further propagation.

## Use case

MDF is most useful as a POST-PARTIAL-SEED PROPAGATOR. Given a J1-hinted
partial (240 cells) or any other partial, iteratively MDF-fill the
remaining interior cells. The constraint should be very tight given that
we have 240 placed neighbors.

For row 15 specifically: each row-15 cell has 3 filled neighbors (left,
right, above). Some have only 1 free color slot (the bottom border = 0).
This means the 4-color multiset is HIGHLY constrained.

## Empirical test

Use MDF on the J1-hinted v2 partial (240 cells). Apply MDF to fill row 15.

Expected: maybe 0-3 cells immediately forced; 13-16 cells still
under-constrained. If MDF reveals row 15 is over-constrained (no
candidates anywhere), we've identified a structural infeasibility.

## Status

`design-complete`. Implementation next.

## Linked

- [[j1-hinted-v2-corner-color-bug]] (motivation)
- [[../concepts/piece-set-symmetries]] (background)
- [[j1-backward-multiset-constraint]] (similar but at the chain level)
