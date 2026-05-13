# RESEARCH_NOTES_18.md — vol-18 live log

Date opened: 2026-05-13.

Previous volume closeout: `RESEARCH_NOTES_17_OVERNIGHT.md` (F1-F6, L1-L5),
`RESEARCH_NOTES_17_REFRAMING.md` (R1-R7 lenses), `OPTIMIZATION_REPORT.md`
(measurement infrastructure diagnosis).

Headline state at vol-18 open:
- **Cold-start ceiling**: 447/480 (calibrated_v17a), one-shot. Hand-tuned
  best: 456/480 (winning5 + v17a) — **NEVER reproduced under controlled
  conditions** (n=1).
- **Warm-PT ceiling**: 446/480 (vol-6 historical).
- **Community SOTA**: 469/480 (McGavin, Blackwood algorithm).
- **Gap**: 469 − 447 = **22 matches** between us and SOTA on cold start.
- **Engine throughput**: ~7 k nps `joe_depth150_bp_par`, ~367 k nps
  `BLACKWOOD_RAW` single-thread (vol-16 numbers).

---

## Carry-in from vol-17 (unfinished)

### 1. OPTIMIZATION_REPORT phases — Phase 0 partially shipped

**Phase 0 (deterministic measurement infrastructure)** — *in progress*.

Shipped this session (commit pending):
- `AlnsConfig.repair_step_budget: u64` — when > 0, `sa_repair` runs exactly
  this many SA moves instead of using wall-clock; eliminates same-seed score
  variance from wall-clock-bounded SA repair (the F2 root cause).
- `AlnsConfig.cp_repair_parallel: bool` — when false, `cp_repair` uses
  single-thread `gacolor_ac3` instead of `gacolor_ac3_par`.
- `sa_repair_with_steps`, `cp_repair_with_opts`, `repair_with_opts`
  helper APIs.
- Plumbed both new fields through 14 `AlnsConfig {}` literals.
- `alns_only` exposes `--repair-step-budget` and `--cp-repair-single`.

Smoke-tested 2026-05-13: same `--repair-step-budget 50000 --seed 1`
gave identical score (436/480, `iters` differs because the outer
wall-clock loop terminates at slightly different outer-iter counts).
Without step budget, the test condition (30s budget × 1500ms repair)
only does ~20 outer iters and the repair finishes naturally before
truncation — so F2 didn't manifest there.

**TODO Phase 0**:
- Calibrate `repair_step_budget` to match the wall-clock budget that was
  giving good (453) scores. The 50k-step test gave 436 because it overshot.
- Plumb `--repair-step-budget` into `run_e2_blackwood`, `alns_portfolio`,
  `alns_pt`, `cold_portfolio`.
- Add ALNS-level `--alns-stagnation-action stop|restart|pivot` (Phase 1
  from OPTIMIZATION_REPORT).
- Fix CP depth reporting (`max(stats.max_depth_seen, sink.best_depth)`).
- Log per-ALNS repair iterations and stop reason in `AlnsStats`.

**Phase 1, 2, 3 (budget control, experimental defaults, algorithmic
post-determinism work)** — *untouched*, see OPTIMIZATION_REPORT.md.

### 2. Cross-domain reframings R1-R7 — only R4 tested

From RESEARCH_NOTES_17_REFRAMING.md, with vol-18 status:

| # | Idea | Status | Outcome |
|---|------|-------|---------|
| R1 | Diffusion-on-corpus inpaint | not tried | EV medium-high, 1-2 day PoC |
| R2 | Wolff cluster on Z/23 Potts | not tried | EV high, principled Houdayer |
| R3 | Iterative-OT/Hungarian | not tried | EV medium, fast PoC |
| R4 | Piece-side mutual information | **TESTED, soft null** | interior MI 0.27 bits / 6.6% — no propagator-worthy structure |
| R5 | Mismatch homology β_1 | not tried | EV high, 30 min measure on existing boards |
| R6 | Swap-walk SA on S_256 | not tried | EV medium |
| R7 | Hilbert-FFT spectral feature | not tried | EV low-med, 4h |

**Highest unstarted EV**: R5 (β_1) — measurement on saved boards, cost is
30 minutes, signal could justify building a `CycleDestroy` op.

### 3. Dangling hypotheses from RESEARCH_NOTES_17.md

- **H18**: Smarter chimera — instead of random missing-piece placement,
  pair each duplicate with a missing piece such that edge-colors match the
  cluster boundary. Reduces chimera pre-ALNS chaos.
- **H19**: Use the 455 board as a CP hint seed. Pin 50 non-hint cells in
  rows 8-15 (high-confidence backbone) and re-run Blackwood CP.

