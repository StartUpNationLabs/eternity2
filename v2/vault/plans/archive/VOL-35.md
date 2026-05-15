# VOL-35 — draft plan

**Opened**: 2026-05-14 at vol-34 close.
**Status**: draft pending audit-at-open.

## Why this volume exists

Vol-34 produced 3 main outputs:
1. The piece_swap_hillclimb bug fix (+ verified all vol-32 records).
2. Encoding reconciliation for capiman's unsat database.
3. Empirical confirmation that vanilla_fast 8-thread × 30min only
   produces 5 distinct basin families with all caps at 454-457.

The bottleneck for breaking 458 is **basin diversity + ALNS recovery
quality** — confirmed across all measurements. Vol-35 should attack
exactly one of these.

## Audit-at-open

Items aged ≥ 3 volumes per BACKLOG that must be resolved or extended:

- `multi-cell-bound-ascent` (13 vols, vol-22): aged out — mark wont-do
  unless picked here.
- `bound-floor-alns-with-per-step-check` (13 vols, vol-22, partial):
  invasive, low EV given basin-escape recipe didn't deliver. Mark
  wont-do.
- `diverse-457-search` (14 vols, vol-21, partial): subsumed by vol-34
  T1+T3 (the vanilla_fast snapshot lottery IS the diverse-457 search).
- `joe-iteration-budgeted-prune` (3 vols, vol-32): viable, low cost.

## Candidate binding items (pick 1-3)

### T1 (RECOMMENDED) — fitness-landscape mapping on small puzzles

User-proposed (vol-34 mid-vol). Systematically enumerate local
optima and basin properties at 4×4 / 6×6 / 8×8, look for
transferable structural invariants.

See [[../concepts/fitness-landscape-mapping]] for the 5-phase plan
(enumerate LOs, measure basin properties, compute FDC, test
transferability, predict + exploit at 16×16).

**Why this is highest EV**: gives a principled basis for operator
design. Until we understand the landscape's structure, ALNS
operator-tuning is folk-wisdom. Many vol-15-vol-32 negative
results (e.g. bound-ascent-collapse, basin-escape ALNS recovery
failure) become explainable — and potentially fixable — if we
understand the saddle-point geometry.

Cost: 2-3 days. Compute is cheap at 6×6 scale.

**Gate**: at 6×6/5c, produce a basin graph with ≥50 LOs and
measured saddle-heights. At 8×8/5c, confirm at least one invariant
from 6×6 (e.g. "best basin is within Hamming N/4 of every other
basin"). Predict canonical-16×16 saddle-height and compare to
the vol-18 76-cell barrier (oracle-data point).

### T2 (medium EV) — vanilla_fast oversubscribed probe

Run vanilla_fast with `--threads 32` AND `--snapshot-on-visit`.
More distinct early prefixes → more basin families. The 5 → 32
basin-family count would 6× the lottery's exploratory coverage.

Cost: 1h compute. Builds on vol-34 T1 infrastructure.

**Gate**: lottery from new partials produces a verified score ≥ 458
(rescore_board confirmed) on a non-vol-32 seed.

### T3 (medium EV) — soft unsat-pruner depth-conditional

Wire capiman's unsat database into engine as `ValueOrder::UnsatSoft`
active at depth < 100, fallback to MRV+LCV at d ≥ 100. The depth
analysis showed the unsat signal is strongest at shallow depths
(rank 0-12% at d=30-120, inconsistent at d≥160).

Cost: 4-6h build + 2h measurement. Uses ml/data/ reconciliation maps.

**Gate**: at depth=120 with unsat-soft + joe_depth150_bp, depth ≥ 174
matches insertion mode baseline. AND no canonical-validity
violations on a known-good 458 partial test.

### T4 (low EV, deferred) — Joe iteration-budgeted prune

Build iteration-count-triggered prune-restart from vol-32 BACKLOG.
30-49% search-space reduction expected. Defer if T1+T2 fill the volume.

## What this vol explicitly does NOT do

- ❌ Code refactor (vol-33 territory).
- ❌ More ML training.
- ❌ Hard unsat-clause-pruner (refuted vol-34).
- ❌ Basin-escape recipe extension (vol-22's path; bounds without
  ALNS-recovery).

## Cost summary

- T1: 0.5 day (probe + analysis)
- T2: 0.5-1 day (build + measurement)
- T3: 0.5 day (build) + 0.5 day (compute)

**Total**: 1.5-2 days.

## Linked

- [[vol-34]] — predecessor.
- [[unsat-clause-propagator]] — concept, status updated.
- [[vanilla-fast-backtracker]] — infrastructure to extend.
