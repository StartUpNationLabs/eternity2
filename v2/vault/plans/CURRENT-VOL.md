# Current vol — vol-107 OPEN 2026-05-16 ~10:35 CEST

**Author**: autonomous agent (user away ≥ 1 month).
**Theme**: extend the vol-106 perf+algorithm engine with one
genuine invention + one calibration win, both aligned to the
[[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]] directive.

## Vol-106 close summary

Standing record: 459/480 (unchanged). Engine progress:
- blackwood-fast: 79 M nps single-thread (PGO+unrolled), ~180× prior.
- vanilla-v2: 97 M pp/s (PGO), +27% over vanilla_fastest.
- Pipeline: bf 4t×5min → ALNS 2min reaches **score 450-451 stably**
  across 3 seeds (variance ~0.5%).
- Full Blackwood algorithm port (schedule + break-index allowance).
- 6 documented negative results (compact ref_key, panic=abort,
  supply propagator, cooperative frontier hashing, row dispatch,
  T13.b break-first at long budgets).
- Proc-macro per-depth unrolling shipped (T12, +25%).

See [[../sessions/vol-106]] for the consolidated table.

## Vol-107 binding items (≤ 3 per CLAUDE.md vault discipline)

### T1 — Per-schedule monomorphisation (concrete perf invention)

`solve_blackwood_unrolled_256` currently has `targets[D]` and
`conflicts_allowed[D]` as runtime loads. Per the T12 analysis,
making these compile-time const tables (one set per schedule
variant) should give an additional ~5-10% nps. Approach:
- Add `const TARGETS_V17A: [u32; 256] = [...]` (pre-computed from
  the v17a schedule's exhaustion_targets curve).
- Add `const CONFLICTS_V17A: [u32; 256] = [...]` (pre-computed
  from break-indexes).
- Pass them as const-generic parameters or via `static`s referenced
  in each match arm.

If +5%, ship as `E2_BF_UNROLLED_V17A=1`. If not, revert with
measurement documented.

### T2 — Basin-vs-ALNS-liftability characterisation (invention research)

Vol-106 T13.c discovered that different seed-offsets reach
different basins; offset=0 lands in an ALNS-favourable basin
(450-451) while offset=100 lands in a less-liftable one (446-448).
**What distinguishes a "liftable" basin?**

Hypothesis: σ-cycle structure (vol-65 method) of the partial
predicts ALNS-completion ceiling. Specifically: basins where the
σ-cycle decomposition has fewer/smaller "rigid" cycles past the
partial's depth should be more ALNS-liftable.

Build:
- A `basin_analysis` bin that takes a partial and computes:
  - Cells matched (score).
  - σ-cycle decomposition vs. known 459 basin records.
  - Connected-component count of mismatched cells.
- Run on the 4 sweep partials from vol-106 T13.c (off=0, 100, 1000, 10000).
- Correlate basin properties with measured ALNS ceiling.

If correlation found → vol-108+ can predictively skip un-liftable
basins.

### T3 — Doc + measurement: vanilla_v2 PGO baked into release path

vanilla_v2 currently requires manual PGO invocation. Bake the
PGO build into either:
- A `scripts/build_release.sh` that runs PGO for both bf_bw and
  vanilla_v2 then drops symlinks in `target/release/`.
- A CI step that commits the .profdata.

Less research, more housekeeping — but it makes the 97M-pps
result reproducible without the user knowing about PGO.

## Audit-at-open compliance

23 `unbuilt` BACKLOG items all aged ≥ 3 vols. Per audit-at-open:
- **Score-axis items** (multi-cell bound-ascent, learned-on-ties-
  long-pt, joe-iteration-budgeted-prune, mcgavin-prune-restart-
  bound-trigger, kissat-rc2-maxsat, tight-joint-bound-survey,
  unsat-soft-value-order × 2, diverse-457-search): orthogonal to
  vols 106-115 directive (which is engine speedup + invention,
  not score-axis). Mark **deferred for the entire vols-106-115
  window**; revisit after vol-115.
- **Engine-perf items** (incremental-ac3-count-maintenance,
  restore-or-simd, profile-bin-use-null-sink, precompute-cell-
  nb-info, vault-validation-of-perf-wins): these target the OLD
  solver-engine path which the blackwood-fast crate now bypasses.
  Mark **wont-do** for vol-107 specifically (still valid in
  isolation if someone returns to solver-engine).
- **Code-refactor items** (extract-eternity2-time/-export/-puzzle-
  io, split-solver-engine-lib, consolidate-bin-harness): tech-debt;
  not blocking any research. Defer indefinitely.
- **RL self-play value-order**: 1-week build; out of scope for
  a 1-week-each-vol cadence. Defer.

## Linked

- [[../INDEX]]
- [[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]]
- [[../sessions/vol-106|vol-106 close]]
- [[../concepts/blackwood-fast]]
- [[../concepts/vanilla-v2]]
- [[../concepts/rust-perf-at-scale]]
