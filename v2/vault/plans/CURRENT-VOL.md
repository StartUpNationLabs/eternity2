# CURRENT VOL — vol-24 binding plan

**Opened**: 2026-05-13 at vol-23 close.
**Status**: draft, awaiting audit-at-open at next session start.

## Audit-at-open required at vol-24 start

Items aged ≥ 3 volumes per BACKLOG. Must pick or mark `wont-do`:

- **[[pt-tabu]]** — 5 vols overdue (since vol-17). Strong candidate.
- **`cooperative-pair-swap`** — 2 vols (vol-21). Borderline; vol-20 cycle_scan may have covered this — audit before building.
- **`color-relabel-search`** — 2 vols (vol-21). Score-preserving symmetry; low expected lift.
- **`forced-perturb-meta-op`** — 2 vols (vol-21). Larger-k basin_hop variant.
- **`joe-2019-sat-postprune`** — was already flagged for `wont-do` decision; aged 9 vols. Mark `wont-do` unless re-motivated.

## Suggested vol-24 binding items (1 strong, 1 backup)

### T1 (primary) — `score-optimizing-cp` (NEW from vol-23)
The vol-23 finding sharpened the prune-restart conclusion: CP fills in FirstSolution mode, so prune-restart-as-cold-start-seeder underperforms vanilla ALNS. The gap-closer is CP with score in the objective.

Two routes:
- (a) **MaxSAT via sat-encoder + kissat-rc2**. Blocked on `kissat-rc2-maxsat` (also unbuilt). Building the MaxSAT route means building both. 1-2 days.
- (b) **Branch-and-bound CP**: modify `recurse()` in `crates/solver-engine/src/lib.rs` to track an upper-bound on matched-edges-achievable-from-this-partial and prune branches whose upper < best-so-far. 1 day.

**Recommended**: route (b). Self-contained, doesn't depend on external solvers, directly composes with our existing prune-restart driver.

### T2 (backup if T1 wraps fast) — `pt-tabu`
5-vol-overdue audit item. 4-6 hrs build. Hash-cons states in PT chains; reject revisits to break the vol-22 442-plateau.

## Out-of-scope (parked, log to BACKLOG if discovered)

- All N-EXOTIC ideas — already `wont-do`.
- `cooperative-pair-swap`, `color-relabel-search`, `forced-perturb-meta-op` — staying in BACKLOG, audit-at-vol-25 if still untouched.
- `kissat-rc2-maxsat` — keep `unbuilt`; pick if route (a) for T1.

## Vol-close protocol reminder

At vol-24 close:
1. Update T1/T2 status in BACKLOG.
2. Update concept pages touched.
3. Write `sessions/vol-24.md` journal (compact, single page, link to concepts).
4. Update INDEX.md score-history row.
5. Draft `CURRENT-VOL.md` for vol-25.