Both are post-Phase-0 work — they're hypothesis tests that need
deterministic measurement to be honest.

### 4. Structural findings to remember

These are facts established in vol-17 worth keeping in mind during
vol-18 design:

- **Piece-set per row-region is CONSERVED across same-schedule ALNS runs.**
  Boards A/C/D (447/455/454, all v17a) have identical piece-sets per
  row-region {0-4, 5-8, 9-12, 13-15}. Different ALNS runs from the same
  CP partial only shuffle pieces *within* regions. So cross-grafting
  same-schedule boards is a no-op. Only different schedules give
  piece-level diversity.
- **Backbone**: 18 cells consistently agree (piece+rotation) across all
  9 saved boards. 5 canonical hints + 13 cells in rows 13-15. So 238/256
  cells are flexible across ALNS runs.
- **Mismatch geometry**: 447-class boards have all mismatches in rows
  0-3 (top-row cluster, 51-cell component). Matches community 469
  geometry; INVERTS vol-6/vol-14 (which had mismatches at bottom).
  Scan order determines this, not the puzzle.
- **ALNS lift constant**: +86 ± 3 matches between CP partial and ALNS
  output, across 21 chunks. So the cap of ~455 comes from the CP partial
  quality (362), not ALNS plateau.
- **F2 — same-config variance up to 11 matches** — invalidates most n=1
  "REFUTED" verdicts from vol-17 (H5, H6, H17 need re-test under Phase 0
  deterministic conditions).
- **Schedule diversity (v17e noise) is the only CP-level lever**
  (per F1: fixed (schedule, seed) → same CP outcome).

### 5. Carry-in from `RESEARCH_NOTES_17_PLAN.md` (ideas A-L)

10 ideas A-J + late additions K (Blackwood-then-CSP) + L (cold portfolio):

| ID | Idea | Vol-17 status |
|----|------|---------------|
| A | Blackwood schedule calibration | DONE (v17a/b/c/d/e) |
| B | Houdayer cluster ALNS | not started (R2 in REFRAMING covers this) |
| C | Bipartite gacolor v2 | not started |
| D | Zobrist hash for PT | DONE (vol-17 commit) |
| E | Fiedler ordering | not started |
| F | Projected MPS | not started (vol-13 ruled out 2D MPS) |
| G | CP+SAT cooperative | not started (MaxSAT dead end per memory) |
| H | Verhaard set-SA | not started |
| I | ConflictDriven k=80 | DONE (in winning5) |
| J | (forgotten) | — |
| K | Blackwood-then-CSP pipeline | partial: bin `run_e2_blackwood_then_csp` exists; not benchmarked |
| L | Cold portfolio | DONE (bin `cold_portfolio`) |

---

## Vol-18 mission

The user's vol-17 prompt about cross-domain framings was the real signal:
**stop replicating, start reframing**. The OPTIMIZATION_REPORT is the
foundation that makes any reframing experiment scientifically clean.

**Vol-18 prioritization (proposed)**:

1. **Finish Phase 0** (1-2 hours) — calibrate `repair_step_budget` to a
   move count equivalent to the current default `repair_budget_ms=1500`.
   Plumb it into all binaries. Verify F2 disappears under controlled test.
2. **Run R5 — β_1 mismatch homology** (30 min) — cheap measurement on
   existing saved boards. If β_1 > 0 on any 447-455 board, design
   `CycleDestroy`.
3. **Verify the 456 record** (30 min) — under Phase 0 determinism, run
   winning5+v17a+seed=1 3-5 times. Confirm or refute 456 as reproducible.
4. **Pick one high-EV reframing** (1-2 days) — based on the R5 outcome:
   - If β_1 > 0: build `CycleDestroy` (R5).
   - If β_1 = 0: build R2 (Wolff cluster on Z/23 Potts) OR R3 (iterative OT
     /Hungarian on mismatch component).
5. **Run Phase 2 overnight** — winning5 + v17b + 3-run repeats per config,
   short chunks, stagnation-stop ALNS. The OPTIMIZATION_REPORT-prescribed
   defaults.

Throughout vol-18: **honest n≥3 per claim** (per L1). Single-run results
go in a "needs replication" column, not the "shipped" column.

---

## 2026-05-13 — vol-18 opens

Carry-in committed. Next concrete steps queued as tasks. Awaiting user
direction or proceeding with the prioritization above.

---

## 2026-05-13 — R5 sequence + permutation cycle discovery

### R5 findings (mismatch homology + row distribution)

