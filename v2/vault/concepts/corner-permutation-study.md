---
name: corner-permutation-study
description: \"by considering that we have something like 16 known starting positions
status: built
metadata:
  type: concept
---
# Corner-permutation study — basin-quality across 24 corner assignments

**Status**: in-progress (ALNS phase running for empirical scores).
**Origin**: vol-60 (2026-05-15), prompted by user thinking exercise:
"by considering that we have something like 16 known starting positions
if we pin hints+corners, how could that help?"

This page is the central knowledge-base for what we know about how
different corner-piece-to-corner assignments affect the search basin
on canonical Eternity II. Updated as data lands.

## The setup

E2 has 4 corner pieces (IDs 0, 1, 2, 3) — each has 2 BORDER sides and
2 colored sides. Each corner POSITION (TL=0, TR=15, BL=240, BR=255)
has exactly ONE rotation per piece that makes the 2 BORDER sides face
outward (TL needs rot 3; TR rot 0; BL rot 2; BR rot 1).

There are 4! = **24 distinct permutations** of corner-piece-to-corner.
Pinning canonical hints (5 cells) + the 4 corners = 9 pinned cells per
starting state.

## The 24 permutations enumerated

| Perm ID | (TL, TR, BL, BR) |
|---|---|
| p00 | (0, 1, 2, 3) |
| p01 | (0, 1, 3, 2) |
| p02 | (0, 2, 1, 3) |
| p03 | (0, 2, 3, 1) |
| p04 | (0, 3, 1, 2) |
| p05 | (0, 3, 2, 1) |
| p06 | (1, 0, 2, 3) |
| p07 | (1, 0, 3, 2) |
| p08 | (1, 2, 0, 3) |
| p09 | (1, 2, 3, 0) |
| p10 | (1, 3, 0, 2) |
| p11 | (1, 3, 2, 0) |
| p12 | (2, 0, 1, 3) |
| p13 | (2, 0, 3, 1) |
| p14 | (2, 1, 0, 3) |
| p15 | (2, 1, 3, 0) |
| p16 | (2, 3, 0, 1) |
| p17 | (2, 3, 1, 0) |
| p18 | (3, 0, 1, 2) |
| p19 | (3, 0, 2, 1) |
| p20 | (3, 1, 0, 2) |
| p21 | (3, 1, 2, 0) |
| p22 | (3, 2, 0, 1) |
| p23 | (3, 2, 1, 0) |

## Which perms appear in known records?

Across 9 verified records (8 ours + McGavin), only **5 of 24** perms
are represented:

| Perm | (TL, TR, BL, BR) | Records |
|------|---|---------|
| p04 | (0, 3, 1, 2) | vol-32 458 (3/5 hints), vol-35 458 — "FA basin" |
| p02 | (0, 2, 1, 3) | 3× blackwood_mrv 457 (5/5 hints) — "FB basin" |
| p05 | (0, 3, 2, 1) | vol-35 diverse/full 457 (3/5 hints) |
| p12 | (2, 0, 1, 3) | vol-56 lottery 458 (0/5 hints) |
| **p22** | (3, 2, 0, 1) | **McGavin 469 (community)** |

**19 of 24 perms have NEVER been entered by our pipeline.**

## Vol-60 sweep results — CP-best partial per perm

24 perms × 5min CP via `vanilla_fast --pin-hints --extra-hint 0:PID:3 --extra-hint 15:PID:0 --extra-hint 240:PID:2 --extra-hint 255:PID:1`.

### Score tiers (CP-best partial / depth reached)

| Tier | Score | Depth | Perms |
|---|---:|---:|------|
| **Top** | **433/480** | **210** | p04, p05, p06, p07, p14, p15, p20, p21 (8 perms) |
| Mid-high | 426/480 | 207 | p00, p01, p02, p03, p10, p11, p18, p19 (8 perms) |
| Mid | 424/480 | 206 | p08, p09 |
| **Stalled** | **278/480** | **135** | p12, p13, p16, p17, p22, p23 (6 perms) |

