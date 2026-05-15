# 479-UB basin: context and structural analysis

**Status**: discovered 2026-05-15 morning.
**Source**: `output/v17_alns_only/winning5_sa_t1_s1_1778670467.json`

## How it was created

From the file metadata:
- `alns_ms: 60000` (only 1 minute of ALNS compute)
- `ops_preset: winning5`
- `repair_kind: sa` (simulated annealing repair)
- `t: 1.0` (high temperature)
- Final score 457

This basin was **lightly explored** — only 1 minute of single-seed
ALNS compute. Yet it has LP UB 479 — the highest in our archive.

## Why this matters

The compute spent on this basin (~1 minute) is < 1% of what we
spent on the vol-32 458 basin (~8h cumulative across vol-44/45).
Yet the LP UB is +1 above vol-32's basin.

**Inference**: there may be MANY more high-LP-UB basins in our
4746-board archive that we never seriously tested.

## Structural relationship to known classes

| Comparison | Same (pos,piece,rot) | Top region piece overlap |
|---|---:|---|
| vs class A (vol-32 458) | 5 / 256 | 20 / 56 (36%) |
| vs class B (vol-32 457) | 9 / 256 | 17 / 56 (30%) |

Essentially disjoint from both A and B. This is a new family.
Mismatch geometry is top-band like class B, but UB is +2 above B.

## LP UB profile

| | bb | bi_ub | ii_ub | total |
|---|---:|---:|---:|---:|
| vol-32 458 (A) | 60 | 54.02 | 363.98 | 478 |
| vol-32 457 (B) | 60 | 54.17 | 362.83 | 477 |
| **479 basin (D)** | **60** | **55.48** | **363.52** | **479** |
| Combinatorial max | 60 | 56 | 364 | 480 |

The 479 basin is the closest to 480. Its B-I is 0.52 short of max;
its I-I is 0.48 short. Spread evenly.

To find a 480 basin: need bi_ub=56 AND ii_ub=364 simultaneously.
The 479 basin shows it's not unreachable.

## ALNS push result (vol-46)

8 ALNS-diverse seeds × 1h on this basin:
- All 8 seeds plateau at 457 (no lift)

The 479-UB basin is locked at 457 under ALNS-diverse, same pattern
as our class A 458 basin locked at 458.

## MIP cluster-repair result (vol-46)

28-cell MIP on union of all 10 mismatch clusters: **delta=0 in 0.46s**.

**Proven locally optimal at 457.** Same proof pattern as vol-32 458.

## Conclusion

The LP UB 479 cap doesn't translate to integer lift in this basin.
The 22-point LP-integer gap is consistent across all sampled basins:
- Class A: LP 478, integer 458, gap 20
- Class B: LP 477, integer 457, gap 20
- 479 basin (D): LP 479, integer 457, gap 22

**LP UB is a basin signature but not a predictor of integer ceiling.**
Each basin has a ~20-point gap that local-search cannot close.

To actually break 458 requires either:
- A basin where the LP-integer gap is smaller (none found in 18 LP UB
  tests across diverse basins).
- Multi-day MIP / RL / custom propagator work.

## Linked

- [[lp-ub-478-basins]]
- [[lp-ub-479-basin-found]]
- [[vol-46]]