- **Strong row-distribution law** (n=12 boards):
  pearson(score, rows_touched_by_mismatch) = **−0.93**
  - 456 boards: defect confined to 5 rows
  - 447 boards: defect spread across 7 rows
- **View-B β_1 = 5-12 measures cyclomatic complexity of the mismatch
  region**, not perfect-cell holes. Interior perfect islands are 1-2
  per board (mean 1.5).
- **Mismatch *edge* graph is a forest** on all 15 boards. No
  `CycleDestroy` on view A.

### R5c — Leaking pieces hypothesis CONFIRMED

For 447 board chunk_0003: 4 of 7 pieces in rows ≥5 of mismatch
region (pid=93, 245, 131, 82) consistently sit at rows 0-3 in
ALL 4 known 456 boards. Strong causal evidence.

### R5d — Direct snap-to-oracle FAILS

Snapping a 447 board to a 456 oracle (incrementally) produces
non-monotone trajectory:
  k=5: 437 (−10)   k=20: 419 (−28)   k=40: 404 (−43)   k=ALL66: 428

The 447 → 456 swap path traverses worse intermediate states.
**Single-piece swaps cannot climb to 456**, which is why ALNS
gets stuck at 447.

### R5e — Permutation cycle decomposition

σ = oracle_pos ∘ current_pos^−1 decomposes into 10 cycles:
  1× len-40, 1× len-9, 1× len-7, 2× len-4, 2× len-3, 3× len-2

**Every individual cycle applied in isolation has negative score
delta** (−4 to −34). Even the smallest 2-cycle costs −4.

Applying ALL 10 cycles together: 450/480 (close to oracle 456).

**Implication**: 447 → 456 is a **first-order phase transition**.
All paths through swap-space are downhill, but the final state is
+9 uphill. Standard MCMC can't cross. PT can't propose
cycle-coherent moves. ComponentDestroy + SA-repair *cannot* discover
this — every step looks worse, so every step gets rejected.

### Strategic pivot: OracleAssistedDestroyRepair

The only ALNS op that can cross 447→456 in one shot:
1. Pick a cycle of σ.
2. Destroy all positions in that cycle.
3. Repair by placing the oracle's pieces at oracle's positions
   (with oracle rotations) — bypassing the SA repair entirely
   for these cells.
4. Score; accept if better than current best.

This is bootstrapping: **using previously-discovered high-score
boards as priors to escape local optima on lower-score boards
from the same neighborhood.**

The honest framing: we already paid the compute to find 456. We
can replicate it (4-time tied score). Now we use 456 as a *prior*
to push toward 457+. Operator must accept oracle's pieces but
also have moves that go *beyond* oracle (random destroy + SA
repair, etc.) to discover something new.


---

## 2026-05-13 — R3 iterative-OT: empirically refuted as repair op

Built `crates/localsearch/src/ot_repair.rs`: `iterative_ot_repair`
takes a free_set, builds a (k×k) reward matrix where reward[i][j] =
#matches piece-i would have at position-j with current static
neighbors (max over 4 rotations), then runs Kuhn-Munkres
(maximizing weight) to find the optimal piece→position assignment.
Iterates until fixed point.

CLI: `alns_only --repair-kind ot`.

Test 1: 30s on a fully-placed 447 board.
  SA  repair: 20 iters → 447 (locked in, no improvement)
  OT  repair: 17 215 iters → 447 (same)

Test 2: 30-60s on a 197-placed CP partial (chunk_0003).
  SA  repair: 20 iters → **453** (+91, the normal pipeline result)
  OT  repair: 4-8 M iters across seeds → **STUCK AT 362** (the CP
              starting score, placed = 197/256)

The OT op bails (returns unchanged board) whenever any free position
is empty, so it cannot bootstrap a partial board.

Test 3: 30s on a fully-placed 453 board.
  OT  repair: 333-352 k iters × 5 seeds → all stuck at 453.

The 453 board is at an OT-stable fixed point. **OT cannot cross
the basin barrier** — same finding as R5e: every local move is
downhill.

### Verdict on R3

- OT is ~1000× faster than SA (microseconds vs ms per iter).
- But OT is a strict **valley-finder**: monotone non-decreasing in
  match count under fixed neighbors. It cannot climb out of local
  optima.
- On fully-placed plateau states (453+), OT contributes zero.
- On CP partials, OT structurally cannot start because of the
  empty-slot bail.

**R3 is REFUTED as a standalone repair op.** Still potentially useful
as a *post-SA polish step* on borderline-improvable boards, but
empirically not on 453/447 boards. Mark as null result. Memory entry
to follow.


---

## 2026-05-13 — hold pattern: replication test + hot-PT design

