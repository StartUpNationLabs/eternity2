# CURRENT VOL — vol-23 binding plan

**Opened**: 2026-05-13 14:20 CEST (drafted at vol-22 close before vault refactor).
**Status**: in-progress, vault-restructured.

## Audit-at-open compliance

Per [vault/README.md](../README.md): all items aged ≥ 3 volumes were reviewed in `BACKLOG.md`. Two items provoked the audit:

1. **`prune-restart`** has been `unbuilt` since vol-14 (8 volumes). **Must pick or `wont-do` this vol.** → **PICKED as T1.**
2. **`pt-tabu-zobrist`** has been `unbuilt` since vol-17 (5 volumes). **Must pick or `wont-do` this vol.** → **PICKED as T2.**

Older-than-3-vol items not picked are now explicitly marked `wont-do (deferred until prune-restart shows ROI)` in BACKLOG.

## Vol-23 binding items (limit: 1 active)

Revised at user direction 2026-05-13 14:30: narrow to T1 only. T2 and the integration task stay in BACKLOG for vol-24+.

### T1 — `prune-restart` engine (1-2 day build) — ONLY binding item
**Score lift estimate**: +5..+10 if it closes the saturation gap in [[basin-440-469]].
- File: `crates/solver-engine/src/lib.rs`
- See `concepts/prune-restart.md`
- **Binding**: by end of vol-23 either built or this concept is marked `refuted/wont-do` with reasoning.

## Running in background (not binding work)

- PID 66809: 8h `alns_pt` on the 440/469 basin (will finish ~22:00 CEST). Result will be logged to [[basin-440-469]] at vol-close.
- PID 66953: batch basin recipe (100 seeds, ~5 hrs total). Result will be logged to [[basin-escape-recipe]].

Neither is a binding item — they're speculative compute. If their results suggest a new direction at vol-23 close, log to BACKLOG as new entries; do NOT pivot T1.

## Out-of-scope this vol (parked, not new ideas)

- `kissat-rc2-maxsat` — keep `unbuilt` in BACKLOG, revisit after T1/T2.
- `bound-ascent-then-blackwood-cp` — keep `unbuilt`.
- `multi-cell-bound-ascent` — keep `unbuilt`.
- All N-EXOTIC ideas (1, 2, 4, 5, 6, 7) — keep `wont-do`.

## Discoveries policy

If something interesting surfaces mid-vol: **add to BACKLOG with status `unbuilt`, do NOT pivot the vol's three items.** Only break this rule if the new finding obsoletes T1 or T2.

## Vol-close protocol

At vol-close:
1. Update each T1/T2/T3 status in BACKLOG.
2. Update any concept pages touched.
3. Write `sessions/vol-23.md` journal entry (append-only, links to concepts/basins, no plans).
4. Draft `CURRENT-VOL.md` for vol-24 using audit-at-open.
