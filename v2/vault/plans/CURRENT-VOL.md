# CURRENT VOL — vol-25 binding plan

**Opened**: 2026-05-13 at vol-24 close.
**Status**: draft, awaiting audit-at-open at next session start.

## Audit-at-open required at vol-25 start

Items aged ≥ 3 volumes per BACKLOG. Must pick or mark `wont-do`:

- **`piece-orbit-as-atom`** (5 vols, vol-20). Low value (only 5 orbits of 256 pieces); previously flagged "likely wont-do".
- **`multi-cell-bound-ascent`** (3 vols, vol-22). 3-cycle and 4-cycle moves in bound landscape. Concept open.
- **`bound-floor-alns-with-per-step-check`** (3 vols, vol-22, `partial`). Invasive — touches ALNS internals.
- **`bound-ascent-then-blackwood-cp`** (3 vols, vol-22). Composes a vol-22 lever with vol-15 algorithm.
- **`gap-recording-instrumentation`** (3 vols, vol-22). Cheap (1-2 hrs). Diagnostic-only.
- **`diverse-457-search`** (3 vols, vol-21, `partial`). 0 build, overnight compute.
- **`kissat-rc2-maxsat`** (2 vols, vol-22). Just under threshold; pick if the user wants the MaxSAT route.

## Suggested vol-25 binding items (1 strong, 1 backup)

### T1 (primary) — Tighter MaxScore upper bound for [[score-optimizing-cp]]

Vol-24 shipped the loosest correct bound (`total_internal_edges - decided_edges`). A tighter per-cell bound would account for piece-uniqueness and remaining-domain feasibility on each unplaced cell:

```
for each unplaced cell pos:
    best_edges_for(pos) = max over r in domain[pos] of
        (#sides of r that match a placed neighbour
         + #sides of r that face an unplaced neighbour-with-matching-color-in-domain)
remaining_upper_bound = (sum over unplaced of best_edges_for(pos)) / 2
                       + edges_to_placed_neighbour(unplaced cells)
```

Cost: O(unplaced × domain × 4) per node. Pays for itself when it lets us skip subtrees the loose bound misses. Expected ~2× node-count reduction on canonical E2 (vol-24 measured 533 M nodes for 419/480; tighter bound should reach the same score in ~30s instead of 300s, or push the bound to 420-423 in 300s).

Built honestly — ~6-8 hrs (not 1-2 days).

### T2 (backup if T1 wraps fast) — Hybrid MaxScore-CP → ALNS pipeline

Use vol-24's MaxScore CP-fill (419 from vol-23 round-2 partial) as an ALNS starting point. The 419 board is presumably a better basin than the 297 partial; ALNS from 419 might exceed the 424 ALNS-from-297 mark. **Never measured.** ~30 min build (just chain in the existing ALNS binary), couple hours overnight compute.

This isn't a "new algorithm" binding item — it's a pipeline composition test. If it lifts past 451 (vol-22 cold-portfolio best), it's a real result.

## Out-of-scope (parked, log to BACKLOG if discovered)

- All N-EXOTIC ideas — already `wont-do`.
- `pt-tabu`, `joe-2019-sat-postprune`, `cooperative-pair-swap`, `color-relabel-search`, `forced-perturb-meta-op` — resolved `wont-do` at vol-24 open.
- `kissat-rc2-maxsat` — keep `unbuilt`; route (a) of score-optimizing-cp. Pick only if T1 wraps and we want the exact-joint-bound alternative.

## Vol-close protocol reminder

At vol-25 close:
1. Update T1/T2 status in BACKLOG.
2. Update concept pages touched ([[score-optimizing-cp]] for T1, [[alns]] / new for T2).
3. Write `sessions/vol-25.md` journal (compact, single page, link to concepts).
4. Update INDEX.md score-history row.
5. Draft `CURRENT-VOL.md` for vol-26.
