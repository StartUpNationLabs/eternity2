---
tags: [umbrella, meta-concept]
status: built
covers: vol-122
---

# Umbrella — vol-122 experiments (19 sub-pages)

Vol-122 was the "user redirect to inventor mode" volume. Many distinct mini-experiments were
documented as their own concept pages. This umbrella lists them with one-line verdicts so
future work can locate findings without reading all 19.

## Status table

| Sub-concept | Verdict | One-liner |
|---|---|---|
| [[vol122-a1-pipeline-result]] | partial | A1 border-DP basin generation pipeline — reaches 433-439 on clean borders |
| [[vol122-random-path-sweep-result]] | refuted | Random scan order plateaus far below border-first MRV |
| [[vol122-pcls-poc-result]] | refuted | Supply-LP gives identical UB for good vs bad borders; no discriminator |
| [[inv-b4-hall-color-pair-refuted]] | refuted | Color-pair Hall condition LP = 480, same as vol-44 |
| [[dlx-e2-implementation-status]] | partial | XCC color-secondary semantics need re-implementation per Knuth Algorithm C |
| [[vol122-rcbo-refuted]] | refuted | Reverse Construction Boundary-Out: center-out CSP 10-100× slower than border-out |
| [[vol122-cfcc-color-flow-propagator]] | refuted-net | Python 2.47× prune; Rust marginal due to fast-Rust substitution effect |
| [[vol122-j3-spectral-discovery]] | confirmatory | Laplacian Fiedler vector EXACTLY recovers border/interior partition (60/196) |
| [[vol122-hffm-forced-pieces]] | structural | 92/256 pieces uniquely provide some adjacency color-pair |
| [[vol122-25-edge-gap-is-all-interior]] | finding | Decomposition of McGavin 469 vs perm0 444 mismatch gap |
| [[vol122-sigma-perm0-444-to-mcgavin-indecomposable]] | finding | σ-cycle indecomposability confirmed on perm0 444 → McGavin 469 |
| [[vol122-pair-supply-discriminator]] | refuted | Pair-supply not a basin discriminator |
| [[vol122-fsmc-convergence-measured]] | partial | Python FSMC PoC: 17-94% convergence on 3×3–7×7 |
| [[vol122-fsmc-rust-scaling-wall]] | refuted | Rust FSMC: 0% hit rate on canonical 16×16/22c |
| [[vol122-bf-bw-alns-pipeline-452]] | partial | bf_bw → ALNS pipeline reaches 452 on this run |
| [[vol122-border-structure-analysis]] | structural | Border piece-positioning structural analysis |
| [[vol122-mcgavin-border-our-stack-435]] | finding | Our stack on McGavin's border configuration reaches 435 |
| [[vol122-prune-restart-bf-bw-partial]] | partial | prune-restart on bf_bw partial run |
| [[vol122-three-basin-structural-overlap]] | structural | Three basins compared structurally; overlap regions identified |
| [[vol122-alns-multi-seed-results]] | data | ALNS multi-seed results table |
| [[vol122-k8-interior-mip-intactable]] | refuted | K=8 interior MIP at canonical scale intractable |

## Top-level findings (the durable ones)

- **K11 basin signatures** (λ_2 + mz) → separate concept [[k11-basin-signatures]].
- **FSMC + CFCC together multiply on small puzzles, fail at canonical** — represents an active research direction that hit a scaling wall.
- **J3 spectral confirms binary frame/interior partition** — useful as a sanity check, no new heuristic.

## Standing record produced this vol

- Vol-122 strict-canonical 458 (NEW STRICT RECORD) — see [[E2_KNOWN_FACTS]].

## Linked

- [[vol-122]]
- [[vol-123]]
- [[PAPER_2026-05-17_vol122_basin_diversity_and_rigidity]]
