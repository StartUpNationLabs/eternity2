---
name: basin-component-landscape
description: Cluster 135 unique 455+ records by σ-distance (= cells with different
status: built
metadata:
  type: concept
---
# Basin-component landscape of canonical E2 records — vol-65 day 4

**Status**: `built` — vol-65 (2026-05-15).
**Origin**: post-hoc analysis of 135 unique 455+ records in `output/`.

## Method

Cluster 135 unique 455+ records by σ-distance (= cells with different
piece-position). Connect any two records at Hamming < 100; compute
union-find components.

## Results

**47 distinct basin-components** at 455+:

| component size | count | example max score |
|---|---|---|
| singleton (size 1) | 18 | McGavin 469, 456-459 various |
| size 2 | 11 | local 459 + 1 cousin |
| size 3 | 5 | 456-457 small families |
| size 4-6 | 9 | 457-458 families |
| size 8 | 1 | 457 family |
| size 11 | 1 | 457 family (max) |
| size 22 | 1 | 458 family (max) |

**Key fact**: **McGavin 469 is a SINGLETON component**.

## McGavin's isolation

Min Hamming distance from McGavin to any other unique 455+ record =
247. The 9 closest non-McGavin records:

| Hamming | score | file (last 50 chars) |
|---|---|---|
| 247 | 455 | winning5_sa_t1_s4_1778765217_488312000_p73617.json |
| 248 | 455 | winning5_sa_t1_s1_1778757069_986256000_p98134.json |
| 248 | 455 | winning5_sa_t1_s1_1778757070_86636000_p98206.json |
| 248 | 455 | winning5_sa_t1_s2_1778765217_464785000_p73606.json |
| 248 | 455 | winning5_sa_t1_s4_1778748361_954377000_p17985.json |
| 248 | 456 | v17_alns_only/winning5_sa_t1_s101_*.json |
| 248 | 457 | v17_alns_only/winning5_sa_t1_s1_1778743785.json |
| 248 | 458 | stage3_seed200.json |
| 249 | 455 | full_sa_t1_s4_1778757937_655322000_p6812.json |
| 249 | 455 | result_p19_seed4.json |

## Local-459 basin

Size 2: local-459 + 1 cousin at Hamming 52 (score 456).
This is our highest-score basin and has only 1 sibling.

Vol-32 458 sits in a different size-2 component.
Vol-61 458 sister-basin pair (s17 + s200) sits in a 6-board cluster
of 455-458 records — our most-explored 458 family.

## Implications

1. **Our search produces highly disjoint basins**: 47 components, many
   singletons. ALNS doesn't broadly explore the basin landscape; it
   converges to one of many disjoint attractors.

2. **McGavin's basin requires a transition of ≥ 247 cells**.
   This is ~10× larger than our largest destroy operator (k=64 in
   MegaBand). Standard ALNS cannot bridge.

3. **Sister-basins are rare**: most components are singletons or
   size-2. ALNS produces few near-duplicates of the same basin.

## Vol-66+ algorithmic targets

- **Cross-component crossover** (BLGS): take regions from different
  basin components, hope offspring is in a new component.
- **Basin-component-aware seeding**: track which seed/profile lands in
  which component. May reveal that certain seeds/profiles ONLY
  produce certain components.
- **Forced-disjoint search**: explicitly destroy and rebuild large
  regions to escape current component.

## Linked

- [[basin-permutation-group]]
- [[e2-maximally-adversarial-thesis]] axis 6
- [[vol-65]]