### (TL, TR) pattern groups

Within each (TL, TR) group, BL and BR vary but CP-best is IDENTICAL at
the 5min budget. This is because row-major scan reaches TL (depth 1)
and TR (depth 15) early but doesn't reach BL/BR (depths 240, 255) in
5min. Only the TL+TR piece choice exercises the constraint
propagation at depth ≤ 210.

| (TL, TR) | CP-best |
|---|---:|
| (0,3), (1,0), (2,1), (3,1) | 433 (4 best (TL,TR) pairs) |
| (0,1), (0,2), (1,3), (3,0) | 426 |
| (1,2) | 424 |
| (2,0), (2,3), (3,2) | 278 (these STALL early) |

### Critical: McGavin's perm STALLS

p22 (3,2,0,1) = McGavin's community-469 corner perm reaches only
depth 135, score 278 in 5min. This is the SAME tier as p12 (lottery
458's perm). **Our pipeline cannot naturally penetrate the (TL=3,
TR=2) basin space.** This is a structural observation, NOT a
fundamental basin-quality observation — see below.

## Heuristic "basin matching density" — NOT an upper bound

**⚠️ CORRECTION (2026-05-15)**: An earlier version of this section
called `relaxed_bound` "an upper bound on edge matches". That was
WRONG. `relaxed_bound` is a greedy local-search WITH PIECE REUSE.
It returns scores ABOVE achievable integer scores (e.g., 462 on the
458 board, which has integer ceiling 458).

The values below are HEURISTIC INDICATORS of matching density, not
hard ceilings. A true upper bound requires LP relaxation
(`border_lp_ub.rs`) or MIP (`border_mip.rs` / vol-55 cluster MIP).

Use these tables to RANK perms relatively, NOT to claim "perm X
can reach score Y".

User question: "they might yield worse scores, but how would we know
if they are in fact closer to a real solution?"

Honest answer: with `relaxed_bound` alone we DON'T know. We see
relative matching density, which is suggestive but not authoritative.
To answer mathematically: run LP UB or cluster-MIP per perm. That's
the right next experiment.

### Heuristic matching density on 9-cell partials (NOT a bound)

Values are `relaxed_bound(9-cell partial)` = greedy local search with
piece reuse. **Treat as comparative indicator, NOT as score ceiling.**

| Perm | (TL,TR,BL,BR) | greedy-score | Known record |
|------|---|---:|------|
| **p10** | (1,3,0,2) | **463** | NEW |
| **p11** | (1,3,2,0) | **463** | NEW |
| p06 | (1,0,2,3) | 462 | NEW |
| p07 | (1,0,3,2) | 461 | NEW |
| p08 | (1,2,0,3) | 460 | NEW |
| p09 | (1,2,3,0) | 460 | NEW |
| p18 | (3,0,1,2) | 458 | NEW |
| p19 | (3,0,2,1) | 458 | NEW |
| p21 | (3,1,2,0) | 458 | NEW |
| p20 | (3,1,0,2) | 457 | NEW |
| p22 | (3,2,0,1) | 457 | McGavin 469 |
| p23 | (3,2,1,0) | 457 | NEW |
| p04 | (0,3,1,2) | 455 | FA |
| p12-17 | (2,*,*,*) | 454-455 | lottery 458 (p12) |
| p05 | (0,3,2,1) | 454 | vol-35 |
| p02 | (0,2,1,3) | 452 | FB |
| p00, p01, p03 | (0,1)/(0,2) | 451-452 | NEW |

**KEY**: p10 and p11 (TL=1, TR=3) have HIGHEST 9-cell bounds (463).
These are unexplored. FA's perm has 455 — LOWER than 9 other perms.

### Heuristic matching density on MERGED partials (NOT a bound)

Same caveat: greedy local search with piece reuse. Indicator only.

