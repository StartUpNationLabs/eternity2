---
name: chiasmus-basin-crossover
description: Naming: CHIASMUS — Greek χιασμός, the crossing of fibers in DNA recombination. Reserved name; invention credit.
status: partial
metadata:
  type: concept
---
# Chiasmus — Basin Crossover via Row/Column Interleave (V172)

Status: `partial` (PoC measured 2026-05-20)
Origin: vol-172 (planned next)
Files: `scripts/v172_chiasmus/probe.py`.
Naming: **CHIASMUS** — Greek χιασμός, the crossing of fibers in DNA recombination. Reserved name; invention credit.

## Idea

Given two completed (or near-completed) boards $B_A, B_B$ in different basins, build a hybrid by interleaving rows:

$$
B_H[y, x] := \begin{cases} B_A[y, x] & \text{if } y \in \mathcal{R}_A \\ B_B[y, x] & \text{if } y \in \mathcal{R}_B \end{cases}
$$

where $\mathcal{R}_A, \mathcal{R}_B$ partition $\{0, \ldots, 15\}$.

**Piece conflicts.** A piece $p$ used in both $\mathcal{R}_A$-rows of $B_A$ and $\mathcal{R}_B$-rows of $B_B$ causes a conflict. Resolve by leaving the cell empty in the hybrid; ALNS-repair fills it.

**Hybrid as ALNS init.** The hybrid is partial (placed $\le 256$). ALNS-fill with corpus-pinned-cells gives a board in a "between-A-and-B" basin.

## PoC measurements

### Same-family pair (our two V155→ALNS 460s)

cp(A) = (0,3,2,1), cp(B) = (0,3,1,2). Hamming-pid distance ≈ 226 (vol-156 measured).

| Scheme | placed | conflicts | matched |
|---|---|---|---|
| rowAB (alt) | 243/256 | 13 | 406/480 |
| top8A | 256/256 | **0** | **460/480** |
| border4A | 256/256 | **0** | **460/480** |

Half-and-half schemes (top8, border4) produce a *valid 256-placement* with 0 conflicts and matched = 460. Meaning: the two 460 basins are essentially compatible across their halves — the piece sets in each row-band are nearly disjoint.

### Cross-basin pair (V155 460 + McGavin 469)

cp(A) = (0,3,2,1), cp(B) = (3,2,0,1). Vastly different basins.

| Scheme | placed | conflicts | matched |
|---|---|---|---|
| rowAB | 194/256 | 62 | 159/480 |
| top8A | 187/256 | 69 | 284/480 |
| border4A | 195/256 | 61 | 270/480 |

The hybrids have ~60 empty cells (piece-set overlap between basins is large). Matched score is 270-284 in 187-195 cells. The matched DENSITY is comparable to A's interior — i.e., the parts that came from each parent are intact; the breakdown happens at the boundary between the two basins.

## Strategy

Stage 1: collect $N$ candidate 460-tier boards across $K$ distinct corner-perms (via V171 MURMURATION).

Stage 2: for each (i, j) pair with i < j and cp(i) ≠ cp(j):
  - generate all 6 hybrid schemes (rowAB, top8A, border4A, etc.).
  - ALNS-fill each hybrid with `basic_lkh + prior-escape` ops, 5-30 min.
  - score the result; if > max(score_i, score_j), record as a cross-basin lift.

Stage 3: build a "basin proximity graph" — nodes are basins; edges weighted by best cross-basin hybrid score. Use the graph to identify basins that act as bridges between high-score regions.

## Math

If basins A and B are σ-equivalent (vol-65 result), then any chiasmus is equivalent to permuting A within its own orbit; no new geography. If A and B are σ-DIFFERENT (vols 122/129 found 18 distinct cp's), the chiasmus enters a genuinely new region of the search space.

The cross-basin hybrid is *not* in either parent's basin — it's in a third basin whose score depends on:
1. piece-set overlap (more overlap → more conflicts → smaller filled fraction).
2. compatibility of A's top with B's bottom at the row 7-8 interface.

Both factors are basin-dependent. Pairs (A, B) where (1) is moderate and (2) is high are the prime candidates for breakthrough.

## What's still open

- Run the cross-basin sweep after V171 produces a 460-basin atlas.
- Compute piece-set Jaccard distance per (band, basin) pair — predict good chiasmus pairs.
- Diagonal interleaves, not just row-bands.
- 2D quilting: take 4×4 patches from A vs B by a checkerboard pattern.

## Linked

- [[vol-172]]
- [[murmuration-basin-sampling]] (V171 provides the basin diversity input)
- [[prior-guided-alns]] (V169 used as the lift stage)
