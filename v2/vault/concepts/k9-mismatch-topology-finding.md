---
name: k9-mismatch-topology-finding
description: "K9 = Mismatch graph topology. NEW observation: 458 records all have identical 2-component mismatch topology (17 mis, max comp = 25); 459 record has 4 small components (max 10). Suggests basin signature."
metadata:
  type: project
status: built
---

# K9 — Mismatch-graph topology (NEW finding)

## Origin

Per cross-domain directive (waves/lights/images), K8 FFT-on-colors was
refuted (all complete boards have low_frac ≈ 0.903). Refined approach:
instead of color-image FFT, analyze the MISMATCH GRAPH as a binary 2D
image.

## Method

For each board, compute the set of cells touching mismatched edges
(horizontal or vertical). Run 4-connected component analysis on this
cell set.

## Results

| Board | matched | #mismatches | #comps | max comp |
|---|---:|---:|---:|---:|
| Standing 459 (vol-60) | 459 | 11 | 4 | 10 |
| Vol-32 RECORD 458 (3 copies) | 458 | 17 | 2 | 25 |
| Vol-35 RECORD TIE 458 | 458 | 17 | 2 | 25 |
| Vol-35 RECORD TIE 457 | 457 | 14 | 5 | 8 |
| J1-hinted-v2 ALNS s7 | 445 | 26 | 10 | 15 |
| J1-hinted-v2 ALNS s42 | 444 | 26 | 7 | 13 |
| J1-FLH 447 | 447 | 24 | 5 | 13 |

## Key observations

1. **The 458 records are TOPOLOGICALLY IDENTICAL.** Three different 458
   boards have the SAME (17 mis, 2 comps, max=25) signature. Likely same
   basin retrieved by different runs OR a structural ceiling at 458.
2. **459 has FEWER LARGER components broken into pieces.** 459's max
   component (10) is much smaller than 458's (25). Implies 459 is
   *fragmentation* of 458 → smaller-cluster topology.
3. **J1 boards have MANY MEDIUM components.** 5-10 components, max
   13-22. The J1 family's topology is FRAGMENTED across the board.
   This is consistent with J1's loss-localization (all loss in V_8..14):
   8+ vertical mismatches distributed across 16 columns produce many
   small clusters.

## Hypothesis (testable)

**Two-component → one-component → zero-component** is the basin descent
that beats 459. If we have a 459 → 460 path, it requires UNIFYING the
4 small components into a single resolvable cluster.

Equivalently: **the 459 ceiling is the LARGEST number of EDGES where
clusters are still small enough to repair locally**. Beyond 459, the
mismatch geometry CONSOLIDATES into 1-2 big clusters that resist local
moves.

## Counter-prediction

If hypothesis is correct: any 459-board ALNS should attempt to
**merge the 4 small components into 1 big component** before trying
to reduce it. Standard ALNS targets the largest single component;
this approach actively MERGES first.

## Operational implication: cluster-merge ALNS

A new ALNS operator: at each iteration, pick TWO mismatch components,
destroy a "merge bridge" between them, then repair. The bridge =
shortest path between the two components.

If 459's 4 components are too far apart for natural ALNS moves, this
operator could traverse the score-saturation barrier.

## Status

`finding-documented`. Cluster-merge ALNS operator design pending.

## Linked

- [[k8-fft-signature-refuted]] (refined from)
- [[vol-122]] (today)