| Perm | Placed | Bound | Note |
|------|---:|---:|------|
| **p07** | 213 | **476** | NEW (1,0,3,2) — HIGHEST absolute |
| p18 | 209 | 472 | NEW |
| p19 | 209 | 472 | NEW |
| p21 | 212 | 472 | NEW |
| p05 | 212 | 472 | vol-35 |
| p04 | 212 | 471 | **FA vol-32 458** |
| p06 | 213 | 471 | NEW |
| p08 | 208 | 471 | NEW |
| p09 | 208 | 471 | NEW |
| p20 | 212 | 471 | NEW |
| p11 | 209 | 470 | NEW |
| p00 | 209 | 470 | NEW |
| p01 | 209 | 468 | NEW |
| p23 | 138 | 468 | NEW |
| **p22** | **138** | **467** | **McGavin** — DENSEST (3.4/cell) |
| p15 | 212 | 467 | NEW |
| p03 | 209 | 466 | NEW |
| p14 | 212 | 466 | NEW |
| p02 | 209 | 465 | FB |
| p12 | 138 | 464 | lottery |
| p17 | 139 | 464 | NEW |
| p13 | 138 | 463 | NEW |
| p16 | 139 | 463 | NEW |

### Key metric: bound density (bound / placed_cells)

| Perm | Density | Note |
|------|---:|------|
| p22 | **3.39** | McGavin — HIGHEST density (sparse partial but very matched) |
| p23 | 3.39 | NEW, sister of McGavin |
| p13 | 3.36 | NEW (TL=2, TR=0) |
| p12 | 3.36 | lottery |
| p16 | 3.33 | NEW (TL=2, TR=3) |
| p17 | 3.34 | NEW (TL=2, TR=3) |
| p07 | 2.23 | NEW — highest ABSOLUTE bound (476) but low density |
| p04 | 2.22 | FA |
| p06 | 2.21 | NEW |

**Interpretation**: HIGH DENSITY (≥ 3.3) perms reach few cells but
those cells are highly matched. McGavin's basin behavior is consistent
with this — depth 135 but bound 467 indicates the basin is "denser"
in match-potential per placed cell.

**LOW DENSITY (~ 2.2) perms** reach more cells (213) but per-cell
match-potential is lower. These are the "easy" perms.

## Two hypotheses (with the corrected mathematical caveat)

⚠️ Both hypotheses below are based on the greedy-relaxed score, NOT
a true integer-score ceiling. Treat as conjectures pending LP/MIP
analysis.

### H1: HIGH GREEDY-RELAXED SCORE correlates with high record potential
- Conjecture: p07 (greedy-relaxed 476 on merged partial) reaches more
  matched edges under our pipeline than perms with lower scores.
- Predict: ALNS recovery from p07 might produce 458+.
- Test: ALNS from p07. If yields below 455, conjecture refuted.

### H2: HIGH MATCHING DENSITY indicates dense basins
- Conjecture: p22 / p23 / p13 (density 3.36-3.39 edges per placed
  cell) have geometrically denser partial states. Sparser (138 cells)
  but tightly matched.
- McGavin reached 469 on p22 with the Blackwood algorithm. Whether
  this reflects basin density or Blackwood's algorithm is unclear.
- Test: ALNS from p22 vs ALNS from p07. If p22 underperforms by ≥10
  points, density isn't predictive of OUR pipeline's reach.

## What the running ALNS phase will tell us (T7, ETA 17:40 CEST)

96 jobs (24 perms × 4 seeds × 5min ALNS) with `--extra-hint` pinning
all 4 corners. The score-per-perm distribution will distinguish:

- **If "easy" 213-cell partials yield 458+, hard 138-cell partials
  yield ≤ 445**: our pipeline favors high-absolute-bound. p07 is the
  next ALNS target.

- **If hard 138-cell partials surprise upward (≥ 455)**: the basin
  density signal is real, our pipeline CAN exploit dense partials,
  and McGavin-style perms become priority for vol-61 with longer
  ALNS budgets.

