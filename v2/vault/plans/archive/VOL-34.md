# VOL-34 — throughput exploitation + record chase

**Opened**: 2026-05-14 (vol-32 close).
**Status**: drafted at vol-32 close.
**Theme**: study + exploit vol-32's vanilla_fast throughput
(125M pp/s single-thread, 577M aggregate × 8 cores). Use it to find
459+ basins.

Companion to **vol-33** (code quality). Can run in parallel if the
user wants record-chase + refactor simultaneously.

## Why this volume exists

Vol-32 produced the vanilla_fast bin at 125M placements/sec (60×
faster than blackwood_raw). The basin landscape findings:

- 458 is the new record (vol-32). Basin-locked under ALL our ALNS
  ops presets (mega, full, hingeonly, componentonly all → 458 at
  5min × seed 1).
- Bound-ascent navigates to higher-bound configs (b463, b464 from
  the 458 board) but ALNS recovery from those doesn't reach 458+.
- 8-thread ALNS lottery on diverse vanilla_fast partials: 1/8 hit
  458; max stays at 458 (basin family ceiling).

**The bottleneck is basin diversity + ALNS recovery quality**, not
throughput. But more throughput enables:
1. Sampling thousands of distinct depth-210+ partials (basin diversity)
2. Affording slower-but-stronger per-placement propagators (algorithmic pruning)
3. Hours-long deep-CP runs (depth 220+ unexplored)

## Audit-at-open

- `unsat-clause-propagator-prototype` (vol-32 open): Python prototype
  shipped; Rust loader + 540MB CSR binary saved; encoding-reconciliation
  is the blocker. **PICKED, becomes T2**.
- `vanilla-fast-backtracker` (vol-32 open): **SHIPPED** at vol-32 close;
  becomes the foundation for T1 + T3.
- `diverse-457-search` (since vol-21, 13 vols): **subsumed** by T3
  (vanilla_fast basin sampling).
- `multi-cell-bound-ascent` (since vol-22, 12 vols): defer or mark wont-do.
- `joe-iteration-budgeted-prune` (since vol-32 open): defer to vol-35
  (vanilla_fast doesn't restart; prune-policy isn't the right axis).

## Binding items (3 tracks)

### T1 — Hour-long vanilla_fast probe + basin sampling

**Setup**: extend vanilla_fast to periodically (every 60s) save the
deepest partial seen. Run for 1 hour × 8 threads. Total: 480
thread-minutes of compute = ~3.6 trillion placements.

**Expected output**:
- ~60-480 distinct depth-210+ partials saved
- Possibly depth-215+ or 220 reached (vol-32 hit 211 in 1 min)
- Diverse basin families

**Cost**: 1 hour compute + 1h analysis = half day.

**Gate**: at least one partial reaches depth ≥ 215.

### T2 — Unsat-clause-propagator integration

**Prereqs ready from vol-32**: 540 MB CSR binary
(`output/vol-33/forbidden_all.bin`), 238 ns/lookup benchmark,
validator script (`ml/validate_unsat_partial.py`).

**Vol-32 blocker**: 74% of our placements aren't in capiman's
encoder; 21 conflict pairs on known-good moves. Encoding-
reconciliation must come first.

1. **Encoding reconciliation** (4h): capiman card↔our piece_id map
   via edge-tuple match. Validate against `edge_bp_165.json` until
   0 conflicts.
2. **Engine hook in vanilla_fast** (4h): add propagator call at
   each placement; lazy-load forbidden_all.bin via OnceCell.
3. **Measurement** (1h): pruning rate, throughput cost, depth lift.

**Cost**: 1-1.5 days.

**Gate**: 5%+ pruning rate AND zero canonical-validity violations.

### T3 — Mass ALNS lottery from vanilla_fast partials

**Depends on T1** (partials collected).

For top 100 partials by depth:
- 4 ALNS seeds × 5 min each × winning5 ops
- 1 ALNS run × 5 min × full ops (HingeDestroy + ConflictDriven{80} + MegaBand)
- Save scores > 458

Total: 100 × 5 = 500 ALNS runs = 250 min wall-clock on 8 cores.

**Gate**: at least one score ≥ 459 OR clear evidence the basin family
caps at 458.

## What this vol explicitly does NOT do

- ❌ Code quality refactors (that's vol-33).
- ❌ More ML.
- ❌ Vol-22 basin-escape from 458 (already tried at vol-32 close;
  bound-ascent moved to b464 but ALNS recovered to 452 — recipe
  doesn't generalize past 457).
- ❌ Heavy operator engineering (no Houdayer-on-ALNS-side this vol).

## Cost

- T1: half day
- T2: 1-1.5 days
- T3: half day compute, half day analysis

**Total**: 2-3 days.

## Linked concepts

- [[../concepts/unsat-clause-propagator]] — vol-32 prototype, vol-34 build target.
- [[../sessions/vol-32-458-NEW-RECORD]] — what we're trying to break.
- [[../sessions/vol-32-blackwood-mrv-discovery]] — alt cold-start path (456 ceiling).
