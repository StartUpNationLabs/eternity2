---
name: mcgavin-469-near-twin-orbit
description: Comprehensive single- and double-near-twin-swap test on McGavin 469. Single swaps: only 1/114 preserves 469. Double swaps: 0/6441 give 470+. The 469 score-level set under near-twin perturbations contains exactly 2 boards.
metadata:
  type: project
---

# 469-level set under near-twin perturbations (vols 68 + 99)

**Status**: `built` — measured 2026-05-16 ~03:37.

## Single near-twin swap

Tested all 114 near-twin pair swaps on McGavin's 469 (each
near-twin pair shares 3 of 4 edge colors). Score distribution:

| score | count |
|---|---:|
| 469 | **1** (piece pair 234↔235 at pos 73 ↔ 75) |
| 468 | 2 |
| 467 | 111 |

**Only 1 of 114 single swaps preserves 469.** That's the
[[../basins/basin-469-near-twin]] board found in vol-68.

## Double near-twin swap

Tested all 6441 pairs of near-twin swaps on McGavin:

| score | count |
|---|---:|
| 470+ | **0** |
| 468 | 3 |
| 467 | 118 |
| 466 | 233 |
| 465 | 5893 |
| 464 | 14 |
| 463 | 1 |

**Zero combinations give 470+.** Even the best double-swap gives
only 468 (worse than McGavin).

## Conclusion

The 469-score-level set under near-twin perturbations contains
**exactly 2 boards**:
1. McGavin's original 469
2. Vol-68 near-twin swap (pieces 234↔235 at positions 73↔75)

No near-twin perturbation (single or double) of McGavin's basin
reaches 470. This is a comprehensive negative — 6555 perturbations
tested, 0 record breaks.

## Linked

- [[mcgavin-mip-local-optimal-halo1]] (halo-1 MIP rigidity)
- [[mcgavin-halo3-percomp-proven]] (halo-3 rigidity)
- [[mcgavin-469-mismatch-geometry]]
- Memory: `project_e2_vol68_mcgavin_rigidity.md`
