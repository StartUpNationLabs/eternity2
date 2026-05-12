# RESEARCH_NOTES_12.md — vol-12: dual-track engineering + innovation

**Session start**: 2026-05-12 13:12 CEST.
**Predecessor**: vol-11 closed at 2026-05-12 (commit `4fe93f4`). NS-1 deficit
invariant measured on 82-board corpus. BP/SP on cell-encoding empirically
confirmed dead-end. Nodes/sec calibration: 2,101 nodes/sec vs McGavin
295M/sec (~140× constant-factor gap addressable, ~1,000× architectural).

**Calibration**: 469/480 = community ceiling (McGavin 2020). Our stack is
at 454/480 (vol-6 PT warm-started). Bar for "we caught up": ≥469. Bar for
"cleared SOTA": ≥470.

## Mission (vol-12, user override)

User instruction: **do everything, do not wait for confirmation, no time
estimates, take notes from real time (`date`), explore unwalked paths**.

Both engineering AND innovation tracks ship in this session.

### Engineering punch list (definitely ship)

1. **NS-1 deficit propagator** in Rust at `crates/propagators`. Δ=0
   necessary after border ring closes. Cost O(56·color_count). Add
   `EngineConfig::multiset_equality_propagator: bool` and wire into
   `run_extra_propagators` after gacolor (it's a similar tier).
2. **Depth-thresholded propagators**. Add
   `EngineConfig::depth_threshold_for_propagators: Option<u32>` (or per-
   propagator threshold). Sweep ∈ {0, 100, 150, 180} on canonical E2.
   Joe's prune-back-150 ⇒ skip expensive propagation under depth 150.
3. **Bitset domains** (the AUDIT_REPORT 7-step plan). Add bitset
   alongside existing `Vec<u32>` first, invariant test, then flip hot
   paths. Run `fleet --budget-ms 60000` baseline + after.

### Innovation tracks (all four, user said no choice required)

A. **Edge-color BP**: 480 vars × 22 colors, 256 cell constraints. Per
   `project_e2_dead_ends.md`, the explicitly-recommended message-passing
   alternative we haven't tested.
B. **CVM / GBP on 2×2 plaquettes**. ~225 plaquettes × ~10⁴ states. Cluster
   variation method captures short-range correlations BP misses.
C. **14×14 interior MaxSAT scaling**. Pin a known 469/470 border from the
   corpus, scale vol-7 MaxSAT machinery to 196 interior cells. Either
   constructive or impossibility proof.
D. **Hamilton-cycle frame enumeration**. 60-cell border ring as Hamilton
   cycle on edge-piece left-right compat graph, rotations inside edge
   labels. Filter by NS-1 deficit.

### Reading absorbed (line that mattered)

- `project_e2_dead_ends.md`: *"If we ever revisit message-passing, use
  edge-color encoding (480 vars × 22 colors, 256 cell constraints), NOT
  the cell-place-rotation SAT encoding."* — pinned direction for innovation A.
- `project_todo_engine_bitset.md`: *"The first hour is a low-risk 'add
  bitset alongside, write invariant test' slice — useful even if the
  full refactor doesn't happen that session."*
- `project_e2_ns1_deficit_invariant.md`: *"All 4 known 480 boards [...]
  satisfy A=B exactly. Necessary condition validated."* — propagator
  shippable.
- `reference_e2_bp_measurements.md`: *"Random outperforms BP and static,
  90 s budget. BP marginals add no value-order advantage."* — don't try
  cell-encoding BP again.
- `RESEARCH_NOTES_11.md`: vol-11 didn't reach 467/469; best Python
  backtracker score 297 < vol-9 cold-start 308. Engineering throughput
  is the binding constraint.
- `05_Joe_pruning_method_thread.md`: *"if the backtracker spends N
  iterations at depth > T without finding the next placement, prune
  back to depth T and restart."* — depth-threshold tied directly to
  this empirical schedule.
- `11_Inner_14x14_thread.md`: *"Carlos Fernandez: 13×13+border in 4
  minutes without hints"* — Innovation C is plausible at 14×14 interior
  with a fixed border.
- `09_Blackwood_solver_thread.md`: 469 parameter set documented verbatim;
  schedule `heuristic_sides=[17,2,18]` + `break_indexes_allowed=[…]`.
- `AUDIT_REPORT.md`: *"Add `domain_bits: Vec<u64>` (length `n_pos *
  words_per_pos`) to SearchState, populated alongside the existing
  `Vec<Vec<u32>>` — both representations coexist initially."* — exact
  plan to follow.

### Operating constraints
- Hourly cron `/loop` set (job 122d151e, fires at :07 each hour).
- Read-only on vol-7..11 artifacts; new files go in `output/v12_*`,
  `scripts/v12_*`, `crates/propagators/` (NS-1), and the engine.
- All commits to `develop` with `Co-Authored-By: Claude Opus 4.7 (1M
  context)`.

## Session log

### 2026-05-12 13:12 — start (after reading)
Set up cron `122d151e` for hourly check-ins. Read MEMORY.md linked entries
+ RESEARCH_NOTES_11 (full) + community-mining 05/09/11 + AUDIT_REPORT.md
+ propagators/lib.rs + solver-engine wiring. Engineering track 1 (NS-1)
is highest-leverage / lowest-risk; starting there now.

</content>
</invoke>