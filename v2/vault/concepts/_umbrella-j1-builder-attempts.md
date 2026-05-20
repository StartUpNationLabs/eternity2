---
tags: [umbrella, meta-concept]
status: built
covers: J1 pipeline variant
---

# Umbrella — J1 builder attempts (18 sub-pages)

J1 was a pipeline variant tested across many sub-experiments. Each sub-experiment was documented
as its own concept page, leading to a 18-page cluster. This umbrella lists them with one-line
verdicts.

## What J1 is

J1 = a chain-hinted band-decomposition builder. Builds in vertical bands with the prior band's
S-edges as the next band's N-edge target.

## Status table

| Sub-concept | Verdict | One-liner |
|---|---|---|
| [[j1-poc-perfect-band-results]] | partial | PoC reaches perfect band scores in isolation |
| [[j1-chain-band-decomposition-math]] | structural | Math of chain-band decomposition formalized |
| [[j1-rust-beam100k-first-complete-board]] | partial | First complete board from Rust beam K=100k |
| [[j1-band-14-failure-analysis]] | refuted | Band 14 fails systematically |
| [[j1-chain-hinted-band-12-failure]] | refuted | Chain-hinted variant fails at band 12 |
| [[j1-chain-hinted-v2-fix]] | partial | v2 fix for chain-hinted band 12 |
| [[j1-hinted-v2-band-score-decomp]] | structural | Per-band score decomposition |
| [[j1-hinted-v2-corner-color-bug]] | bug-fix | Corner color bug found and fixed |
| [[j1-stratum-fix-result]] | partial | Stratum fix result |
| [[j1-stratum-fix-repair-theorem]] | finding | Repair theorem for stratum fix |
| [[j1-fragment-anchor-design]] | unbuilt | Fragment-anchor design sketch |
| [[j1-multi-band-beam-search]] | partial | Multi-band beam variant |
| [[j1-loss-localization-math]] | structural | Localization math for J1 loss |
| [[j1-forward-look-heuristic]] | partial | Forward-look heuristic variant |
| [[j1-backward-multiset-constraint]] | partial | Backward multiset constraint variant |
| [[j1-center-sweep-failure]] | refuted | Center-sweep variant fails |
| [[j1-bidirectional-symmetric-failure]] | refuted | Symmetric bidirectional variant fails |
| [[j1-column-dp-design]] | unbuilt | Column-DP design (not built) |

## Overall verdict

J1 is **bounded** at the band-12/14 wall. It could not break 459. The math is good (chain-band
decomposition is a clean reformulation), but the implementation hits the same structural walls
as other row/band-based builders.

The successor pipeline that opened ≥460 from scratch is **V155 PRIOR + V181 KEYRING**, which uses
beam-search with corpus-prior signals rather than band decomposition.

## Linked

- [[prior-data-augmented-beam]] (the successor approach)
- [[keyring-patch-prior]] (the production builder)
- [[TIMELINE]] vol-? where J1 was developed (see git log on j1-* files for dates)
