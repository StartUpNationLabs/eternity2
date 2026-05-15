# Vol-58 — multi-experiment, lottery-companion

**Open**: 2026-05-15
**Status**: in-progress.

## T1 — MIP on family-B basin (DONE)

Family-B 457 board (blackwood_mrv): mismatches concentrate in **top
rows (y=0-4)**, not bottom like family A. Consistent with blackwood
algorithm working top-down.

MIP cluster results on family-B canonical 457:
- (3,1)+5×4 cluster: 20 cells, 49 edges. LP=39.98, MIP=39, current=39.
- (6,0)+6×3 cluster: 18 cells, 39 edges. LP=32.0, MIP=32, current=32.

**Family B is also locally MIP-optimal**, just like family A. Both
families are as-good-as-the-search-finds within their respective
basins.

### Combined picture (vol-55 + vol-58)

| Basin | Records | Mismatch geometry | MIP-locally-optimal? |
|---|---|---|---|
| Family A (vol-32 458, 3/5 hints) | 3 | bottom rows | YES (vol-55, 4 clusters) |
| Family B (blackwood_mrv 457, 5/5 hints) | 3 | top rows | YES (vol-58, 2 clusters) |

Both basins are locally optimal. The path to >458 needs:
1. A DIFFERENT basin (lottery in progress, no luck so far).
2. Or a fundamentally different algorithm.

The LP-tightening / MIP arc is now fully closed:
- Vol-44: 196-cell whole-interior MIP on family A.
- Vol-55: 4 cluster MIPs on family A, all locally optimal.
- Vol-58: 2 cluster MIPs on family B, also locally optimal.

This is a major STRENGTHENING of the standing record's claim.
