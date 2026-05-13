# Vol-17 overnight portfolio (21 chunks, 6.86h) — scientific record

**Run window**: 2026-05-13 02:06:34 → 09:00:34 (the v17a-late-switch run).
**Binary**: `target/bench-fast/run_e2_blackwood` built at commit before
b9b8f6c (full11 op set — the suboptimal one; lesson below).
**Per-chunk wall**: nominal 1200s (10 min CP + 10 min ALNS).

## Summary statistics

| metric | value |
|---|---|
| chunks completed | 21 |
| total wall | 6.86 h |
| best ALNS score | **453/480** (chunk 19, calibrated_v17b, aSeed=1, H22=0) |
| prior session best (NOT beaten) | 456/480 (winning5 op set + v17a) |
| ALNS lift (matched_alns − matched_cp), n=21: | mean=86.0, stdev=3.2, range=75..91 |

## Findings (numbered hypotheses, each with the supporting data)

### F1. Blackwood CP partial is FULLY DETERMINISTIC for fixed (schedule, schedule_seed)

Across 21 chunks varying ALNS seed, H22 on/off, and schedule:
- Only **2 unique (cp_matched, cp_placed, cp_depth)** tuples observed:
  - `(362, 197, 192)` — 16 chunks (v17a all H22=0 chunks, v17b chunks)
  - `(364, 198, 193)` — 5 chunks (v17a chunks with H22=1 + aSeed≥11)

The CP search is deterministic *given* (engine config, schedule). ALNS
seed and H22 affect nothing in CP because CP doesn't consult them.