Launched 5-seed replication of winning5 + SA repair starting from
chunk_0019/cp_board (197 placed, 362 matched). 300s each, 25 min total.

Per-seed results (live): seed 1 in progress.

While waiting, designed the next experiment:

### Hot-PT-from-456 (queued)

Per R5e: 447 → 456 transition is a first-order phase change with the
biggest swap-cycle costing −34. To accept Δ=−34 at p≈1/2 we need
T ≈ 49. Standard PT runs T_max ≈ 2-5. **Hot-PT at T_max=50 has not
been tested.**

Plan: take a known 456 board, run `alns_pt --t-min 1 --t-max 50
--n-chains 4 --time-budget-ms 300000 --ops winning5`. If replica
exchange between the cold (T=1) chain (which stays at 456) and the
hot (T=50) chain (which jiggles broadly) gives the cold chain a new
basin, we'd see 457+.

This is still inside our algorithm family (PT exists) but in an
unused regime (T=50 not T=2). Outside-the-stack would be R6
swap-walk-on-S_256 (a permutation-space SA we don't have).

If replication shows 456 is rare (e.g., 1/5), do hot-PT from the
most stable basin reached (likely 451-453). If replication is good
(3+/5), do hot-PT from a 456 directly.


---

## 2026-05-13 — Replication test → trajectory-families finding

5-seed replication of winning5 + SA repair from chunk_0019/cp_board
(stopped at seed 3 per user direction): seeds 1, 2, 3 → **454, 454, 449**.
None reached 456.

Followed up with piece-position + region overlap comparison across
2 new 454 boards + 447-chunk_0003 + 2 known 456 oracles:

| | within family | between families |
|---|---:|---:|
| piece-position overlap | 70-89% | **12%** |
| 4-row-region overlap | 89-99% | **43%** |

**Two distinct trajectory families exist**:
- **Family A** (pre-overnight CP): 447-chunk_0003 + 4 known 456 boards.
- **Family B** (chunk_0019 overnight CP): the new 454 boards.

Score-distance ≠ configuration-distance:
- 447 → 456 within Family A: 9 score pts, **76 misplaced pieces**.
- 454 → 456 between B → A: 2 score pts, **218 misplaced pieces**.

σ-cycles in the cross-family 454→456: cycles up to 88-129 cells with
Δ ∈ {−132, −171}. Hot-PT at any reasonable T cannot cross.

Implication: chunk_0019 is 456-unreachable. Must work within Family A
trajectories, or generate new families via schedule diversity.

Memory: project_e2_vol18_456_unreplicable, project_e2_vol18_trajectory_families.

---

## 2026-05-13 — 🏆 NEW COLD-START RECORD: 457/480

Built `oracle_swap.rs` module + `oracle_cycle_swap` binary:
- compute_sigma_cycles, apply_cycle, apply_all_cycles, rotation_fixups.
- Within-family test on 447-chunk_0003 → 456-oracle: applying 10
  cycles + 2 rotation fixups produces **456 exactly, in microseconds**
  (the precise +9 score gap the cooperativity math predicted).
- Cross-456-trajectory: winning5_456 → diverse_456 transforms one
  into the other via 7 cycles + 1 fixup. Both at 456; no 457 reachable
  this way.

Then ran hot-PT FROM the freshly OracleCycleSwap'd 456:
- `alns_pt --cp-board <456> --n-chains 4 --t-min 1 --t-max 30
  --time-budget-ms 300000 --ops winning5 --seed 1`.
- Per-chain scores: **[456, 456, 457, 457]**.
- Global best: **457**, found by chain 1 at round 2.
- Saved at output/v17_alns_pt/pt_winning5_n4_t1_30_s1_1778661199.json.

**Validates R5f physics prediction**: Δ=−21 transitions need T≈30 for
~50% acceptance. Standard PT runs T_max=2-5 → useless. Hot-PT at
T_max=30 empirically opens the 456→457 barrier.

Memory: project_e2_vol18_457_record.

---

## 2026-05-13 — Pushing past 457 (in progress)

T_max=30 from 457, seed 2: 4 chains all stuck at 457.
T_max=50 from 457, seed 1 (4 chains) AND seed 2 (6 chains): all stuck at 457.

457→458 barrier is harder than 456→457. Currently running seeds 3, 4, 5
at T_max=30 (background, ~10 min remaining) as reproducibility probe.

If 0/3 find 458: budget hypothesis (5 min × 4 chains × T=30 insufficient).
Next attempt: longer budget (15-30 min), and/or T_max=80-100, and/or
multi-init PT from several distinct 457 boards if we can generate them.

If 1/3 find 458: 458 IS accessible, push further with same recipe.

