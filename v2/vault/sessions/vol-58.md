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

## T2 — partial 2WL optimization

Vol-58 T2 made unit_prop_from_clauses take the just-assigned literal
as hint, so it only walks clauses watching that one literal (vs
walking all clauses with any assigned literal). Single pass, no
fixpoint loop.

Test result on 6×6/5c:
- vanilla: 287k nodes, 4.35s.
- cdcl: 73k nodes (3.9× fewer), still 30s timeout.
- 28k clauses, avg 6.7 literals.

Per-node cost is still high (28k clauses × per-clause linear walk).
Real 2WL with watch advancement is multi-day Rust work; defer.

## T3 (incidental) — lottery 458 found, 0/5 hints

Vol-56's basin lottery (still running) has at 40/156 produced:
- 1 board with matched=458
- 2 boards with matched=457
- Plus ~30 boards at 446-456 range

The 458 lottery board: `result_t601_s002_d207_seed4.json`:
- 256 placed, all 256 pieces unique ✓
- matched=458/480 ✓
- **0/5 canonical hints obeyed** ✗
- Cell-by-cell agreement with vol-32 458 record: **3/256** (different
  basin entirely).

This is a "free-458" — a board that achieves matched=458 with full
piece-uniqueness but ignores ALL canonical hints. Same matched-count
as the standing record, on a completely different (0-hint) puzzle.

### Implication

- **Not record-breaking** under any canonical interpretation: vol-32
  458 had 3/5 hints, this has 0/5. Strict-canonical record stands at
  457.
- **Demonstrates basin diversity**: the lottery found a 3rd-distinct
  basin family achieving 458, beyond Family A and Family B.
- **The vanilla_fast pipeline without --pin-hints has multiple basins
  at the 458 ceiling**, all locally optimal but mutually disjoint.

### What this lottery proves

The lottery (basin-diversity test) does what we asked of it: finds
multiple distinct 457-458 basins. None exceed 458 in literal
matched-edges. The score-458 ceiling persists across all explored
basins.