- **If FA's p04 yields highest (~458)**: corner perm doesn't matter
  much; existing pipeline is optimized for it.

## Cross-reference: the new 459 SOTA — IT USES p20!

Independent cross-machine result imported 2026-05-15: 459 achieved
via border-first vanilla_path DFS → ALNS pipeline ([[basin-459-pt]]).

**The 459 board's corners decoded from its bucas URL**:
- TL = piece 3 (rot 3)
- TR = piece 1 (rot 0)
- BL = piece 0 (rot 2)
- BR = piece 2 (rot 1)
- **Corner perm = (3, 1, 0, 2) = p20**

### What p20's metadata says

| Metric | Value | Note |
|---|---:|------|
| 9-cell relaxed bound | 457 | Mid-high tier |
| Merged relaxed bound | 471 | High but not the highest (p07 has 476) |
| CP-best in our sweep | 433 | **Top tier (depth 210)** |
| Bound density | 2.22 | "Easy" perm (low density) |

### What this confirms about corner-perm theory

1. **Corner perm matters for record-breaking.** The 459 SOTA uses
   p20 — a corner perm NOT in any of our 9 pre-existing records.
   Different corner perm → different basin → different record
   potential. **This claim is empirically confirmed by the 459 result
   itself.**

2. **"Easy" perms (CP-Top tier, depth 210) can yield records.**
   p20's CP-best in our sweep is 433. The CP partial at depth 210
   IS exploitable by ALNS to reach 459. **Confirmed by SOTA.**

3. **(WEAKER claim, NOT a math statement)**: under our pipeline, perms
   with high greedy-relaxed score have empirically correlated with
   high-score basins. p20's greedy-relaxed = 471 → SOTA 459. p04's =
   471 → 458 (vol-32 record). Whether this correlation holds for p07
   (greedy 476, untested) or p22 (greedy 467 with sparse partial)
   requires testing.

4. **Untested perms with greedy-relaxed score ≥ 470** are reasonable
   candidates for further investigation — but we cannot claim their
   integer ceilings without LP UB or MIP analysis:
   - p07 (greedy 476, untested)
   - p18 (greedy 472, untested)
   - p19 (greedy 472, untested)
   - p21 (greedy 472, untested)
   - p06, p08, p09 (greedy 471, untested)
   - p11 (greedy 470, untested)

   Right next step BEFORE investing more compute: run LP UB on each
   of these to get a TRUE upper bound on the integer ceiling per perm.

### Prediction for ALNS phase (now running)

Given p20 reached 459 with the right pipeline (border-first DFS + ALNS
minimal→basic + seed=42), our running v3 ALNS (5min × 4 seeds × 24
perms with corner pinning):

- Will likely yield ~452-456 on most perms (limited by 5min budget).
- p20 specifically might reach 458+ at one seed (less likely 459 at
  5min vs 30min in the source experiment).
- The relevant comparison is which 5min-perm tops the others, not
  whether 459 is reproduced in 5min.

The lesson: corner perm + sufficient time + right ops + right seed
matters. To reach 459, the SOURCE machine used **30 minutes** of
ALNS basic seed=42. Our 5min × 4-seed sweep is a quicker scout.

## Open questions

1. What corners does the new 459 SOTA use? Check the bucas URL pieces.
2. Does p07's 476-bound basin yield ALNS scores comparable to FA's
   p04 (which yielded vol-32's 458)?
3. Can the high-density McGavin-style perms (p22, p23) yield
   high-score boards with longer ALNS budgets (30-60 min)?
4. Why do 6 specific perms (p12-17, p22-23) stall at depth 135?
   Edge-color geometry analysis would clarify.

## Linked

- [[vol-60]] — sweep session
- [[basin-459-pt]] — new SOTA, cross-machine
- [[basin-mcgavin-469]] — community ceiling on p22 perm
- [[relaxed-bound]] — bound function used
