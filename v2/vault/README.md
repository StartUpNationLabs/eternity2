# E2 Research Vault

Concept-first knowledge structure. Goal: stop the "plan items deferred 8 volumes ago" pattern.

## Layout

- `concepts/` — one page per algorithm class or research idea. Tracks: definition, when introduced, runs, results, current status. **Source of truth for "have we tried this?"**
- `basins/` — one page per notable board / basin (the 457 PT lock, the 440/469 breakthrough, etc.)
- `sessions/` — append-only journals per volume. Link to concepts; do not duplicate their content.
- `plans/BACKLOG.md` — single canonical T-list, edited across volumes. Status tags: `unbuilt`, `in-progress`, `built`, `refuted`, `wont-do`.
- `plans/CURRENT-VOL.md` — the ONE binding plan for the in-progress volume. Limited scope.

## Discipline (per user agreement 2026-05-13)

**Audit-at-open.** First action of every new volume:
1. Read `plans/BACKLOG.md`.
2. Any item with status `unbuilt` for **3+ volumes** must be picked, or explicitly marked `wont-do` with a reason. Aging items must resolve.
3. Update `CURRENT-VOL.md` with the chosen items.

**Concept entries** carry the durable knowledge. Sessions are journals; they should not redefine concepts.

**No quiet deletes.** If a concept is refuted, mark `status: refuted` with the evidence link — do not remove the page.
