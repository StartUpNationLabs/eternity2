# VOL-36 — draft plan (auto-drafted at vol-35 close)

**Opened**: 2026-05-14 at vol-35 close.
**Status**: DRAFT for user review.

## Vol-35 close summary

- **458 record stands** (vol-32 vanilla_fast → ALNS, single occurrence).
- 5 distinct 457 cluster reps identified. σ-cycle analysis reveals
  clusters A and B are in the SAME piece-multiset family as 458.
  C, D, E are different families.
- Escape-457 lottery (20 runs × 3min from each cluster) ALL stay
  at 457. **Current ops cannot escape any 457 attractor.**
- vanilla_fast confirmed 124.7M pp/s single-thread.
- Deep family-255 lottery (48 × 3min × 4 ops) capped at 457.
- Deep_458_basin lottery (48 × 5min on vanilla_fast partial) in
  flight; results awaiting at vol-36 open.

## Key vol-35 insight

The vol-32 458 family includes 3 distinct 457 boards from blackwood_mrv.
We have 32 blackwood seeds tested; 3/32 = 9.4% produced a 457 in this
family. The 458 came from vanilla_fast + ALNS (one shot, lucky).

To break 458, we need either:
1. More compute on the vanilla_fast → ALNS pipeline (chance-based)
2. A genuinely NEW basin family with score-recoverable ≥ 458
3. An operator that can make cross-basin transitions at the
   σ-cycle scale (191 cells for B → 458)

## Audit-at-open

Aged items in BACKLOG to resolve:
- `multi-cell-bound-ascent` (14 vols, vol-22): mark wont-do.
- `bound-floor-alns-with-per-step-check` (14 vols, vol-22, partial):
  mark wont-do.
- `mcgavin-prune-restart` (recurring): vol-22 / vol-35 keep pointing
  at it. Either build PoC or formally defer with reason.
- `joe-iteration-budgeted-prune` (4 vols, vol-32): viable, low cost.

## Candidate binding items (pick 1-3, audit-at-open: max 3)

### T1 (RECOMMENDED) — McGavin-style prune-restart PoC

The vol-22 + vol-35 bound-ascent dead-end has now been hit twice.
The recovery from bound-ascent loses the basin context. McGavin's
prune-restart retains basin state during the bound walk — the
key missing primitive.

**Build a PoC**: at each bound-improving move, store the placed
pieces + retain in a pinned set. The pinned set grows monotonically
with the bound; only un-pinned cells can be modified. Once bound
reaches some target (470?), unfreeze with a small relaxation.

Cost estimate: 1-2 days. The σ-cycle data from vol-35 gives
concrete targets to validate the PoC against (clusters A and B
should be reachable from the 458 partial via the PoC).

### T2 — Multi-seed vanilla_fast → ALNS replication

Most direct path to a record. Vol-32's 458 was 1 run. Run 50+
parallel attempts at the same recipe (vanilla_fast 5min × 8 threads
+ ALNS 5min × 12 seeds × 4 ops). Total ~100 ALNS runs from the
vanilla_fast partial space. Cost: ~2-3 hours wall on 8 cores.

If vol-32 458 was 9% probability conditional on hitting that family,
then 50 attempts gives ~99% chance of finding ≥1 more 458, ~30%
chance of finding ≥1 × 459 (very rough order-of-magnitude).

### T3 — Bigger destroy operator

`MegaDestroy{k=200}`: destroy 200 random cells, repair via SA. K=200
exceeds the cluster B σ-cycle length (191), so within one move
it could traverse the 457 → 458 piece-permutation. Cost: half
day to implement, then test on the 5 cluster reps.

Risk: the "repair via SA" stage is the bottleneck — SA can't
reconstruct a coherent placement from a 200-cell gap. The vol-22
recipe (Hungarian-style assignment after destroy) might be what
this needs.

### T4 — Within-thread snapshot lottery

The aborted vol-35 experiment: t255_s000-s004 partials all start
the same prefix but diverge at depth 80+. Multi-snapshot ALNS
should test if within-family snapshot variation can find a 458.
Cost: 20 runs × 5min = ~15 min on 8 cores.

## Recommendation

T1 + T2 in sequence. T1 is the structural unblock; T2 is the
luck-replication that might find a 459 within current tooling.

If T1 takes too long, fall back to T2 + T4.

## Drafting status

This is a DRAFT, not the binding plan. User must review and pick
the binding items at vol-36 open.
