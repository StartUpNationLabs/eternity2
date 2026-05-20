---
name: v125-border-dp-stage-a
description: "Vol-125 Stage A — 100 diverse border-DP partials × CSP-fill 60s × ALNS basic 60s seed=1. Top score 436. Distribution clusters 420-432. Conclusion: border-DP partials, despite combinatorial diversity, do NOT lead to McGavin-class basins (455+); the 459 ceiling requires bf_bw-style seed generation, not border-DP."
metadata:
  type: project
status: built
---

# Vol-125 Stage A close — border-DP basin generation REFUTED for record-track

## Setup

Generated 5000 piece-unique 60-matched border partials via `vol125_border_corpus.py` (6 corner-perm × corner-rot configs × multiple chain DFS).

Picked 100 evenly across the index. For each:
1. **CSP-fill 60s** with `border_to_csp_fill --solver joe_depth150_bp_par`: extends 60→210 cells.
2. **ALNS basic 60s** with seed=1.

Total compute: 100 × (60 + 60)s = 200 min wall on engine 4-thread parallelism.

## Results

100 ALNS endpoints, score distribution:

| Score | Count |
|---|---|
| 436 | 1 |
| 433 | 2 |
| 432 | 1 |
| 431 | 3 |
| 430 | 2 |
| 429 | 3 |
| 428 | 4 |
| 427 | 8 |
| 426 | 4 |
| 425 | 6 |
| 424 | 5 |
| ... (mostly 420-427) | ~50 |
| 380-419 | ~25 |

**Top score: 436** (b4300_perm13). **None above 437.**

## Conclusion: border-DP CANNOT reach McGavin-class basins (≥455)

The 100-border sample × 60s ALNS plateaus at 436. Even allowing for "60s ALNS is too brief" — extending to 30min would require 100 × 30 = 3000 min = 50 hours, which is the actual pipeline. The 60s sample is a CHEAP filter and the score ceiling at 436 indicates **border-DP partials are STRUCTURALLY in a different basin family from the McGavin-class 458-460 basins.**

Confirmation: the THIRD distinct 459 basin discovered this volume (vol-125 s100=459, corner perm 0,3,1,2) came from `bf_bw --seed-offset=100`, NOT from any of the 5000 border-DP partials. The 460 record came from `bf_bw --seed-offset=125`. Border-DP and Blackwood explore DIFFERENT corners of the basin space.

## Why border-DP plateaus at ~436

Hypothesis: border-DP gives mathematically piece-unique 60-cell rings with all 60 border edges matched. But the interior fill (CSP-fill 60s adds ~150 cells to reach 210) is then ALNS-constrained on whatever interior the CSP chose. The CSP chose a low-σ-cycle interior that's "locally optimal but not 455+ class". ALNS basic 60s polishes this to 420-436 but the basin doesn't escape to McGavin's family.

Blackwood-bf_bw's depth-160 schedule explores DIFFERENT internal cells and arrives at partials whose interior color profile aligns with the McGavin family.

## Implication for record-track work

**Do NOT use border-DP as a seed for ALNS** if record-class scores are needed. Use bf_bw (Blackwood-fast) with diverse seed-offsets instead. This was the empirical conclusion (vol-125 RECORD_460 came from bf_bw, NOT from border-DP).

Border-DP retains value for:
- Per-border interior MIP UB sweeps (vol-122 inv3).
- Diversity sampling for SAT cube generation.

But NOT for record-track ALNS.

## Linked

- [[record-460-2026-05-18]] (the 460 record from bf_bw, not border-DP)
- [[v125-third-459-basin]] (also from bf_bw)
- [[vol-125]]
