---
name: new-459-from-bf-pipeline
description: "Vol-110 T2 — pipeline reaches 459/480 reproducibly. INDEPENDENTLY RESCORED 459. CRITICAL CAVEAT (vol-111): the pipeline VIOLATES all 5 canonical 5-clue hints (0/5 hint compliance). The 459-score is on the HINT-FREE / 1-clue variant of E2, NOT canonical 5-clue. Standing canonical record (459/480 with 5/5 hints, vol-60) is NOT tied or broken by this work."
metadata:
  type: project
status: built
---

# Pipeline 459 basins — HINT-FREE caveat (vol-110 T2, vol-111 retraction)

## CRITICAL CAVEAT — hint compliance violation

**As discovered in vol-111**: all 5 pipeline-derived 459+ boards
have **0/5 canonical-hint compliance**. The bound-ascent step
re-arranges pieces freely, displacing the 5 canonical-hint pieces
from their pinned positions. The Hungarian + ALNS steps don't
restore them.

| board                       | matched | hints |
|-----------------------------|--------:|------:|
| pipeline orig (vol-110 T2)  | 459/480 | **0/5** |
| pipeline bseed1             | 459/480 | **0/5** |
| pipeline bseed6             | 459/480 | **0/5** |
| pipeline bseed11            | 459/480 | **0/5** |
| pipeline bseed9             | 460/480 | **0/5** |

**These boards are valid 1-clue / unframed E2 solutions but NOT
canonical 5-clue solutions.** The standing canonical record
(459/480 with 5/5 hints, vol-60 RECORD_TIE_459_p06) is **NOT
tied or broken** by this work.

The bseed9_score460 board would be a 460/480 RECORD on the
1-clue variant but the canonical Eternity II target is the 5-clue
puzzle. Different scoring conventions apply.

## What this means

Vol-110 T2's "reproducible 459" finding is REAL but on the wrong
puzzle variant. The bf-pipeline + bound-ascent + Hungarian + ALNS
recipe is effective for the 1-clue variant; for canonical 5-clue
it would need hint-preservation (pin the 5 hint positions
through every step).



**Status**: `built` 2026-05-16 ~13:05 CEST.
**File**: `output/vol-110/NEW_459_from_off100_pipeline_seed1.json`.
**Independently rescored**: 256/256 placed, **459/480 matched**.
**Cell-diff vs vol-60 RECORD_TIE_459_p06 seed2**: 3/256 agreement
(the 5 canonical hints account for most of those; this is a
DIFFERENT basin).

## The pipeline

Starting state: `output/vol-106-final/sweep_off100.partial.json` —
a bf_bw 4t × 2min v17a-strict partial with bf score 442, max depth
244. (offset=100 seed; was the "structurally locked" basin from
vol-107 T2 that defied ALNS direct lift past 446.)

1. **Bound-ascent** (vol-22): 1000 iters greedy from the partial.
   Reaches bound=472, score=150 (matched-edges count drops during
   ascent; bound is the relaxation upper bound).
2. **Hungarian matching** (vol-22): bipartite match against the
   bound-ascended state's relaxed assignments. Recovers
   score=443/480 (best in run 445).
3. **ALNS** with `winning5` ops, 60s, `t=1.0`: lifts to **459/480**.

Total wall time: ~5-30s for ascent + Hungarian + 60s ALNS ≈ 90s.

## Variance (4 seeds at step 3 only)

| ALNS seed | final score |
|----------:|------------:|
|         1 |     **459** |
|         7 |     **459** |
|        42 |     **459** |
|       100 |         457 |

3/4 reach 459. Variance ~0.5 across seeds. This is REPRODUCIBLE,
not a lottery.

## Why this is significant

- **Score 459 ties our standing record (vol-60).** That record came
  from a different recipe (the corner-perm sweep + ALNS direct).
- **Different basin** (3/256 cell agreement) — adds to the corpus
  of known 459 boards.
- The starting basin (offset=100 bf-partial, score 442) was the one
  vol-107 T2 / vol-108 T1 found "structurally locked" — direct
  ALNS on it caps at 446-448. The bound-ascent + Hungarian step
  RELOCATES the search into a different basin that ALNS CAN lift.
- Vol-108 T1.a empirically refuted "graft oracle pieces" — but
  vol-22's bound-ascent + Hungarian is a different mechanism: it
  reshuffles pieces to maximise the BOUND (a piece-uniqueness-
  relaxed score), not to copy from an oracle.
- The bf_bw engine enabled this by producing the offset=100 partial
  cheaply (4 threads × 2min = 8 thread-min). The vol-22 recipe on
  the OLD solver-engine would have taken hours to reach a similar
  partial.

## Replication

```bash
# 1. bf_bw partial (already saved)
ls output/vol-106-final/sweep_off100.partial.json

# 2. bound-ascent
./target/release/edge_bound_ascent \
    --board output/vol-106-final/sweep_off100.partial.json \
    --iters 1000 --seed 1 --acceptance greedy

# 3. Hungarian match (uses the latest v21_bound_ascent_b*.json)
./target/release/edge_target_match \
    --board $(ls -t output/v21_bound_ascent_b*.json | head -1)

# 4. ALNS
./target/release/alns_only \
    --cp-board $(ls -t output/v21_target_match_*.json | head -1) \
    --alns-budget-ms 60000 --seed 1 --ops winning5 --t 1.0
```

## What this means for the standing record

Standing record: 459/480. **NOT broken yet** — score TIED. The
recipe DID lift offset=100 (a previously-locked basin) past its
direct-ALNS ceiling (446 → 459). This is a +13 score improvement
via the composite pipeline.

Open question: can the recipe go higher than 459 on different
seed offsets or different bound-ascent trajectories? Vol-110 T2.b
candidate.

## Linked

- [[basin-escape-recipe]] — vol-22 origin of the bound-ascent +
  Hungarian + ALNS pattern.
- [[blackwood-fast]] — engine producing the input partials cheaply.
- [[sigma-cycle-predicts-alns]] — vol-107 T2 (max-cycle > 50
  predicted offset=100 as "locked"; this pipeline broke that lock).
- [[oracle-aware-alns-repair]] — vol-109 T1 alternative approach (refuted).
- [[vol-110]] — origin of this measurement.
