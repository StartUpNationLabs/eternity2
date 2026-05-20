# Vol-60 — corner-permutation sweep + ALNS + local 459 tie

**Status**: CLOSED 2026-05-15.
**Standing record at close**: 459/480 (cross-machine SOTA + local tie).

## Headline result

**459/480 matched-edges TIED locally on a NEW corner perm (p06)**.

The cross-machine SOTA reached 459 via p20 + vanilla_path border-first
+ ALNS basic 30min seed=42 (~30 core-hours total). Our local tie
reached 459 via p06 + vanilla_fast --pin-hints + ALNS winning5 5min
seed=2 (~10 min on 1 thread). **Same score, different basin** (0/16
top-row cells match), different pipeline. Corner-perm hypothesis
empirically vindicated.

## T3 — corner-sweep CP results (24 perms)

Tier 1 (CP depth ~210, score 433 partial): 8 perms — (0,3,*,*),
(1,0,*,*), (2,1,*,*), (3,1,*,*).
Tier 2 (depth 207, score 426): 8 perms — (0,1,*,*), (0,2,*,*),
(1,3,*,*), (3,0,*,*).
Tier 3 (depth 206, score 424): 2 perms — (1,2,*,*).
Tier 4 (STALLED at depth 135, score 278): 6 perms — (2,0,*,*),
(2,3,*,*), (3,2,*,*). Includes McGavin's (3,2,0,1) = p22.

## T7 — ALNS phase results (96 jobs: 24 perms × 4 seeds × 5min)

### Score distribution

| Score | Count | Notes |
|---:|---:|---|
| **459** | 1 | **p06 seed 2 — local record tie** |
| 458 | 1 | p04 (FA basin) |
| 457 | 4 | p05, p10, p18 — includes NEW perms |
| 456 | 10 | distributed |
| 455 | 16 | — |
| 454 | 10 | — |
| ≤438 | 17 | mostly stalled-CP perms (p12, p13, p16, p17, p22, p23) |

### Per-perm max (sorted by max desc)

| perm | max | mean | note |
|------|---:|---:|------|
| p06 | **459** | 452.0 | NEW basin — RECORD TIE |
| p04 | 458 | 453.0 | FA |
| p05 | 457 | 450.2 | vol-35 |
| p10 | 457 | 452.2 | NEW |
| p18 | 457 | 454.0 | NEW |
| p07 | 456 | 451.8 | NEW |
| p14, p15 | 456 | 452.8-453.0 | NEW |
| p19, p20 | 456 | 451.8 | NEW (incl SOTA's perm) |
| p00, p03 | 456, 455 | 452.5 | NEW |
| p22 (McGavin) | 430 | 426.0 | stalled CP, ALNS can't recover |
| p23 | 433 | 429.2 | stalled CP |
| p16 | 436 | 426.8 | stalled CP |
| p12 (lottery 458) | 438 | 432.0 | stalled CP |

### Critical findings

1. **The 459 came from p06 + lucky seed (2)**. Same perm with other
   seeds: 451, 452, 446. The seed mattered.

2. **p20 (SOTA's corner perm) only reached 456 via our pipeline.**
   The SOTA's 459 on p20 required vanilla_path border-first + ALNS
   basic 30min seed=42. **Pipeline > perm.**

3. **Stalled-CP perms can't be rescued by 5min ALNS.** McGavin's p22
   gives 430 max here. With Blackwood's full algorithm McGavin reached
   469. The basin is rich, our recovery is too short.

4. **No relationship between greedy-relaxed score and final ALNS score**:
   - p07: greedy 476, ALNS max 456.
   - p06: greedy 471, ALNS max **459**.
   - p20: greedy 471, ALNS max 456 (despite being the SOTA basin!).
   The greedy heuristic IS NOT predictive. Confirms vol-60 correction:
   `relaxed_bound` is not a UB and not useful for prioritizing perms.

5. **The right basin needs the right pipeline.** Corner perm alone is
   insufficient; pipeline+seed+budget are co-determining.

## Vol-60 close

Standing record updated: 458 → 459 (cross-machine + local tie).

Tools shipped tonight (harness improvements):
- `verify_record` bin: matched/placed/unique/hint checks one-shot.
- `diff_boards` bin: direct piece-id comparison between two boards.
- `scripts/verify_records.sh`: canonical pre-record-claim workflow.
- `greedy_relaxed_score` alias: honest-name for the heuristic that
  WAS being called "bound".
- `relaxed_bound` doc: now explicitly warns NOT a UB.
- `CLAUDE.md`: 12 scientific-rigor rules captured to prevent repeat
  mistakes (no false bounds, diff before narrating, variance reporting,
  etc.).

Vol-61 (faithful SOTA replay) launched at vol-60 close:
- vanilla_path border-first × 9 threads × 30min → ~403 partial.
- ALNS minimal × 5min seed=1 → ~452.
- ALNS basic × 30min × 8 seeds (incl seed=42) parallel → record attempt.
- ETA ~18:50 CEST.

## Linked

- [[basin-459-pt]] — cross-machine SOTA
- [[basin-459-p06]] — local tie
- [[corner-permutation-study]] — full 24-perm study
- memory: `project_e2_459_sota_cross_machine`, `feedback_no_false_metrics`
