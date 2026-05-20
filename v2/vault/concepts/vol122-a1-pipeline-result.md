---
name: vol122-a1-pipeline-result
description: "Vol-122 A1 border-DP → CSP-fill → ALNS basic 30min result. Best 439/480 across 3 clean-slate borders (perm0/2/3). Far below 459 standing and 469 community ceiling."
metadata:
  type: project
status: built
---

# Vol-122 A1 — full pipeline result

## Pipeline

1. **vol-122 border-DP** generates 5 piece-unique 60-matched border partials
   (perm0, perm1, perm2, perm3, perm4); each is a distinct (corner-rot ×
   edge-piece-perm) configuration with all 60 border-border adjacencies
   color-matched.
2. **border_to_csp_fill** (new bin) treats the 60 placed cells as Hints and
   runs `joe_depth150_bp_par` to fill interior. 3 of 5 succeed
   (perm0/2/3 → 176 placed, 295-299 matched). perm1/4 fail with
   corner-piece-edge constraint conflict.
3. **--random-fill-remaining**: fill the 80 remaining cells with unused
   pieces at random rotation (Fisher-Yates seeded). Yields complete 256
   placed @ 309-314 matched.
4. **alns_only --ops basic --t 1.0 --alns-budget-ms 1800000 --seed 42**:
   30 min × 1 seed × 3 borders.

## Results

| Border config | CSP-only matched | Complete matched | ALNS final matched |
|---|---|---|---|
| perm0 | 295 | 311 | **424** |
| perm2 | 297 | 314 | **436** |
| perm3 | 299 | 313 | **439** |

**Best clean-slate basin = 439/480.**

## Comparison

- 439 vs **our standing 459** (vol-110/118): gap = -20 edges.
- 439 vs **McGavin 469**: gap = -30 edges.
- 439 vs **LP-UB 480** (vol-122 J4): gap = -41 edges (huge integrality gap).
- 439 vs **vol-122 J4 LP-UB on McGavin border** = 480: same LP-UB, very
  different actual ceiling. Supply-LP can't distinguish.

## Interpretation

**A1 is structurally working**. Clean-slate basins reach 433-439 in 30min
ALNS, which is a real basin discovery. But these basins are 20-30 edges
below our standing records — confirming the LP-UB is loose and the actual
basin ceiling depends on structural properties not captured by supply LP.

**What this rules out.** Just enumerating more clean-slate borders (without
a structural filter) likely won't break 459 — the 3 we tried plateau in a
band. Need a per-border MIP or per-border ALNS with much longer compute to
find an outlier.

**What this leaves open.**
- More seeds per border (need 8+ to estimate distribution).
- Longer ALNS (1h, 2h, overnight).
- Stronger CSP-fill (current plateaus at 176/256 — try gacolor_ac3_par
  with longer budget or invent new variable-order).
- B3 per-border interior LP-UB with positional constraints (in flight).
- Per-border integer MIP ceiling — would tell us if 439 is the basin
  ceiling or just an ALNS limit.

## Linked

- [[vol-122]]
- [[inv3-border-dp-seed]] — A1 source
- [[vol122-pcls-poc-result]] — J4 LP supply-UB observation
- [[INVENTIONS_BACKLOG]] — A1 entry update
