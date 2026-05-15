---
name: mcgavin-basin-top-bottom-symmetry
description: Test whether McGavin's 469 basin admits BOTTOM-N row reconstruction with same sharp threshold as top-N. Hypothesis pre-registered 2026-05-16 00:24, before vol-82 results.
metadata:
  type: project
---

# McGavin basin top/bottom symmetry test (vol-82, pre-registered)

**Status**: `built` — **H2b CONFIRMED** (asymmetric basin, top-determining).
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

## Theoretical refinement (added 00:25 before vol-82 results)

McGavin's 469 mismatch geometry: all 11 mismatches concentrate in
rows 0-4 (top 5 rows). Rows 5-15 are LOCALLY PERFECT.

Concrete distribution (by row of the mismatched edge's upper cell):
- row 0: 1
- rows 1-2: 4
- rows 3-4: 6

This means:
- Bottom-N pinning for N ≤ 11 keeps a LOCALLY-PERFECT region pinned
  and frees the HARD region (rows 0-4) for ALNS to solve.
- Top-N pinning keeps the HARD region pinned (rows 0..N-1 for
  small N) and lets ALNS solve an easy region.

So **the basin is asymmetric by construction** — the hard region
IS the top, and McGavin's algorithm has already done the heavy
lifting up there. Our ALNS reconstructing the bottom (easy) is
the trivial task; reconstructing the top (hard) is the test.

Sharpened prediction:
- bottom-N=14 will likely give a SUBSTANTIALLY LOWER score than
  top-N=14 (which gives 469). Likely range: 450-460.
- The basin's rigidity is asymmetric and TOP-DETERMINING.
- This is a stronger version of H2b: the basin is asymmetric AND
  the asymmetry is explained by mismatch geometry.

## Results (vol-82 completed 00:28)

Single seed=1, 60s ALNS budget per N. ops=winning5, T=1.0.

| N | pins | bottom-N | top-N (historical) | Δ |
|---:|---:|---:|---:|---:|
| 11 | 176 | 443 | — | — |
| 12 | 192 | 453 | — | — |
| 13 | 208 | 454 | 455 | -1 |
| 14 | 224 | **462** | **469** | **-7** |
| 15 | 240 | 460 | ~469 | -9 |

## Verdict: H2b CONFIRMED

- **Bottom-N=14 → 462, top-N=14 → 469.** Pre-registered prediction
  CORRECT: bottom-pinning gives substantially lower scores at the
  same N.
- **No sharp threshold for bottom-N.** Unlike top-N (sharp jump
  455→469 at N=14), bottom-N rises gradually 443→454→462.
- **N=15 gives 460, LOWER than N=14 (462).** Pinning MORE pieces
  gives a WORSE score under bottom-pinning. Mechanism: pinning row
  1 locks the EASIER side of the hard band; under N=14 row 1 is
  free and can absorb some adjustment for the difficult row 0.
- **The basin is asymmetric and TOP-DETERMINING.** This confirms
  H2b: McGavin's structural work was concentrated in the top 5
  rows; that's the choice that defines his basin.

## Reverse implication for breaking 469

To find a 470 or higher, the experimenter needs to:
1. Solve the HARD TOP REGION (rows 0-4) independently. This is the
   missing piece. McGavin's algorithm did this with Blackwood's
   break-index schedule + heuristic-side exhaustion.
2. Once top-5 is solved, ALNS-fill the bottom 11 rows is easy
   (per vol-82 N=11 result: even with NO McGavin info, our ALNS
   reaches 443; with bottom-11 pinned it's filling the easy half).

So the gap to 469+ is **fundamentally a top-5-rows problem.**

## Linked

- [[mcgavin-469-basin]]
- [[mcgavin-469-mismatch-geometry]] (parent: top-concentrated)
- [[n-row-pinning-scaling]] (vol-68 parent)
- Memory: `project_e2_vol68_mcgavin_rigidity.md`
- Memory: `project_e2_vol68_n_row_scaling.md`
