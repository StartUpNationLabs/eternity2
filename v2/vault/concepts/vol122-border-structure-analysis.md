---
name: vol122-border-structure-analysis
description: "Vol-122 border-structure analysis: all valid 60-matched borders have identical interior-color multiset; differences are permutation/rotation. Color-gap uniformity does NOT correlate with eventual ALNS score."
metadata:
  type: project
status: built
---

# Vol-122 — border structural analysis

## Setup

Compared 5 borders:
- perm0, perm3 (clean-slate, A1=424 and 439 ALNS)
- McGavin actual border (469-host)
- mc_b001, mc_b050 (our generated borders with McGavin's corner perm)

## Finding 1: identical interior-color multiset (POSITIVE invariant)

ALL borders have the same 56-color multiset on their interior-facing edges:
```
{6:4, 7:5, 8:3, 9:3, 10:1, 11:1, 12:2, 13:3, 14:4, 15:6, 16:4, 17:2,
 18:3, 19:6, 20:4, 21:3, 22:2}
```

**Why**: every valid border uses the same 60 pieces (4 corners + 56 edges). The pieces' interior-facing edges' color multiset is determined by the piece set and the constraint that border-side edges = 0, not by the permutation.

## Finding 2: positional permutations differ wildly

- perm0 vs perm3: 38/56 positions have different colors
- perm0 vs mcgavin: 52/56 different
- perm3 vs mcgavin: 49/56 different

## Finding 3: color-gap UNIFORMITY does NOT predict score (refuted hypothesis)

**Hypothesis tested**: McGavin's border puts colors at uniform cyclic spacings, enabling more matching with interior pieces.

**Measurement**: variance of cyclic gaps per color, weighted by occurrence count.

**Result**:
- McGavin actual: uniformity = **148.27**
- Our perm0 (ALNS=424): **108.24** (MORE uniform than McGavin!)
- Our perm3 (ALNS=439): **110.05** (MORE uniform!)
- 100 mcgavin-perm-borders: range 119.90 to 161.09 (McGavin in the middle)

**Conclusion**: uniform color spacing is NOT the discriminator. Our worst-scoring borders are MORE uniform than McGavin.

## Finding 4: per-border-cell single-piece supply is also invariant

For each border cell's interior-facing color, count interior-piece-rotation
options that can place a piece adjacent. Sum across all 56 cells:

| Border | sum_supply | min_per_cell | mean |
|---|---|---|---|
| perm0 | 2548 | 43 | 45.5 |
| perm3 | 2548 | 43 | 45.5 |
| mcgavin | 2548 | 43 | 45.5 |

Identical. The single-piece per-cell supply is determined by the color
multiset, which is invariant.

## Finding 5: Rust border_lp_ub (per-cell-pair LP) also identical

| Border | bb | bi_ub | lp_interior | total_ub | solve_time |
|---|---|---|---|---|---|
| perm0_b0 | 60 | 56.0 | 364.0 | **480.0** | 511s |
| McGavin | 60 | 56.0 | 364.0 | **480.0** | 422s |

The MUCH stronger per-cell-pair LP (with positional constraints) also says
480 for both. Even rigorous LP can't distinguish 469-host borders from
439-host borders.

## Conclusion

**LP-style methods cannot distinguish "good" basin-hosting borders from
"bad" ones at any level we've tested**: per-color supply, per-cell-pair
geometry, color-gap uniformity, per-cell single-piece supply. All invariant
across all valid borders.

The 30-edge gap between McGavin (469) and ours (439) is entirely
INTEGER-STRUCTURAL — captured only by full MIP or actual ALNS search.

## Open question

What structural property of the border permutation enables 469 vs 439? 
The supply-LP says 480 for all (refuted as discriminator by [[vol122-pcls-poc-result]]).
The positional permutation matters, but uniformity isn't the right metric.

Next hypotheses to test:
- Specific 2-color pairs at adjacent cells (= which color pairs the interior pieces favor for 2-cell band matches).
- Match-density vs interior piece availability per local 2×2 region.
- Cycle structure / sigma-orbit of the border with McGavin.

## Linked

- [[vol122-a1-pipeline-result]]
- [[vol122-pcls-poc-result]]
- [[vol-122]]
