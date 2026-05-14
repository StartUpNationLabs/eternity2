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

## Cluster-repair MIP result (option a — exhausted)

Tool: `crates/bench-audit/src/bin/cluster_repair_458.rs`, run 1 on
2026-05-14. Per-cluster MIP, permuting only the existing 2-5 pieces
in each cluster (with rotation choice), preserving boundary matches.

**All 10 clusters returned `delta = 0`.** Solve time per cluster
< 0.01 s.

**Interpretation**: For each cluster K with its current piece-set,
the MIP confirms there is NO permutation+rotation of those pieces
that increases the within-cluster matched edges while preserving the
boundary edges. The 458 board's within-cluster placements are
**already locally optimal** under piece-permutation moves.

**Conclusion (proved):** the 458 → 462+ jump cannot be made by
within-cluster moves alone. Cross-cluster piece swaps or external-pool
swaps (the unused pieces are in cells outside K but inside the
board) are required.

## Cluster-repair MIP (option b — halo enlargement)

Approach: for each cluster K, enlarge to region R = K ∪ (cells within
Manhattan distance ≤ d). Apply the same MIP (permute pieces in R,
maximise matches in R's internal+boundary). All pieces currently in R
are candidates.

| halo radius d | typical region size | C9 region size | total time | total delta |
|---:|---:|---:|---:|---:|
| 0 (option a) | 2-5 | 2 | 0.1 s | 0 |
| 1 | 6-8 | 8 | 0.3 s | 0 |
| 2 | 12-16 | 16 | 2 s | 0 |
| 3 | (in progress) | ~30 | (running) | (?) |

**Provisional result (halo ≤ 2):** the 458 board is locally optimal
under **radius-2 (16-cell)** MIP-exact local search around each
mismatch cluster. This is **strictly stronger** than vol-22's K=5
operator-lock (vol-22 proved local optimality under all moves of
cardinality ≤ 5; we've now proved it for region-sizes up to 16).

The MIP gives an EXACT optimum within each region. The board cannot
be improved by any rearrangement of ≤16 pieces in proximity to any
one mismatch cluster.

**Mathematical statement** (formal):

> Let $B^*$ be the vol-32 458 board. Let $K_1, \ldots, K_{10}$ be the
> 10 I-I mismatch clusters. For each $K_i$ and each $d \in \{0, 1, 2\}$,
> let $R_i^d = K_i \cup \{c : \text{dist}_M(c, K_i) \le d\}$. Then for
> every piece-permutation $\pi$ and rotation function $r$ on $R_i^d$
> consistent with the pieces currently in $R_i^d$, the score
> $\text{score}(\pi(B^*|_{R_i^d}), r)$ does NOT exceed
> $\text{score}(B^*|_{R_i^d})$.

The MIP enumeration shows this with mathematical certainty (within the
HiGHS B&B's correctness). The 458 board's local structure around each
mismatch is tight.

## What this leaves open

1. **Larger radius** (halo ≥ 3): could find improvement; running now.
2. **Cross-cluster moves**: any non-local move that touches two clusters
   simultaneously. Not addressed by halo expansion of individual clusters.
3. **Border swap**: rearranging the 60 perimeter pieces. Not addressed.
4. **Hint relaxation**: the 5 canonical hints are fixed. If we treat
   the puzzle as 0-hint or 1-hint, we'd be on a different variant.

## Cross-cluster MIP — UNION of all 10 mismatch clusters

Tool: `repair_region --all-mismatch-clusters`, run 2026-05-14.
Region = union of all 28 cells touching any I-I mismatch.
**MIP solved to optimality in 1.74 s. delta = 0.**

**This proves**: the 458 board's bottom-band 28 cells are at the
**integer optimum** under any rearrangement of just those 28 pieces
(boundary edges to the perfect top 9 rows held fixed).

To improve 458 further, we MUST:
- Bring pieces from OUTSIDE the bottom-band (rows 0-9) INTO the
  bottom-band (rows 10-14), OR
- Modify the perimeter, OR
- Modify the canonical hints (forbidden by puzzle).

Effectively, **the 458 board's top region (rows 0-9) is committed
to a specific piece-set, and that commitment is what limits the
bottom region**.

## Mathematical statement (strong form)

> Let $B^*$ = vol-32 458 board, $R$ = the 28 cells touching any I-I
> mismatch, $\Pi_R$ = pieces currently at $R$. For every assignment
> $\sigma: R \to \Pi_R$ (bijection) and every rotation function
> $\rho: R \to \{R_0, R_1, R_2, R_3\}$:
>
> $$\text{score}(B^* | \sigma, \rho) \le \text{score}(B^*) = 458$$
>
> The bound is achieved by the current placement.

The MIP proves this exactly via HiGHS B&B.

## Where the slack actually lives

LP UB = 478. Integer at R-permutation optimum = 458. The 20-point
gap consists of:
- (a) LP relaxation slack — the fractional vars in the LP that don't
  correspond to integer solutions.
- (b) Piece-uniqueness commitment — the rest-of-board (rows 0-9 plus
  perimeter) fixes which 28 pieces are available for the bottom band,
  and that 28-piece set has score-458 ceiling on this border.

Item (b) is the real constraint. To break it, we need cross-region
swaps (move a piece from row 0-9 to row 10-14, displacing another
piece, with the ripple maintained globally).

## Next experiment: cross-region MIP

Take a larger region $R^+ = R \cup \{\text{rows 6-14}\}$ for
example — a 14×9 = 126 cell rectangle covering the bottom 9 rows.
MIP would be ~126 × 126 × 4 ≈ 63 000 binary x-vars. Might or might
not be tractable for HiGHS. Worth trying with 10-min budget.

## Linked

- [[vol-44]] — session
- [[scan-order]] — bottom band is reached late in row-major scan,
  consistent with vol-14 "shoulder region" finding
- [[border-enum-lp-ub]] — the LP framework
