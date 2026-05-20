# VOL-57 — CDCL no-good learning Rust prototype

**Open**: 2026-05-15 (same autonomous session, continuing post-vol-56)
**Predecessor**: vol-56 (math design + green-light empirical signal).

## Mandate

Per autonomous mandate, multi-week work is in scope. Vol-57 builds
the first Rust implementation of CDCL no-good learning for E2.

Vol-56 measurements:
- Clauses are compact (median 6 literals on 6×6/5c).
- 96% of search states have ready-to-fire clauses.
- Conservative estimate of search-tree reduction: 50%+.

## Binding item — standalone `eternity2-cdcl-proto` crate

Per `cdcl-engine-integration.md`'s Option A recommendation, the
solver-engine refactor preserves the hot path. As a first step,
build a **standalone prototype crate** that implements the full
no-good learning system without touching solver-engine.

### Scope of the prototype crate

`crates/eternity2-cdcl-proto/`:
- Own minimal CSP solver for E2 (AC-3 with cause tracking).
- 1-UIP analysis.
- 2-watched-literals no-good DB.
- Tests on 6×6/5c and 8×8/8c puzzles.
- Comparison to vanilla DFS (search-tree size + wall-clock).

### Why standalone vs in-place refactor

- Faster iteration: don't break existing engine while developing.
- Cleaner math: pure no-good logic, no inherited optimizations to
  fight.
- Vol-58 ports to solver-engine once the prototype proves out.

### Implementation plan (this vol)

Day 1 (tonight, this session):
- Scaffold crate, add to workspace.
- Implement basic AC-3 with per-row cause tracking.
- 1-UIP analysis on AC-3 wipeout.
- 2WL data structure.

Day 2 (next session):
- Add unit propagation from learned clauses.
- Tests on 6×6/5c.

Day 3-5 (vol-58):
- 8×8/8c measurement.
- Performance tuning.

## Linked

- [[cdcl-no-good-e2]] — math design
- [[cdcl-engine-integration]] — engine refactor sketch
- [[vol-56]] — empirical justification
- [[vol-57]] — this vol's journal
