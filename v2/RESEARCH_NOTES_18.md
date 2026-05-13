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
