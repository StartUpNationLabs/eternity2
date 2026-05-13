# Session — vol-22 (2026-05-13)

**Time**: ~13:23 → 14:20 CEST.
**Cold-start record going in**: 457. **Going out**: 457.

## Concepts touched

- [[basin-escape-recipe]] — INTRODUCED (vol-22 composite of vol-21 building blocks); status `built`. Vol-22 breakthrough.
- [[relaxed-bound]] — used for measurements across basins.
- [[bound-ascent]] — used as step 1 of recipe; built `edge_bound_floor_alns.rs` (null).
- [[exact-joint-bound]] — INTRODUCED; status `unbuilt` (z3 attempted, failed).
- [[basin-440-469]] — INTRODUCED (discovered this session).
- [[houdayer-cluster]] — TESTED on (457, 456_k) pairs; refuted.

## Plan adherence

Vol-22 plan was: T1 bound-floor ALNS, T2 bound-ascent+CP, T3 multi-cell bound moves, T4 gap basin triage, T5 max bound survey, T6 prune-restart.

Vol-22 did: **T1 only**, plus the unplanned basin-escape recipe. T2-T6 NOT touched.

**Pattern recognized at vol-close**: 8 volumes of deferring prune-restart. User raised this issue. Vault restructure (vol-22 -> vol-23 transition) is the response.

## Discoveries logged to BACKLOG

- `multi-cell-bound-ascent` (from this session's bound-470 plateau finding)
- `bound-floor-alns-with-per-step-check` (per-RUN was null; per-STEP unbuilt)
- `kissat-rc2-maxsat` (z3 doesn't scale)
- `overnight-alns-pt-saturation` (8h test running, PID 66809)
- `batch-basin-recipe` (100-seed batch running, PID 66953)

## What we owe to vol-23

- Pick [[prune-restart]] as T1 (8 vols overdue per audit-at-open).
- Read overnight results (PID 66809, PID 66953) and update [[basin-440-469]].
- Write [[pt-tabu]] as T2 (5 vols overdue).
