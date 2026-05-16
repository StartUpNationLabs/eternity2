---
name: multiple-459-basins-rigid
description: "Vol-110 T2 follow-up. The NEW 459 basin found by bf+pipeline composition is MIP-halo-1 locally optimal (same as vol-60's 459 basin). 2 components instead of 4. Cell-diff = 253/256 from vol-60 (essentially disjoint). Strong evidence the 459-level set has MULTIPLE structurally-distinct basins, all halo-1-rigid. To exceed 459 requires board-spanning σ-cycle moves, not local ALNS."
metadata:
  type: project
---

# Multiple 459 basins, all halo-1 rigid (vol-110 follow-up)

**Status**: `built` 2026-05-16 ~13:15.
**Significance**: extends the [[local459-halo1-joint-proven|vol-90
rigidity result]] from "the vol-60 459 basin is rigid" to "459 is
generically rigid across multiple structurally-distinct basins."

## The two 459 basins

| basin | components | defect cells | halo-1 region size | MIP delta |
|---|---:|---:|---:|---:|
| vol-60 RECORD_TIE_459_p06 | 4 | 35 | 59 (joint, vol-90) | +0 PROVEN (1800s) |
| **bf-pipeline NEW_459** (vol-110) | 2 | 33 (31+2) | 52 + 4 | **+0 PROVEN per-comp** (~60s) |

Cell-diff between them: 3/256 agreement (= the 5 canonical hints
minus 2 border-related). They are structurally disjoint.

## Theoretical implication

The 459-level set is a UNION of MULTIPLE structurally-distinct
basins. Both tested basins are MIP-halo-1 rigid. This is empirical
evidence (not proof) that:

**Conjecture (vol-110 C1)**: For some K ≥ 2, the canonical
Selby-Riordan E2 has at least K distinct 459 basins, each MIP-halo-1
locally optimal. The 459-level set is therefore NOT a single basin
neighbourhood but a disjoint union.

**Conjecture (vol-110 C2)**: Local ALNS operators (destroy radius
≤ halo-1) cannot lift any of these 459 basins past 459 because
each is rigid in its halo-1 neighbourhood. Reaching 460 requires
either:
1. A board-spanning move (e.g. σ-cycle of cardinality ≥ ~80 cells)
   that re-routes pieces across the lattice.
2. A piece-set swap with a different basin that breaks the
   halo-1 rigidity by relaxing piece-uniqueness across regions.

These conjectures are consistent with vol-65/99/101's σ-cycle
indecomposability findings — the σ-cycles between 459 and 469 are
board-spanning, and applying subsets doesn't give a score gain.

## What this means operationally

The pipeline `bf_bw → bound-ascent → Hungarian → ALNS` can navigate
WITHIN the 459-level set (find new 459 basins) but cannot exceed
459 because every reachable 459 basin is halo-1 rigid.

To break 459, we'd need:
- A board-spanning ALNS op (`MegaBand{12}` exists, but its
  acceptance rate is near-zero on 459 basins).
- A different objective function that admits intermediate states
  below 459 as stepping stones (multi-objective ALNS, vol-110 T1
  candidate).
- A completely different algorithm (RL self-play with
  reward = max-score-reached, vol-30+ candidate).

## What to do next

1. **MIP halo-2 check on the new basin**: confirm the rigidity
   extends beyond halo-1 (mirror vol-93's halo-2 work on vol-60).
2. **σ-cycle measurement between the two 459 basins**: how big is
   the giant cycle? If similar to 459 ↔ 469 (~80 cells), it
   confirms the 459-level-set is structured like 469-target with
   board-spanning σ-cycles.
3. **Sweep more pipeline trajectories**: how many DISTINCT 459
   basins can the pipeline find? Each additional one strengthens
   conjecture C1.

## Vol-110 T2.b extension (2026-05-16 ~13:40)

Manufactured **3 distinct pipeline 459 basins** by varying the
bound-ascent seed on offset=100 (8 trials → 2 success). Plus
preserve the original = 4 pipeline basins. Plus vol-60 = 5 basins
total.

Pairwise σ-cycle structure (cycle sizes):

| pair                          | cycle sizes                |
|-------------------------------|----------------------------|
| vol-60 ↔ pipeline-orig        | [143, 31, 28, 25, 20, ...] |
| vol-60 ↔ pipeline-bseed1      | [112, 80, 24, 12, 10, ...] |
| vol-60 ↔ pipeline-bseed6      | [190, 40, 7, 6, 6, ...]    |
| pipe-bseed1 ↔ pipe-orig       | [11, 10, 6, 4, 3]          |
| pipe-bseed6 ↔ pipe-orig       | [25, 10]                   |
| pipe-bseed1 ↔ pipe-bseed6     | [11, 9, 5, 5, 3, 3]        |

**Clustering finding**: pipeline basins are NEAR each other in
σ-space (max cycle ≤ 25). vol-60 is FAR from all of them (max
cycle 112-190). The 459-level set has at least 2 STRUCTURALLY
DISTANT CLUSTERS of basins.

**Blend test**: enumerated all 2^n σ-cycle subsets across 6 basin
pairs. **None** yields a blend with score > 459. The best
non-trivial blends are 451-455. Strong empirical refutation of
**Path B (basin blend → 460+)** from MATH_NOTES_2026-05-16.

Generalises vol-99's σ-cycle indecomposability from "459 → 469
cycles don't decompose" to "459 ↔ 459 cycles also don't decompose."

### MIP halo-2 check on new basin (vol-111 T2 — PARTIAL)

Tested halo-2 rigidity on the pipeline-orig 459 basin:
- **Component 1** (2 defect cells, 7-cell halo-2 region): delta=+0
  **PROVEN** in 18s.
- **Component 0** (31 defect cells, 67-cell halo-2 region): MIP
  killed at ~13 min CPU; INCONCLUSIVE.

The smaller component is halo-2 rigid. The larger needs hours of
MIP for a definitive proof. Conjecture C3 (halo-2 rigidity across
basins) is supported for the small component but not proven for
the large one.

### σ-distance to McGavin 469 (vol-111 finding)

For each of our 4 basins, compute σ-cycles to McGavin 469
(decoded from corpus). Max cycle size varies:

| basin                          | max σ-cycle to McGavin 469 |
|--------------------------------|---------------------------:|
| vol-60 RECORD_TIE_459_p06      |                         154 |
| pipeline orig (offset=100)     |                       **89** |
| pipeline bseed1                |                         116 |
| pipeline bseed6                |                         149 |

**Key**: the pipeline-orig basin has max σ-cycle **89** to McGavin —
significantly closer than vol-60's 154. This matches vol-99's
"~80-cell σ-cycle from local-459 to McGavin" within rounding —
the pipeline-orig basin is structurally similar to vol-99's
"local-459."

**Implication**: any Path A formulation should use the
pipeline-orig basin as the starting point, not vol-60. The
smaller σ-distance means smaller cycle subsets to manipulate,
making CP formulation tractable.

Decoded McGavin 469 saved at: `output/vol-110/mcgavin_469.placement.json`.

## Linked

- [[new-459-from-bf-pipeline]] — origin of the new 459.
- [[local459-halo1-joint-proven]] — vol-90 vol-60 459 rigidity.
- [[local459-halo2-percomp-proven]] — vol-93 vol-60 459 halo-2 rigidity.
- [[../PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — full rigidity
  theorem from vols 80-101.
- [[../sessions/vol-110]] — session journal.
