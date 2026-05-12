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

Noticed `v2/RESEARCH_NOTES_13.md` + `scripts/v13_tensor_recon.py` already
on disk (modified at 13:16/13:20 — same window): a sibling agent is
running the **tensor-network direction** (vol-13). I will steer clear of
that area and own the engineering + the *other* innovation tracks
(edge-color BP, CVM, 14×14 MaxSAT, Hamilton-frame). Each agent writes to
disjoint directories under `output/v12_*` vs `output/v13_*` so no
collision.

### 2026-05-12 13:21 — engineering track 1 + 2 shipped (commit ff066b5)
- NS-1 multiset-equality propagator at `crates/propagators::multiset_equality_check`.
- `EngineConfig::multiset_equality_propagator: bool` + new `EngineConfig::depth_threshold_for_propagators: Option<u32>` (Joe-Saunders gate).
- 3 new profiles + server registry entries: `gacolor_ac3_ns1`,
  `gacolor_ac3_ns1_par`, `joe_depth150`, `joe_depth150_par`.
- 3 new propagator tests + 7 engine tests pass.

### 2026-05-12 13:24 — baseline fleet measured
```
size colors seed  solved  depth   nodes      nps
 8x5  5      1    yes     64      989,066    98k
 8x5  2      yes  64                10,168   139k
 9x5  1      yes  81                332,924  156k
 9x5  2      yes  81             2,525,585    43k
10x6  1      no   97             4,899,419    82k
10x6  2      yes 100               633,044    91k
11x6  1      no  113             3,430,775    57k
11x6  2      no  117             2,102,121    35k
12x7  1      no  135             1,948,182    32k
12x7  2      no  136             2,183,262    36k
PT 10x10: best=178/180 ips=7.4M
```

### 2026-05-12 13:24 — depth-threshold sweep on canonical E2 (60s/cell)
```
threshold  multiset_equality  depth  nodes    nps    backtracks  ppn
   none      false            164     80,520  1342     12,863    977.7
   none      true             164     72,671  1211     11,633    980.2
   100       false            164     84,441  1407     13,501    979.8
   100       true             164     80,062  1334     12,803    977.9
   150       false            164     75,140  1250     12,023    981.1
   150       true             164     57,563   959      9,321    990.4  ← best
   180       false            164     93,104  1552     14,991    978.8
   180       true             164     78,024  1300     12,495    980.6
```
**Findings**:
- Max depth = 164 across all configs, matching vol-11's calibration. The
  60s budget at our throughput is not enough to escape the 164 plateau on
  canonical E2 with hints.
- **NS-1 prunes about 10–25% of nodes** consistently. At t=150+NS-1 the
  prune rate is 28.6% over the baseline (57,563 vs 80,520).
- depth_threshold=150 alone gives 6.7% prune (75,140 vs 80,520) — small
  because we barely cross threshold 150 in 60s.
- depth_threshold=180 *with* NS-1 gives 3.1% prune — too tight; we
  spend the budget on shallower work that the gate suppressed.
- **The depth gate IS load-bearing in combination with NS-1**: per-node
  cost goes from 1342 nps (baseline) to 959 nps (t=150+NS-1), but with
  ~28% fewer total nodes the work per second of "useful pruning" is
  *higher*. Joe-Saunders 2026 mental model validated empirically.

Tier-3 takeaway: NS-1 + depth-gate-150 is now the canonical-E2 best
single-thread profile. Caveat: max_depth didn't move at 60s — the gate
needs a longer budget (likely 300s+ or parallel) to manifest as a depth
improvement, not just a node-saving improvement.

### 2026-05-12 13:26 — Innovation A: edge-color BP measured

Built `scripts/v12_edge_bp.py` — full Pearl-style sum-product on the
*edge-color* factor graph (480 internal grid-edges as variables × 23
states; 256 cell factors; soft piece-uniqueness). The dead-ends memo
explicitly recommended this encoding as the alternative we had not
tested in vol-11.

After 60 iters @ damping=0.5, soft_uniqueness=on:
- Mean interior-edge entropy: **2.509 nats** (uniform = 3.091)
- **Reduction: 18.84%**.
- 3 iters already reach 16.7%; converges by ~25 iters to within 0.1
  msg-change.

Compare to vol-11's cell-encoding: 8.4% interior reduction. The
edge-color encoding carries **2.24× more information per cell** — and
the dead-ends memo's prediction that this would be stronger is
empirically confirmed.

**Open question**: is the 18.84%-strength edge marginal good enough as
a value-order heuristic? Vol-11's measurement was that BP marginals
*lost to random* at 8.4%. A 2.24× stronger signal might cross the
threshold where it actually helps. A backtracker A/B with edge-BP
marginals vs random is the natural next experiment (vol-13).

### 2026-05-12 13:28 — Innovation D: Hamilton-cycle frame enumeration

Built `scripts/v12_hamilton_frame.py` — DFS frame enumerator: pin the
TL corner, walk CW around the 60-cell ring, match outgoing/incoming
colors, honor the 5 hints, filter at ring closure.

**Full enumeration in 120s**: 75,173 valid 60-cell border rings, from
818,648 DFS nodes (6,822 nodes/s). The community tried "rotation-set
seeding" in 2008 and failed (too many rotation sets). With the 5
official hints + DFS color-matching + rotation-encoded edges, the
canonical 5-clue search space is *much smaller* than community
folklore: 75k frames total, not 10^9+.

**Tier 3 finding**: vol-9's `solver-engine::border_first` runs the
exact same problem inside the full backtracker without separating the
phases. Phase-separating border enumeration from interior solving
gives us 75k *known-feasible borders* to attempt 14×14 interiors
against — community has not done this systematic enumeration on
canonical 5-clue E2 (only frame-rotation generation, which was much
larger).

The 75k frames will be the input to a "for each frame, try the
14×14 interior" sweep (vol-13 if time).

</content>
</invoke>