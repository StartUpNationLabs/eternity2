# VOL-38 — single-focus build: no-good CDCL learning

**Opened**: 2026-05-14 ~17:35 CEST at vol-37 close (forced via re-eval).
**Status**: BINDING. ONE binding item. No pivoting.

## Why this volume + this item

Vol-37 spent ~3 hours producing structural discoveries (pos 161
invariant, make-canonical operator, gh_e2 algorithm) without breaking
records. The user noted "innovation, new methods, things people never
tried" — gh_e2 is novel but doesn't lift records in basic form.

After two re-evaluations, the lesson: **stop pivoting**. Pick ONE thing,
ship it. No mid-vol redirections.

The choice: **no-good CDCL learning** (vol-38 BACKLOG). Standard SAT
solver technique (Conflict-Driven Clause Learning) never applied to
the E2 engine. Compounds across runs and within runs. Expected to give
real but bounded improvement.

## Vol-38 binding item (1, not 3)

### T1 — no-good CDCL learning in solver-engine

**What**: extend the backtracking engine to record reasons-for-failure
at each backtrack. Store these as no-goods (forbidden partial
assignments). On future search paths matching the no-good, prune
immediately.

**Spec**:
1. Engine maintains a no-good database keyed by (depth, partial
   assignment fingerprint).
2. On backtrack from depth d with failure reason r, store (d, r) →
   no-good.
3. Before each variable assignment, check if any active no-good matches;
   skip if yes.
4. (Optional) Persist no-goods to disk across runs.

**Build steps**:
1. Add `pub struct NoGoodDb` + `pub struct EngineNoGoodConfig` to
   solver-engine.
2. Wire into `EngineSolver::recurse` at backtrack site.
3. Add `--enable-cdcl` flag to vanilla_fast and prune_restart.
4. Smoke test: search depth + node count comparison on canonical E2
   with/without CDCL. Target: ≥5% node reduction at depth 100.

**Gate**:
- Engine builds with `cargo build --workspace`.
- Tests pass with `cargo test -p eternity2-solver-engine`.
- Canonical-E2 cold-start CP with `joe_depth150_bp_par`: nodes count
  reduces by ≥5% at iso-depth (60s budget).
- No memory blow-up (no-good DB size bounded by config).

**Cost**: 1-2d engine work, 0.5d measurement.

## What this volume explicitly does NOT do

- ❌ Mid-vol pivots to "let me also try X".
- ❌ Lotteries from existing records.
- ❌ More gradient variants of gh_e2.
- ❌ Structural scans on the same record set.
- ❌ Schedule calibration variants.

If T1 is built but doesn't yield ≥5% node reduction, vol-38 closes with
HONEST NULL. Move on, don't tweak parameters for 4 hours.

## Out-of-scope items kept in BACKLOG for future vols

- Soft unsat-pruner depth-conditional (vol-34 BACKLOG)
- ValueOrder::RecordsPrior (vol-37 finding integration)
- Diffusion + CP projection (vol-39+)
- Joe iteration-budgeted prune (vol-32 BACKLOG)

## Linked

- [[vol-37]] — predecessor (re-evals + structural discoveries)
- [[../concepts/blackwood-algorithm]] — engine that will host CDCL
- [BACKLOG]: `no-good CDCL learning` (currently task #29)
