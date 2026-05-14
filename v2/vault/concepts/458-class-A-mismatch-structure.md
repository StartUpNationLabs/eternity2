# Class-A 458 board: mismatch anatomy (vol-44)

**Status**: measurement.
**Origin**: vol-44 LP UB sweep identified class-A; `board_anatomy` and
`mismatch_map` ran on vol-32 RECORD_BREAK_458_vanilla_fast_alns.json.

## Match anatomy

The 458 board scored on the 480 internal adjacencies as:

| Edge type | Matched / Total | Mismatched |
|---|---|---:|
| B-B (border ring) | 60 / 60 | **0** |
| B-I (border→interior) | 52 / 56 | 4 |
| I-I (interior→interior) | 346 / 364 | 18 |
| **Total** | **458 / 480** | **22** |

LP UB on this border = 478. Integer gap = 20 = (mismatched − LP-mismatched-LB).

## I-I mismatch spatial structure (class A 458 board)

The 18 I-I mismatched edges induce **10 disjoint connected components**
when interpreted as a graph on the cells touching them. Max component
size = 5 cells. **All mismatched cells lie in rows 10-14**:

| Cluster | Size | Cells (x,y) |
|---|---:|---|
| C0 | 5 | (6,12), (7,12), (8,12), (7,13), (8,13) |
| C1 | 5 | (3,10), (3,11), (3,12), (4,12), (5,12) |
| C2 | 3 | (1,13), (2,13), (3,13) |
| C3 | 3 | (9,13), (10,13), (11,13) |
| C4 | 2 | (5,14), (6,14) |
| C5 | 2 | (13,13), (14,13) |
| C6 | 2 | (4,13), (4,14) |
| C7 | 2 | (11,14), (12,14) |
| C8 | 2 | (9,14), (10,14) |
| C9 | 2 | (2,11), (2,12) |

**Total**: 28 distinct cells in clusters. Average cluster size = 2.8.

## Why this matters

1. **The top 9 interior rows (y ∈ 1..9) are PERFECT.** Zero I-I
   mismatches above y=10. Rows 1-9 also have no B-I issues
   (B-I mismatches are at cells (1,1) and (1,15) — also in the bottom
   band). **The "hard region" is purely the bottom 5 interior rows.**

2. **Cluster sizes are small.** Max 5 cells. Average 2.8. This means
   ALNS with destroy-and-rebuild of `K = 5..8` cells can in principle
   address each cluster *individually*, not globally.

3. **10 disjoint clusters = 10 INDEPENDENT subproblems** (with the
   caveat that swapping pieces between clusters would couple them via
   piece-uniqueness constraints).

## Math: per-cluster solvability

Take cluster C0 = {(6,12), (7,12), (8,12), (7,13), (8,13)}. Its
internal I-I edges touched: ((6,12)—(7,12)) wait — let me re-check.

Actually the mismatch_map's edges for C0 were:
- 198=(6,12) — 199=(7,12)
- 199=(7,12) — 215=(7,13)
- 200=(8,12) — 216=(8,13)
- 215=(7,13) — 216=(8,13)

So C0's internal mismatched edges form this subgraph:
```
(6,12) — (7,12) — (8,12)
         |        |
         (7,13) — (8,13)
```

There are 4 mismatched edges in C0. Fixing C0 means re-placing the 5
cells with 5 NEW (piece, rotation) choices such that all 4 mismatched
edges become matched.

**Constraint on the swap**: the new placements must preserve:
1. Piece-uniqueness (pieces taken from the unused pool only, or via
   ripple-swap that re-uses).
2. Compatibility with all *external* boundary edges of C0 (the edges
   from C0 cells to non-C0 cells, which are currently matched and we
   want to keep matched).

For each cluster `K`, let:
- $E_{\text{in}}(K)$ = mismatched edges inside K (those we want to fix)
- $E_{\text{bdy}}(K)$ = boundary edges of K to outside (which must
  stay matched)

The cluster repair problem is: find a piece-rotation assignment to
cells in K (from the unused-piece pool, augmented possibly with
ripple-swaps) such that $|E_{\text{in}}(K)|$ matches improve and
$|E_{\text{bdy}}(K)|$ matches don't degrade.

## Conjecture (vol-44)

The 10 clusters are independent enough that **fixing them sequentially
with cluster-bounded MIPs or SAT instances** could push 458 → 462+
on the same border. Each cluster's MIP has size ~5 cells × 191 pieces
× 4 rotations = ~4000 binary vars — very tractable.

**This is the next experiment.** Build a cluster-repair tool that
solves the per-cluster MIP exactly.

## Linked

- [[vol-44]] — session
- [[scan-order]] — bottom band is reached late in row-major scan,
  consistent with vol-14 "shoulder region" finding
- [[border-enum-lp-ub]] — the LP framework