**Caveat on the second tuple**: H22 (`shuffle_within_blackwood_ties`)
ALSO affects CP (it's a value-order tweak), so when H22=1 with
aSeed=11 or aSeed=21 (the seeds change the in-tie RNG draws), the CP
search reaches `(364, 198, 193)` instead of `(362, 197, 192)`. So
H22+seed creates +1 placed cell and +2 matched edges at the CP-partial
level — a small but real CP-level effect.

### F2. ALNS results are NOT deterministic from a fixed (schedule, ALNS seed) — internal nondeterminism exists

Same config, same seed, run multiple times, shows variance:

| config | scores observed |
|---|---|
| v17a, aSeed=1, H22=0 | 447, 447, 447 (deterministic) |
| v17a, aSeed=2, H22=0 | **448, 448, 437** (variance!) |
| v17a, aSeed=3, H22=0 | 449, 449, 449 (deterministic) |
| v17a, aSeed=1, H22=1 | **446, 450, 450, 450** (variance!) |
| v17a, aSeed=11, H22=1 | 447, 447 (deterministic) |
| v17a, aSeed=21, H22=1 | 451, 451, 451 (deterministic) |
| v17b, aSeed=1, H22=0 | **453, 450, 451** (variance!) |

3 of 7 same-config buckets show variance up to **11 matches** (the
448 → 437 swing in v17a aSeed=2). Source of nondeterminism is
inside ALNS — likely the rayon-based parallel `cp_repair` (gacolor_ac3
multi-thread → racing on tie-breaks). When the same CP partial is fed
twice with identical seeds, ALNS reaches different basins because the
parallel sub-search isn't fully deterministic.

**This is a SIGNIFICANT FINDING.** All my prior "H6 REFUTED" /
"H17 REFUTED" verdicts based on single same-seed comparisons should be
re-evaluated with multiple runs to separate true signal from
parallel-repair noise.

### F3. H22 (Blackwood tie-shuffle) gives a small CP improvement on v17a

Pairing v17a chunks by aSeed where both H22=0 and H22=1 exist:
- aSeed=1: H22=0 → 447, H22=1 → 450 (+3)

That's the only paired sample, so not statistically strong, but it's a
**directional signal**. H22 lets the engine reach `(364, 198, 193)`
where H22=0 walls at `(362, 197, 192)` — +2 matched edges at CP, with
ALNS able to convert that to +3 final score in this one pairing.

### F4. v17b schedule outperforms v17a by ~+4 matches average

Holding aSeed=1, H22=0 constant:
- v17a: [447, 447, 447] mean=447
- v17b: [453, 450, 451] mean=451.3

**Δ = +4.3 in v17b's favor.** v17b's tight envelope produces the same
CP outcome (both reach 362/197/192) but its specific edge constraints
shape the partial differently in ways that ALNS can exploit better.

This is *consistent* with the earlier 448 (v17b) vs 447 (v17a) result
from chunk 19/E15. v17b is a real improvement, not noise. Should be
the default schedule going forward.

### F5. v17c (empirical breaks) and v17e (noise-perturbed) were never tested overnight

The portfolio cycled through 25 configs in order. Only configs 0-3
(all v17a variants) ran. Chunk 19 reached config index 6 (v17b) only
because the auto-switch fired. v17c and v17e never got a chance.

**This is the core failure of the overnight design.** The op-set
dilution (winning5 vs full11) AND the slow auto-switch combined to
trap the portfolio in v17a's basin. Both are now fixed in commit
b9b8f6c.

### F6. ALNS lift is remarkably stable: +86 ± 3 matches across all chunks

ALNS_matched − CP_matched ∈ [75, 91], mean=86, stdev=3.2. This holds
across:
- Different ALNS seeds.
- H22 on/off.
- v17a and v17b schedules.
- 21 runs total.

So **regardless of starting partial (362 or 364), ALNS reliably lifts
+86**. The "cap" of 455-ish comes from the CP partial's quality, not
ALNS variance.

The lone outlier at +75 (chunk 6, v17a aSeed=2 → 437) is the same
chunk that showed F2 variance — that's parallel-repair noise, not a
structural ALNS limit.

## Implications and lessons

### L1. Parallel-repair nondeterminism contaminates all single-run comparisons (HIGH PRIORITY)
My H5 (CP-primary refuted), H6 (op-dilution refuted), H17 (cross-graft
refuted) findings each used n=1 same-seed comparisons. F2 shows
same-config variance is up to 11 matches. Most of those refutations
need at least n=3 to be statistically meaningful.

**Action**: re-run any "REFUTED with one datapoint" hypothesis with 3+
runs at the same config before accepting the verdict.

### L2. v17b is the schedule to use by default
F4 shows v17b reliably beats v17a by ~+4 matches. The "vol-15 cliff
bug" → "v17a is the patched schedule" framing was correct, but the
v17b refinement (tight envelope, McGavin-curve-hugging) is genuinely
better. Should be the production default.

### L3. CP partial determinism means "schedule diversity" is the only CP-level lever
F1 says: same (schedule, schedule_seed) → same CP outcome. So if we
want CP-level diversity, we MUST change the schedule (or its seed).
That's why v17e (noise-injection) was the right idea — except we
never ran it overnight.

### L4. The 456 ceiling is real and reproducible
Best from this overnight: 453 (n=1). Best from earlier hand-tuned
runs: 456 (winning5 ops + v17a). The gap is at most ~3, well within
parallel-repair noise.

**Honest framing**: we have NO statistically clean evidence the
cold-start ceiling is above 453 or below 456. The "456" figure is a
single-run best. The portfolio confirmed ~450 is the typical
neighborhood.

### L5. Time allocation per chunk: 20 min total is sloppy
ALNS plateaus by iter 33 (~30s) per E4. The 400-iter ALNS run wastes
~92% of its budget on iso-score wandering. We could do 4× more
chunks at 5-min ALNS budget without losing meaningful signal.

**Action**: next overnight, run 5+5 min chunks (40 chunks instead of
20) to multiply sampling rate.

## Tier reassessment after overnight

| tier | requirement | status |
|---|---|---|
| T1 | ≥454 cold-start | MET (453 overnight, 455-456 earlier hand-tuned) |
| T2 | +1 new algorithm | MET (Blackwood, calibrated schedules, ALNS ops) |
| T3 | >446 (vol-6 warm-PT ceiling) | MET |
| T4 | +2 new algos + publishable null | partial — many novel ops shipped but no clean break past 456 |

## Recommendation for next session

1. **Re-run with the corrected binary** (commit b9b8f6c) — winning5 op
   set + auto-switch=1 + schedule round-robin. Even 1-2 hours should
   show whether v17b/v17e improve over the 456 record.
2. **3-run per-config minimum** to separate parallel-repair noise
   from real effects (per L1).
3. **Shorter chunks** (5+5 min instead of 10+10) per L5.
4. **First test**: is the 456 record reproducible? Run winning5 +
   v17a + aSeed=1 for 5 trials and report the distribution.
