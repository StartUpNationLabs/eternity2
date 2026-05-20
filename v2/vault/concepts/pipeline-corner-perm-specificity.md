---
name: pipeline-corner-perm-specificity
description: "Vol-118 T2 — our pipeline (bound-ascent + Hungarian + ALNS) is corner-perm-specific. On McGavin's perm (3,2,0,1), pipeline reaches only 396/480 strict-canonical, vs 459/480 on our native (1,0,2,3) perm. Confirms vol-68 finding that McGavin's 469 is inaccessible to our algorithm — basins are corner-perm-locked under our search."
metadata:
  type: project
status: built
---

# Pipeline corner-perm specificity (vol-118 T2)

**Status**: `built` — confirms vol-68 with concrete numbers.

## Test

Pipeline: `edge_bound_ascent` → `edge_target_match` → `alns_only`
starting from corner-perm partial.

| corner perm  | source        | bound-ascent UB | Hungarian post | ALNS 5min   |
|--------------|---------------|----------------:|---------------:|------------:|
| (1,0,2,3)    | vol-60 p06    | 458             | (~441 typical) | up to 459   |
| (3,2,0,1)    | vol-60 p22    | 458             | 367 (5/5 OK)   | 396 (5/5 OK)|
| McGavin actual |             |                 |                | 469 (McGavin algo only) |

McGavin's corner perm with our pipeline only reaches 396 — 63 below
our native corner perm. The 469 host basin under McGavin's perm
is inaccessible to our pipeline.

## Why

The bound-ascent UB is the same (458) — the algorithmic structure
of color-supply is identical across corner perms. But the *realized*
basin under our pipeline reflects the SCHEDULE / ALNS bias toward
the corner perm we calibrated against.

This confirms vol-68's claim: McGavin's basin is rigid in a way our
algorithms cannot navigate. The corner perm (3,2,0,1) is the
necessary but not sufficient condition for the 469 basin; the
sufficient condition is McGavin's algorithm (heuristic schedule +
row pinning).

## Implication

For our pipeline to discover NEW high-score basins:
- Sweep corner perms (24 - 1 = 23 untested).
- Per perm, run full pipeline (bound-ascent → Hungarian → ALNS).
- Look for any that BEATS 459 OR finds a structurally distinct
  basin not in our existing corpus.

The corner perm sweep is ~few-hour scale at 5min ALNS × 24 perms.
Worth doing as a corpus-growth experiment.

## Linked

- [[basin-corner-permutations]] — vol-99 corner perm enumeration.
- [[multiple-459-basins-rigid]] — basin corpus.
- [[vol-118]].
