---
name: mcgavin-basin-top-bottom-symmetry
description: Test whether McGavin's 469 basin admits BOTTOM-N row reconstruction with same sharp threshold as top-N. Hypothesis pre-registered 2026-05-16 00:24, before vol-82 results.
metadata:
  type: project
---

# McGavin basin top/bottom symmetry test (vol-82, pre-registered)

**Status**: `unbuilt` (vol-82 currently running, results pending).
**Origin**: vol-68 found top-N=14 → 469 reconstruction; never tested bottom-N.

## Pre-registered hypothesis (write-before-result, 2026-05-16 00:24)

**H1 (symmetric basin)**: Pinning McGavin's BOTTOM N rows (positions
where row >= 16-N) and running ALNS gives SIMILAR scores to top-N:
N=14 → 469, N=13 → 455-ish. Threshold sharpness same.

**H2 (asymmetric basin)**: Bottom-N pinning gives DIFFERENT scores
than top-N. Either:
- (H2a) bottom-N rigidly determines basin at SMALLER N (e.g., bottom
  -10 → 469 already), meaning the bottom half is more constraining.
- (H2b) bottom-N pinning FAILS to reach 469 at any N up to 15,
  meaning the basin is solely top-determined.

**H3 (search-asymmetric, not basin-asymmetric)**: ALNS scan order
biases search such that top-pinning is easier even if basin
geometry is symmetric. Distinguishable from H2 by varying ALNS scan
order in a follow-up.

## Why this matters

If H1 (symmetric): basin is geometrically symmetric. Implies
either-half pin works; partial information from either half is
equivalently useful.

If H2a: bottom-half is the "key". Different attack vector — find
basin via bottom-row enumeration not top-row.

If H2b: top is uniquely determining. Basin is fundamentally
asymmetric. Stronger version of vol-68 "top-row determines basin"
finding.

If H3: ALNS scan order is biasing. The underlying basin is
isotropic. Implies a bidirectional ALNS would have different
performance.

## Method (vol-82)

For N ∈ {11, 12, 13, 14, 15}:
1. Extract McGavin rows {16-N..15} as pins (16N pieces).
2. Save as partial JSON.
3. Run `alns_only` with this partial, 60s budget, winning5 ops,
   seed=1.
4. Record final score.

Compare scores to vol-68's top-N values: top-N=13 → 455, top-N=14
→ 469.

## What invalidates each hypothesis

- H1 invalidated if any |bottom-N - top-N| > 5 at same N.
- H2a invalidated if no bottom-N < 14 reaches 465+.
- H2b invalidated if bottom-N=14 reaches 469.
- H3 alone cannot be tested in vol-82 — needs scan-order variant.

## Linked

- [[mcgavin-469-basin]]
- [[n-row-pinning-scaling]] (vol-68 parent)
- Memory: `project_e2_vol68_mcgavin_rigidity.md`
- Memory: `project_e2_vol68_n_row_scaling.md`
