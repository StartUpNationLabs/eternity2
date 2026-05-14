# Vol-34 / Vol-35 prep — Record-class landscape at 16×16/22c

**Date**: 2026-05-14.
**Status**: KEY FINDING from analyzing T3 lottery's 56 LOs (vol-34).

## TLDR

When you look at the LOs reached by ALNS-from-CP-partial (not
ALNS-from-random), the canonical 16×16 landscape shows **clear
basin-family structure** — a trimodal Hamming distribution.

This validates the user's "map the landscape" hypothesis at the
right scale. The 1000-LO 6×6/5c probe was at the WRONG scale +
wrong starting condition.

## Setup

Took the 56 verified-score boards from vol-34 T3's lottery
(scores 430-457, mean 446.7). These are ALNS-from-CP-partial LOs at
canonical scale.

## Hamming distance histogram (pairwise, 56 boards → 1540 pairs)

| Bin | Count | Description |
|---:|---:|---|
| H=45-49 | 1 | very close (same basin?) |
| H=50-69 | 6 | close (intra-basin) |
| H=70-99 | 60 | mid-distance |
| H=100-134 | 22 | medium-distance |
| H=150-174 | 240 | cross-basin (within thread family) |
| H=240-254 | 1216 | cross-family (different threads) |

**Trimodal distribution**: clear clustering at H=70-130 (intra-basin),
H=150-175 (cross-basin/same-family), H=240-254 (cross-family).

## Interpretation

Vol-34 T1 produced 14 vanilla_fast snapshots clustering into 5
thread-basin-families (intra: 80-90 cells prefix-shared; inter: 0-1).

T3's 56 ALNS results inherit this family structure:
- Within a thread-family, ALNS finds similar LOs (H ~80, lots of
  shared structure from the early prefix)
- Across thread-families, LOs are essentially random (H ~250)

**The basins ARE clustered** — into 5 macro-families.

## Vol-35 implication

The fitness-landscape question REVERSES from rugged-no-structure
(naive 6×6 result) to **MULTI-BASIN-FAMILY** when measured at
record-class scale.

This suggests an actionable vol-35 idea: **find more basin families**.
Vol-34 T1's 8-thread probe gave only 5 productive families (3
unproductive threads). With `--snapshot-on-visit` + 16-32 threads,
we could reach 20-30 family seeds. Each family has its own bound
ceiling (vol-32/34 data: bounds 457-471 across families). Higher-
bound families MAY contain 458+ LOs.

This is concrete vol-35 T1: **scale basin-family count via
oversubscribed threads + --snapshot-on-visit**, then run T3-style
lottery per family. Predict that:
- A family with bound 469-471 (vol-22 found these) → expected best
  LO 469-471 if ALNS reaches the family ceiling
- We've never tested ALNS from a 471-bound family's CP-partial

## Concrete vol-35 experiment

```
# Step 1: snapshot probe with many threads
vanilla_fast --threads 32 --pin-hints --budget-ms 3600000 \
    --snapshot-dir output/vol-35/t1_oversub \
    --snapshot-interval-ms 30000 --snapshot-min-depth 200 \
    --snapshot-on-visit

# Step 2: cluster snapshots by early-prefix Hamming, identify ~30 families

# Step 3: per family, run 4-8 ALNS seeds × 5min from one representative
# Step 4: compute family-wise bound ceilings via edge_bound_ascent
# Step 5: find the family with HIGHEST max-LO score
```

If step 5 finds a family with max > 457, that's a record break.
If not, we've at least mapped the full canonical-E2 basin-family
landscape (a real scientific contribution).

## Files

- `output/vol-35/landscape_t3/` — 56 T3 LOs with rebuilt summary.jsonl

## Linked

- [[vol-34-landscape-1000]] — the rugged result from naive ALNS-from-
  random; this superseded
- [[vol-34-basin-clustering]] — vol-34 T1's 5 basin families
- [[trajectory-families]] — vol-18's earlier finding (now generalized)
