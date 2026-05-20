---
tags: [umbrella, meta-concept, mip]
status: built
covers: McGavin 469 MIP rigidity work (vols 65–101)
---

# Umbrella — McGavin 469 MIP rigidity proofs (18 sub-pages)

The McGavin 469 basin was the most exhaustively probed in the Local Rigidity Theorem work
(vols 65–101). 18 concept pages documented different cuts of the proof. This umbrella indexes
them so future readers can find any specific cut without searching.

## What the cluster proves

McGavin's 469 basin is **locally MIP-rigid at radius up to halo-4** (proven for one component;
halo-2 and halo-3 proven across the full board). No piece-permutation + rotation within any
tested local region can increase the score from 469. Mismatches concentrate in TOP rows.

## Status table

| Sub-concept | Result |
|---|---|
| [[mcgavin-engine]] | 295 M nps target throughput (Bucas's C engine) |
| [[mcgavin-blackwood-gap-analysis]] | 4 orthogonal gaps between our stack and Blackwood's |
| [[mcgavin-basin-rigidity]] | umbrella claim of basin rigidity |
| [[mcgavin-mip-local-optimal-halo1]] | halo-1 joint MIP: 37 cells, 895s, Δ = +0 PROVEN |
| [[mcgavin-joint-halo2-mip-result]] | halo-2 joint MIP |
| [[mcgavin-halo2-percomp-proven]] | halo-2 per-component: 2 components (8, 8 cells), both +0 |
| [[mcgavin-halo3-percomp-proven]] | halo-3 per-component: 42+47 cells, +0 PROVEN (929s total) |
| [[mcgavin-halo4-comp0-proven]] | halo-4 component 0: 57 cells, +0 PROVEN (1200s) |
| [[mcgavin-top3-mip-locked]] | top-3 rows: 48 cells, +0 PROVEN (70s, gap 0%) |
| [[mcgavin-top3-mip-proven]] | duplicate of above (consolidation candidate) |
| [[mcgavin-top4-mip-bounded]] | top-4 rows: 64 cells, MIP dual bound = 123 (first sound subset-UB) |
| [[mcgavin-top5-mip-inconclusive]] | top-5 rows: didn't converge in tractable time |
| [[mcgavin-basin-top-bottom-symmetry]] | top-N=14 → 469, bottom-N pins → 443-462 (asymmetric) |
| [[mcgavin-469-bottom-row-optimal]] | bottom row is optimal in this basin |
| [[mcgavin-469-mismatch-geometry]] | 11 mismatches concentrate in rows 0-4 |
| [[mcgavin-469-near-twin-orbit]] | exactly 2 boards in 469 orbit (McGavin + near-twin) |
| [[mcgavin-n-row-scaling]] | sharp threshold at N=14 rows pinned |
| [[mcgavin-alns-basic-locked]] | ALNS basic 30min × multiple seeds: locked at 469 |

## Consolidation candidate

`mcgavin-top3-mip-locked` and `mcgavin-top3-mip-proven` describe the same result. Future work
could merge them; for now both stand under the no-quiet-deletes rule.

## Linked

- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — the formal paper
- [[basin-mcgavin-469]] — basin page
- [[three-basin-iso-plateau]] — the strongest current statement
- [[sigma-cycle-universal-indecomposable]] — the cross-basin obstruction
