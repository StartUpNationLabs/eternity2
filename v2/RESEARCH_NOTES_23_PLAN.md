# RESEARCH_NOTES_23_PLAN.md — vol-23 entry plan

**Date:** 2026-05-13 (drafted at vol-22 close).
**Predecessor:** read [[RESEARCH_NOTES_22.md]] + memory
[[project-e2-vol22-basin-escape]] first.

## State at vol-22 close

- **Score**: still 457 (no new record vol-21, vol-22).
- **NEW**: basin-escape recipe (bound-ascent + Hungarian + ALNS)
  produces basins with ceilings up to 471.
- **NEW**: ALNS-saturation gap = ceiling - plateau. In our 457 basin
  saturation gap = 4 (saturated by hours). In fresh basins
  saturation gap = 25-30. THIS IS THE BOTTLENECK.

## Vol-23 strategic framing

Two parallel paths:

**Path A — overnight saturation**: take the 440/469 basin and run
ALNS-PT for HOURS. The basin's saturation gap might close as ALNS
exhausts its score-local-maxima. If the saturation gap closes by
half (-15), we reach 454. If by all (-27), we reach 469 (community
record). HIGH-RISK HIGH-REWARD.

**Path B — better repair**: implement McGavin prune-restart. The
ALNS saturation gap is a structural ALNS limitation. McGavin's
algorithm enumerates more globally and would close the gap in
~minutes per basin rather than hours.

## Vol-23 priorities

### T1 — Overnight ALNS-PT on the 469-ceiling basin (cheap, runs while sleeping)

Run `alns_pt` with 12h+ budget, 16 chains, t_max 100+, on the
output/v17_alns_only/winning5_sa_t1.5_s1_1778671895.json (440/469).
Save every score plateau plus its bound. Hypothesis: with enough
time, the basin saturates and score climbs past 442.

### T2 — McGavin in-place prune-restart engine (1-2 days)

Per vol-14 memory `project_e2_mcgavin_blackwood_gap_analysis`. The
ALNS-saturation gap is exactly what this algorithm closes. Build
in `crates/solver-engine/src/lib.rs`.

### T3 — MaxSAT joint bound with kissat-as-RC2 (4-6 hrs)

z3 cannot solve our MaxSAT instances. Try kissat with `--time=N`
in a MaxSAT-mode wrapper, or compile RC2 specifically. The joint
bound gives the true ceiling.

### T4 — Batch basin generation (overnight, cheap)

Run the vol-22 basin-jump recipe 50+ times with diverse seeds.
Collect (score, bound) pairs. Find the highest-ceiling basin we
can reach. Push it with T1.

## Vol-23 entry tasks

1. Read this plan + RESEARCH_NOTES_22.md.
2. Kick off T1 + T4 in parallel (both cheap, overnight).
3. If overnight T1 reaches 458+: we have a new record!
4. If not: implement T2.

## Score progression history

| Volume | Cold-start record | Notes |
|---|---|---|
| 6 | 454 | warm-PT |
| 12-14 | 443 | engine-bound |
| 15 | 446 | Blackwood schedule |
| 17 | 447 | calibrated_v17a |
| 18 | 456 | cooperativity ops |
| 18 (overnight) | 457 | hot-PT T_max=30 |
| 19 | 457 (locked) | operator-lock proved |
| 20-22 | 457 | exhausted local search |

To climb past 457 we need either path A or path B above.
