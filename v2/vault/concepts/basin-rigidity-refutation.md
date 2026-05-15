# Basin rigidity finding REFINED — vol-70 day 1 refutation

**Status**: `refined` — vol-70 (2026-05-15).
**Origin**: cross-basin rigidity probe across 5 basin-component reps.

## Test

For each basin-component rep, pin top-14 rows + run ALNS with 4
seeds (1, 17, 42, 100) × 30s each. Spread = max - min score.

## Result

| component | target | scores | spread |
|---|---|---|---|
| 1 (McGavin) | 469 | [469, 469, 454, 469] | **15** |
| 23 (local-459) | 459 | [456, 457, 453, 456] | 4 |
| 0 (vol-32 family) | 458 | [456, 454, 455, 455] | 2 |
| 10 (vol-32 another) | 458 | [458, 457, 455, 456] | 3 |
| 33 (vol-61 family) | 458 | [454, 454, 450, 455] | 5 |

**McGavin's basin has THE HIGHEST spread (15)** — refuting my
earlier "McGavin is uniquely rigid" claim. With seed=42, our ALNS
gets only 454 from McGavin's top-14 partial. With other seeds, 469.

## Refined understanding

McGavin's basin is **SEED-DEPENDENT-RIGID**: most seeds (3/4 tested)
converge to 469 from his top-14 pin. One seed gets stuck at 454.

Our basins are **LOW-VARIANCE-FILL at 454-457**. They admit fewer
distinct completions but cap below 458.

So:
- McGavin's basin is **bimodal**: 469 or 454 (under our ALNS).
- Our basins are **unimodal around 455-457**.

McGavin's basin admits a 469-completion under MOST seeds. Our basins
do NOT admit a 469-completion under ANY seed.

## The REAL distinguisher

It's not rigidity-vs-looseness. It's:
**Whether the basin admits a >460 completion AT ALL.**

McGavin's does. Our 4 basins don't.

The bimodality (469 vs 454 in McGavin's basin) means our ALNS
sometimes finds the 469-completion and sometimes finds an alternate
454-completion. With multiple seeds, the 469 frequency is high but
not certain.

## Implication for vol-70 RGS

RGS as designed (filter for low-spread basins) would have FILTERED
OUT McGavin's basin (spread 15 — highest in test). That's the
opposite of what we want.

Better criterion: **HIGH MAX score across multiple seeds**, not
low spread.

That's just "run multiple seeds; take best". Which is what ALNS
does anyway with the seed parameter.

The genuine insight: **McGavin's basin is reachable from his
top-14-rows by ALNS in ~75% of seeds**. Our basins NEVER reach 469
under any seed.

## What this means for finding new high-score basins

A basin admits >460 completion iff PINNING its top-14-rows + ANY
ALNS seed gives ≥460. This is the right detection criterion.

Our 47 basin-components: none admit >460. Therefore none are in
the "McGavin family". Finding the McGavin family requires
constructing a top-14-row whose corresponding 32-cell bottom can
ACTUALLY reach 469.

This recovers the vol-68 finding: McGavin's TOP-14-ROW IS the
special structure. Our pipeline never builds this structure.

## Linked

- [[mcgavin-basin-rigidity]] (parent — refined here)
- [[mcgavin-n-row-scaling]]
- [[basin-component-landscape]]
