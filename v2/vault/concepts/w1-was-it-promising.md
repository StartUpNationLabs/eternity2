---
name: w1-was-it-promising
description: "Honest vol-123 assessment of W1 PEPS-Lagrangian. Concrete wins: solves 4×4/6×6 generated puzzles, solves vol-13 piece-uniqueness obstruction, Rust port has working exact contraction. Unknowns: canonical 16×16 scale unvalidated (first attempt OOM'd). No record broken today."
metadata:
  type: project
---

# Was W1 PEPS-Lagrangian promising?

User asked end-of-session 2026-05-17. Honest answer below.

## YES — concrete demonstrations

1. **Math: vol-13 obstruction is solved.** vol-13 boundary-MPS overcounted by
   $10^{93}$ because it dropped piece-uniqueness. W1's Lagrangian dual on
   per-piece supply enforces it. The math is sound, derivation page
   [[w1-peps-design-derivation]].

2. **Empirical: solves small puzzles completely.**
   - 4×4 generated (16 pieces, K=8): full solve in 1 second.
     Verified: 16/16 unique pieces, 12/12 interior matched, 16/16 border correct.
   - 6×6 generated (36 pieces, K=8): full solve in 5 minutes.
     Verified: 36/36 unique pieces, 30/30 interior matched, 24/24 border correct.
   - Sequential piece-fixing accelerates as cells get pinned (late cells = 0 iter).

3. **Rust port: exact contraction WORKS.**
   - Cell tensor builder: implemented + 3 tests pass.
   - Exact contraction: log_Z matches Python to 6+ decimal places on
     2×2, 4×4, 6×6 puzzles.
   - Single off-by-one axis indexing bug was the difference between -inf and correct.

## NO — significant unknowns remain

1. **Canonical 16×16 (K=24) scale: unvalidated.**
   - First attempt at chi=32 silently died (likely OOM at ~3 GB RSS).
   - chi=16 attempt running now; may or may not converge.
   - Truncation at chi=16 may discard too much information to give useful
     marginals. Even if it runs, results may be wrong.

2. **Lagrangian dual convergence at canonical scale: untested.**
   - At 6×6 (K=8), converged in 70 iter. At 16×16 (K=24), state space is
     $24^{16} \approx 10^{22}$ — orders of magnitude larger.
   - Even if Lagrangian dual converges, marginals may not be well-defined
     under the chi-truncation regime.

3. **Marginal-to-correct-board correlation: untested.**
   - Even if marginals are computed correctly, do they identify the cells
     in the actual record-class boards?
   - Vol-12 BP marginals gave 18.84% interior reduction. W1 must beat this
     to be worth the engineering investment.

4. **Performance**: even at best-case scenarios, canonical W1 is multi-day
   compute. ALNS lottery is hours.

## What was definitively LEARNED (regardless of whether W1 wins)

1. **The math approach is correct.** This is publishable methodology even
   if it doesn't break the record:
   - Encoding C (piece-pool augmented PEPS with Lagrangian relaxation) is
     a clean reformulation.
   - Resolves the vol-13 piece-uniqueness obstruction.

2. **chi truncation has a critical threshold.** At chi=32 on 6×6 (K=8), the
   Lagrangian gradient was wrong (dual diverged). At chi=128 it converged.
   The empirical relationship "chi must scale with K^something" needs more
   measurement.

3. **Rust port is HARD but tractable.** The chain-contraction bond bookkeeping
   has many implicit invariants. Multi-day to do correctly. The eventual win
   (~10x over Python) is real but expensive.

## Other vol-123 results

- **W4 LkhChain operator**: implemented, currently in 4-seed lottery on 459 basin.
  Result TBD when ALNS jobs finish.
- **W7 frozen-variable measurement on 459 basin**: 1 frozen cell out of 256
  across 47 boards. 76.6% of cells have exactly 3 distinct piece-rotations.
  Confirms vol-20 "no deep backbone" finding empirically.

## What I'd do next if I had another week

1. **Week 1**: Get canonical W1 to converge (chi tuning, smaller eta,
   memory profiling). Likely 50-100 hours compute.
2. **Week 1, parallel**: Run W4 LKH-chain on many basins × many seeds.
   Best chance of immediate record.
3. **If W1 converges**: dump marginals, feed as CSP value-order, run W1+CSP
   pipeline. Compare against ALNS-only baseline.
4. **If W1 doesn't converge**: pivot to W3 (Kovalsky-Glasner-Basri Vandermonde
   LP) — different relaxation technique, potentially more robust.

## Bottom line

**W1 was the most ambitious direction this session and produced the most
learning.** Math and algorithm validated at small scale. Canonical scale
is a real risk. The standing 458 strict-canonical record from vol-122 is
NOT advanced today; whether W1 advances it remains to be seen.

If asked "was it worth the time?" — **yes for understanding, possibly for
records.** The vault entries (math derivation, empirical results, canonical
scale plan, this assessment) capture sufficient state for future sessions
to pick up the threads.

## Late-session update (2026-05-17 20:55)

After the W1 small-scale validation, pivoted to W2 (BP-decimation) which
WORKED at canonical scale in 11 minutes producing a 435/480 board. Then
ALNS basic lift took it to 448/480 in 10 more minutes. So:

  - **W2 BP-decim canonical pipeline (~50 min): 448/480** 
  - vs. standing 459 = 95.6% (record-class needs longer ALNS + better basins)

This is the **first end-to-end candidate METHOD** validated on canonical E2
in vol-123. It's not record-class but it's CHEAP (50 min) and REPRODUCIBLE
(no compute-expensive PEPS needed).

W1 vs W2 trade-off:
  - **W1**: stronger marginals, expensive (cloud-scale for canonical)
  - **W2**: weaker marginals, cheap (laptop runs in 11 min)
  - **Hybrid**: W1 marginals computed on cloud, fed as input to W2-style
    decimation. Best of both worlds. Path forward.

This is concrete progress toward "the way to solve".

## Linked

- [[w1-peps-design-derivation]]
- [[w1-peps-empirical-results]]
- [[w1-canonical-scale-plan]]
- [[web-roam-2026-05-17]]
- [[boundary-mps]] (vol-13 refutation, now solved by W1)
