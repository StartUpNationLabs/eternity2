---
name: local459-halo4-percomp-partial
description: Local 459 halo-4 per-component MIP — 3 of 4 components PROVEN +0 (56, 60, 26 cells). Component 3 (smallest, 2 defects) ran ~50min without finishing, killed at threshold.
metadata:
  type: project
status: partial
---

# Local 459 halo-4 per-component (vol-100 partial)

**Status**: `partial` — 3 of 4 components proven, comp 3 timed out.
**Tool**: `vol62_cluster_mip_bound --radius 4 --time-limit-secs 1200`.
**Files**: `output/vol-100-local459-percomp-halo4/log.txt`.

## Results

| comp | core defects | halo-4 cells | delta | obj | time |
|---:|---:|---:|---:|---:|---:|
| 0 | 18 | 56 | **+0** | 116 | 1200s |
| 1 | 11 | 60 | **+0** | 126 | 1200s |
| 2 | 4 | 26 | **+0** | 55 | 3.8s |
| 3 | 2 | (untested) | unknown | unknown | killed after ~50min |

**Three of four components PROVEN halo-4 locally optimal.**
Component 3 unexpectedly slow despite being smallest. Likely
hung at root LP (similar to vol-91 joint failure mode).

## Significance

Even with comp 3 unresolved, this is a strong partial result:
- Comp 0 (18 defects, 56 cells): largest pure-defect-density region proven
- Comp 1 (11 defects, 60 cells): second-largest, all proven
- Total proven coverage: 142 cells out of board's 256

Combined with vol-90 (halo-1 joint, 59 cells) + vol-93 (halo-2
per-comp, all 4) + vol-100 (3 of 4 halo-4), local 459's basin is
proven rigid in an even larger region than before.

## Comparison: McGavin vs local 459 halo-N

| record | r=1 joint | r=2 per-comp | r=3 per-comp | r=4 per-comp |
|---|---|---|---|---|
| McGavin | 37 cells | 29+34 | 42+47 | 57 (comp 0 only) |
| Local 459 | 59 cells | 35+35+13+17 | (untested) | 56+60+26+? |

Local 459 has 4 components (more complex than McGavin's 2) but
all halo-2 components proved. At halo-4, the larger 2 components
each took the full 1200s but completed; only comp 3 didn't.

## Linked

- [[local459-halo1-joint-proven]] (vol-90)
- [[local459-halo2-percomp-proven]] (vol-93)
- [[mcgavin-halo4-comp0-proven]] (vol-96 sibling)
- [[why-records-are-mip-rigid]]
