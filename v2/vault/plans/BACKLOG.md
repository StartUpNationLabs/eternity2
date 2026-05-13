# BACKLOG — canonical T-list

**Discipline**: Any `unbuilt` item with `since` ≥ 3 volumes back must be picked or marked `wont-do` at next vol-open.

Status tags: `unbuilt` | `in-progress` | `built` | `refuted` | `wont-do` | `partial`

---

## Algorithm builds (engine-level)

### `learned-value-order-gate` (vol-26 T1) — status: `built` — vol-26 (2026-05-13)
Imitation-learning model + Rust↔Python stdio bridge for `ValueOrder::Learned`. Trained on 10k synthetic 6×6/5c puzzles (~360k state-target tuples), 53k-param 2-layer grid GNN, 5 epochs CPU. **Gate FAIL on spec, PASS on substance**:
- Coverage (a): 200/200 vs 200/200 — PASS.
- Median node ratio (b): 0.0018 (≈ 540× reduction) — PASS (≤ 0.80 required).
- MRV-failed solved (c): 0 (MRV had zero failures at 6×6/5c within 5s) — FAIL on technicality.

Wall-clock: 56× SLOWER median (609ms vs 11ms) because of stdio JSON + Python torch overhead.

Substance is unambiguous: the model has internalised the expert search trajectory and reduces engine nodes ~540×, but the bridge eats the win. See [[learned-value-order]] for full table + analysis. Vol-27 unblocks via in-process inference (ONNX / PyO3 / hand-rolled forward).

### `bridge-overhead-elimination` (vol-27 T1) — status: `built` — vol-27 (2026-05-13)
Replaced vol-26's stdio Python bridge with in-process `ort = 2.0.0-rc.10` ONNX inference. Wall-clock median per puzzle 11→2 ms (5.5×), max 560→11 ms (50× tail-latency win), 163/200 puzzles outright wall-clock win. The 540× algorithmic compression from vol-26 now surfaces as a wall-clock win. See [[learned-value-order]] "Vol-27 measurement" section.

### `learned-gate-at-stress-budget` (vol-27 T2) — status: `built` — vol-27 (2026-05-13)
Took a sharper path than the planned 7×7 retraining: retested at 6×6/5c with `--budget-ms 100` so MRV's tail-latency outliers become failures (16/200). Learned solves 200/200 → condition (c) "MRV-failed solved by Learned" gives 16/16 perfect recovery. **Gate PASS on all three conditions.** Equivalent methodology to changing puzzle size; cheaper. See [[learned-value-order]].

### `learned-variable-size-cross-domain` (vol-28 T1) — status: `partial` (arch shipped) / `refuted` (cross-domain transfer) — vol-28 (2026-05-13)
v2 model architecture shipped (position-relative GNN, size-agnostic + piece-count-agnostic, ~63k params, ONNX export works at 6×6 and 16×16). Trained to 97.3% val_acc on 6×6/5c. **At canonical 16×16/22c the model is CONFIDENTLY WRONG**: under `joe_depth150_bp` profile, max depth regresses from 165 (baseline) to 57 with v2 Learned. Even at its own 6×6/5c distribution v2 coverage drops 200→186/200 with median nodes 36→19129 — train/inference distribution mismatch (training negatives filtered by border + neighbour edges only, but engine asks the model to score the bitset-domain-pruned candidate set). Two root causes: (1) candidate-set distribution gap; (2) color-embedding cardinality (only 6 of 24 slots saw gradient at training). See [[learned-value-order]] "Vol-28 measurement" section.

### `learned-16x16-trained` (vol-29 T1) — status: `built` — vol-29 (2026-05-13)
Trained v3 model on 20 canonical-E2 trajectories × 60s = ~3300 samples (vol-28's distribution-match fix). Val_acc 94.55% at plateau. **Canonical gate PASS at match condition**: Δ=−1 vs `joe_depth150_bp` baseline (164 vs 165), with −35% nodes and −37% backtracks at same wall-clock. Strict-beat condition not met (and structurally cannot be under imitation). Vol-28's collapse (Δ=−108) was a distribution-gap problem, not architectural. See [[learned-value-order]] "Vol-29 measurement" section.

### `learned-16x16-long-train` (user-Q vol-29) — status: `built` (flavor 1) — vol-30 T2 (2026-05-13)
Vol-30 T2 shipped flavor 1 (long imitation): captured 100 canonical-E2 trajectories × 60s (parallel=4, ~25 min wall), trained v3b (hidden=64, 30 epochs) and v4 (hidden=128, color_emb=24, 50 epochs). **Result: all three models (v3, v3b, v4) hit depth 174 under LearnedOnTies — the +9 lift is invariant**. More data + bigger model gives 47% fewer nodes at iso-depth (v4 vs baseline under full Learned) but does NOT push past +9. Confirms imitation ceiling at the teacher. Flavor 2 (RL self-play) still unbuilt; only direction that can structurally beat the imitation ceiling.
User request: "for the sake of science, train a 16×16-specific model for a long time and use it for a while". Distinct from vol-29 T1 (which uses imitation only). Two flavors worth trying:
1. **Long imitation**: 1000+ seeds × 60s capture (~16 hours wall-clock with parallelism), 100+ training epochs, beefier architecture (hidden=128-256). Tests whether the vol-29 ceiling is data/compute-bound or fundamentally limited by the imitation framing.
2. **RL self-play** (the only thing that could beat the engine, since imitation has a fixed ceiling at "engine's own performance"): train via PPO/REINFORCE where reward = max_depth reached. ~1 week build + many days of training compute. Different vol entirely (`vol-30+ if vol-29 fails informatively`).
Honest expectation: long imitation hits a ceiling at "engine performance on its own data", maybe within Δ=+1..+5 of the baseline. RL would be the meaningful path to beating the baseline.

### `learned-on-ties-hybrid` (vol-30 T1) — status: `built` — vol-30 (2026-05-13)
**First Δ > 0 from ML at canonical scale.** EdgeBpMarginals first, then rerank top-k tied candidates (within EPS=0.05 BP-score) with Learned. Depth 165 → **174** (+9) at 60s budget, 166 → 174 (+8) at 5min budget. Reproducible (engine deterministic given seed=1). EPS + MAX_K tunable via env vars. See [[learned-value-order]] "Vol-30 measurement" section.

### `learned-on-ties-alns-postfill` (vol-31 T1) — status: `built` — vol-31 (2026-05-13)
Shipped `canonical-eval --dump-partial PATH`. Compared baseline-165 vs LearnedOnTies-174 partials through two recovery pipelines:
- Weak (alns_only winning5 5 min): 426 → 436 (+10 score, seed=1; baseline reproducible at seed=2 → 425).
- Strong (pt_e2 8-rep + Houdayer + kicks 15 min): 437 → 445 (+8 score).

**First ML-driven score lift on canonical 5-clue 16×16 E2**, robust across pipeline strengths. The lift comes from the better starting partial (303 vs 280 initial edges); strong pipeline preserves but doesn't amplify (PT-174 hits 443 at round 5, plateaus at 445 by round 25). 445 is not the 457 record (which came from a lucky basin discovery, not iso-budget compute). See [[learned-value-order]] "Vol-31 measurement".

### `learned-on-ties-basin-escape` — status: `unbuilt` — since: vol-31
Combine vol-31's LearnedOnTies-174 partial with vol-22's basin-escape recipe (bound-ascent + Hungarian + ALNS over hours). Does the better starting basin let basin-escape find a >457 basin? Vol-22's 457 came from a specific basin found by chance; LearnedOnTies-174 might give access to a different basin family. ~1 day to wire + overnight run.

### `learned-on-ties-long-pt` — status: `unbuilt` — since: vol-31
Run pt_e2 from LearnedOnTies-174 at 1-2 hour budget (vs vol-31's 15 min). Does the 445 plateau open up with more compute, or is it a real ceiling? Cheap compute, overnight job.

### `learned-on-ties-hyperparam-sweep` — status: `unbuilt` — since: vol-30
EPS ∈ {0.01, 0.02, 0.05, 0.10, 0.20} × MAX_K ∈ {4, 8, 16, 32}. ~5 min compute total at 60s/cell. Might lift past +9. Tunable in current code.

### `mcgavin-prune-restart` — status: `built` — vol-23 (2026-05-13)
Built after 8 vols of deferral. Engine: `SolveOpts.batch_hint_application: bool` lets the engine pin DFS-derived hint sets without false-positive wipeouts. Driver: `crates/bench-audit/src/bin/prune_restart.rs`.

**Empirical (vol-23)**: validated as CP-deepener (cold-start round 1→2 lifts depth 27→152 / score 23→297). But UNDERPERFORMS vanilla cold-start ALNS as a score-maximizer (424 vs 430-450 batch median) because CP fills in FirstSolution mode, taking the first valid completion not the best.

Score lift estimate (1-2 days, +5..10) was wrong in spirit: the CP-deepener does lift CP depth dramatically, but post-ALNS the score is below baseline. See [[prune-restart]] for the empirical detail and `score-optimizing-cp` (new entry) for what would close the gap.

### `pt-tabu-zobrist` — status: `wont-do` — since: vol-17, resolved: vol-24
**Aged 5 volumes; resolved at vol-24 open.** Vol-22 measured PT plateaus at 442/480 on the 440/469 basin across 60s/5min/15min/30min budgets — saturation is the binding constraint, not chain-drift / cycling. Tabu only helps if PT *could* break the saturation gap, which the budget-scan data refutes. Mark `wont-do`; revisit only if a new mechanism (e.g. stronger repair operator) raises the plateau enough that anti-cycle would matter.
- See `concepts/pt-tabu.md` (kept; status updated)

### `joe-2019-sat-postprune` — status: `wont-do` — since: vol-14, resolved: vol-24
Aged 10 vols. ~1-week build to replicate Joe's 11-hour SAT solve on a 2-weeks-of-Blackwood pre-pruned domain. No clear path from here to canonical 5-clue 480 that doesn't already require the upstream Blackwood pre-prune (which we don't have). Mark `wont-do`; the gap-closer we actually need is `score-optimizing-cp` (active vol-24 binding).

### `piece-orbit-as-atom` (N9 from vol-20) — status: `wont-do` — since: vol-20, resolved: vol-27
**Aged 7 volumes; resolved at vol-27 open.** 10 fungible pieces out of 256 represent < 4% of the search space; even a perfect orbit reduction wouldn't materially affect node counts on canonical 16×16. The vol-26 ML result demonstrates that the leverage on E2-family puzzles is in better value-ordering (540× node reduction), not in tightening the orbit/atom representation. Mark `wont-do`; do not revisit unless a different decomposition shows it could matter for the residual hard region.

### `multi-cell-bound-ascent` (vol-22 T3) — status: `unbuilt` — since: vol-22, deferred at vol-31 open
3-cycle and 4-cycle moves in bound-landscape, not just 2-swaps. Plateau at bound 470 might break. **Vol-31 uses existing ALNS as a black-box recovery layer for the depth-174 partial; this item would build NEW ALNS ops which is orthogonal. Defer; revisit after vol-31 score-axis result.**
- See `concepts/bound-ascent.md`
- Est. 1 day

### `multi-cell-bound-ascent` (vol-22 T3) — status: `unbuilt` — since: vol-22
3-cycle and 4-cycle moves in bound-landscape, not just 2-swaps. Plateau at bound 470 might break.
- See `concepts/bound-ascent.md`
- Est. 1 day

### `bound-floor-alns-with-per-step-check` — status: `partial` — since: vol-22, deferred at vol-27 open
Vol-22 T1 was the per-RUN version (null). Per-STEP version requires modifying ALNS internals. **Vol-27 scope is ML-axis; defer to a future ALNS-focused volume.**
- See `concepts/bound-ascent.md`
- Est. 1-2 days (invasive)

### `kissat-rc2-maxsat` (vol-22 T3, user-Q) — status: `wont-do` — since: vol-22, resolved: vol-28 open
**Aged 6 volumes; resolved.** The bound-axis hasn't produced a record-breaking lever in vols 21-27 (relaxed-bound found basin ceilings but the ALNS recovery undoes every step; bound-ascent reaches 473 then collapses). Even an exact joint bound would tell us "we're at the ceiling" — a diagnostic, not a lever. Mark `wont-do`; revisit only if a future bound-axis result re-motivates exact computation.

### `score-optimizing-cp` — status: `built` (route b) — vol-24 (2026-05-13)
Vol-24 shipped route (b): branch-and-bound CP with edge-match objective. `SolveOpts.objective: Option<Objective>` field; engine tracks `matched_count` + `decided_edges` incrementally; prune at `matched_count + (total - decided) ≤ best_score`. RootSplit parallelism uses shared `Arc<AtomicU32>` cutoff + max-by-score aggregation.

A/B on vol-23 round-2 partial (184 pinned, score 297):
- FirstSolution CP-fill: 412/480 (0.2s, vol-23 reproduce).
- **MaxScore B&B CP-fill: 419/480** at 300s. +7 vs FirstSolution.
- Still < 424 (ALNS-fill from same partial) because CP-fill is a constrained sub-problem.

Route (a) MaxSAT remains `unbuilt`, blocked on `kissat-rc2-maxsat`. Route (b) handles the prune-restart gap; route (a) would give exact joint bound (different use case).

Concept page: [[score-optimizing-cp]] with full A/B table and open questions.

---

## Search / exploration

### `cooperative-pair-swap` (vol-21 T2) — status: `wont-do` — since: vol-21, resolved: vol-24
Aged 3 vols. Vol-20 `cycle_scan` already enumerated K=3,4,5 cycles on the 457 basin and confirmed operator-lock through K=5. The K=3-with-shared-endpoint variant is a strict subset of those moves (3-cell cycles ARE the 3-cycles enumerated). Vol-21 Python prototype found zero useful pairs. Mark `wont-do`; the unblock is non-local high-K moves (basin-escape recipe), not finer K≤5 variants.

### `color-relabel-search` (vol-21 T4) — status: `wont-do` — since: vol-21, resolved: vol-24
Aged 3 vols. Color relabel is score-preserving (a π ∈ S_23 permutation of colors maps a board to an isomorphic board with identical edge-match count), so it cannot raise our 457. Hypothesised benefit was reshaping heuristic rankings during search, but vol-17 calibrated_v17a already showed the BP+schedule lens dominates color-blind heuristics. Mark `wont-do`; keep `concepts/color-relabel.md` page.

### `forced-perturb-meta-op` (vol-21 T6) — status: `wont-do` — since: vol-21, resolved: vol-24
Aged 3 vols. Vol-20 `basin_hop` at k=1,4 went nowhere; vol-22 basin-escape recipe (bound→Hungarian→ALNS) is the actually-validated big-k move and is already the dominant cold-portfolio operator. Generic Δ=-k jolts into PT chains add stochasticity without the bound-guidance that made vol-22 work. Mark `wont-do`.

### `diverse-457-search` (vol-21 T5) — status: `partial` — since: vol-21, deferred at vol-27 open
"Lottery" for finding non-byte-identical 457s. Vol-22 didn't run it; instead the basin-escape recipe found different >457-ceiling basins. Still valuable as separate axis. **Vol-27 scope is ML-axis; cheap overnight job, can run any time but not blocking.**
- Est. 0 build, overnight compute

### `bound-ascent-then-blackwood-cp` (vol-22 T2) — status: `wont-do` — since: vol-22, resolved: vol-29 open
**Aged 7 volumes.** Composes vol-22's bound-ascent (which collapses on ALNS recovery — vol-21/22 measurements) with vol-15's Blackwood (which has structural depth-wall, see [[blackwood-layered-depth-wall]]). Both components have known refuted modes; composition unlikely to escape either. Mark `wont-do`.
Use bound-ascent's high-bound edge structure as VALUE-ORDER for Blackwood CP starting from canonical hints. Most novel composition.
- Est. 1 day

### `gap-recording-instrumentation` (vol-22 T4) — status: `wont-do` — since: vol-22, resolved: vol-30 open
**Aged 8 volumes; resolved.** Deferred at vol-23, vol-24, vol-25, vol-27, vol-29 with the same reason: diagnostic-only, no record lever. Five deferrals = wont-do per discipline. If future ALNS-axis work needs this telemetry, add it then as a 1-evening side-job.
Add gap-recording to every ALNS/PT save. Cheap. Long-term diagnostic.
- Est. 1-2 hrs

### `overnight-alns-pt-saturation` (vol-23 T1) — status: `in-progress` — since: vol-22
PID 66809: 8h hot-PT on the 440/469 basin. Started 2026-05-13 13:59 CEST.

### `batch-basin-recipe` (vol-23 T4) — status: `in-progress` — since: vol-22
PID 66953: 100-seed batch of bound→Hungarian→ALNS recipe. Started 2026-05-13 14:00 CEST.

---

## Research / measurement

### `tight-joint-bound-survey` — status: `unbuilt` — since: vol-22
Once `kissat-rc2-maxsat` works: measure joint bound for K=20, 40, 60-cell clusters on our 457 and the 440/469 basins. Tells us how tight the relaxation is.

### `persistent-homology-search-trajectory` (N-EXOTIC-1, vol-21) — status: `wont-do` (provisional) — since: vol-21
Compute β₁ of visited-board sequence. Speculative; high build cost; no clear win path. Mark `wont-do` unless re-motivated.

### `symmetry-broken-color-gauge` (N-EXOTIC-2, vol-21) — status: `wont-do` (provisional) — since: vol-21
Color relabel is `color-relabel-search` above; the gauge framing is mathematically interesting but doesn't add tools.

### `hopfield-embedding` (N-EXOTIC-4, vol-21) — status: `wont-do` — since: vol-21
Continuous-relaxation Hopfield. Naive variants tried in literature; ours wouldn't differ enough.

### `algorithmic-information-bound` (N-EXOTIC-5, vol-21) — status: `wont-do` — since: vol-21
K-complexity gap between adjacent boards. Not actionable.

### `inverse-problem-tweak-puzzle` (N-EXOTIC-6, vol-21) — status: `wont-do` — since: vol-21
Modify puzzle until 457 improves, port back. Theoretical curiosity only.

### `hyperedge-cover` (N-EXOTIC-7, vol-21) — status: `wont-do` — since: vol-21
Different paradigm but no evidence it would beat existing CSP/SA approaches.

### `topological-obstruction-PH-filtration` (N-EXOTIC-8 / vol-21 T16) — status: `wont-do` — since: vol-21
Superseded by the gap-as-dead-end-detector finding (vol-21 concrete signal, this was speculative).

---

## Code quality / refactoring

Audit performed vol-25 (2026-05-13). Durable detail: see [[code-debt]] for the full restructure plan + line counts. Items listed in priority order.

### `extract-eternity2-time-crate` — status: `unbuilt` — since: vol-25
Move identical `Clock` impls (solver-engine, solver-naive) to a single `eternity2-time` crate. 1 h. Trivial dedup. Should ship first because every other extraction can land on it later.

### `extract-eternity2-export-crate` — status: `unbuilt` — since: vol-25
Consolidate **5 duplicated utilities** into one crate: board scoring (`bench-audit::score_board` + `benchmark::report::score_matched_edges`), Bucas URL encoding (currently buried unexported in `benchmark::report`), `DumpedBoard` JSON serialization, ASCII board rendering, report writing. 4–6 h. Highest-leverage extraction — unblocks most other refactors and shrinks every bin.

### `split-solver-engine-lib-into-5-modules` — status: `unbuilt` — since: vol-25
`crates/solver-engine/src/lib.rs` is 5 011 lines. Verified 5-way split:
- `paths.rs` (~330 lines, pure geometry, zero backlinks) — ship first
- `config.rs` (~200 lines, enums + struct)
- `schedule_builders.rs` (~410 lines, pure factories)
- `profiles.rs` (~350 lines, EngineSolver + 40 factories)
- `lib.rs` keeps SearchState + recurse + propagate_ac3 (~3 200 lines, untouched)

Internal module split only — multi-crate split rejected as overkill until a downstream consumer wants schedules/paths independently. 4 h total, each step independently shippable.

### `extract-eternity2-puzzle-io-crate` — status: `unbuilt` — since: vol-25
Hint loading (`benchmark::loader::load_puzzle_with_hints`) and CSV parsing belong with the puzzle types, not in the benchmark crate. Currently invisible to solvers from naming. 3–4 h. Blocked on `extract-eternity2-export-crate`.

### `consolidate-bin-harness` — status: `unbuilt` — since: vol-25
76 bins across `bench-audit` and `benchmark` share ~250 lines of boilerplate each (CLI parsing, puzzle load, ProgressSink, solver instantiation, report writing). Extract into `bin-common` (or `benchmark::bin_harness`). ~7K lines of copy-paste eliminated. 8–10 h. Blocked on `extract-eternity2-export-crate`.

---

## Engine perf — remaining wins

Vol-25 perf push shipped 7 fixes ([[engine-perf-hot-paths]]): joe +22.4%, BLACKWOOD_RAW +27%. These remaining items profiled but not yet shipped.

### `incremental-ac3-count-maintenance` — status: `partial` — since: vol-25
Vol-25 shipped dirty-list scoping (fix-4, commit `fd5b615`) which captured only ~3% of the headline ~22% rebuild cost — because piece-uniqueness drops mark nearly every unplaced cell dirty. Full incremental version decrements `count` at every drop site and increments at every restore. EV: ~10–15% on joe. Effort: 1–2 h with real bug risk. The dirty-list infrastructure already in place can serve as safety net for any missed mutation site.

### `restore-or-simd` — status: `unbuilt` — since: vol-25
`restore()` (lib.rs:3408–3422) ORs `wpp = 16` u64s back into a domain. `chunks_exact(2)` over u64 pairs might trigger NEON autovectorization on apple-m1. EV: 2–4%. Effort: 30 min.

### `profile-bin-use-null-sink` — status: `unbuilt` — since: vol-25
`crates/bench-audit/src/bin/profile_{joe,blackwood_raw}.rs` use `BufferSink`, accumulating 60 s of events into a Vec. `drop_in_place<BufferSink>` was 2.98% of pre-fix BLACKWOOD_RAW samples. Swap to `NullSink` for cleaner attribution in future profiling work. Profile-tooling-only; not a production win. Effort: 5 min.

### `precompute-cell-nb-info` — status: `unbuilt` — since: vol-25
`nb_info: [(Option<Position>, usize, usize); 4]` is reconstructed at every queue-pop inside `propagate_ac3` (lib.rs:3205–3210). Could be precomputed at SearchState::new. Reconstruction itself isn't a flamegraph hotspot (the time is inside the inner loop reading nb_info, not building it), so this might not move the needle. EV: 1–2%, speculative. Effort: 1 h.

### `vault-validation-of-perf-wins` — status: `unbuilt` — since: vol-25
The vol-25 fixes were validated against raw nps on synthetic 60 s probes. The meaningful metric for the research project is matched-edge score on real solves (multi-thread joe_depth150_bp_par for 5–30 min on canonical E2). Per the [[../../../../.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2/memory/project_e2_vol14_bp_null|Vol-14 BP-as-value-order REVERSAL]] memory, raw-nps wins don't always translate to score wins (CP-partial metric mid-pipeline can be misleading). Worth a one-shot validation before declaring victory. Effort: 30 min runtime + 5 min analysis.

---

## Concepts catalog (status pages)

See `concepts/` for the durable knowledge:
- `bound-ascent.md`
- `edge-grid-dual.md`
- `houdayer-cluster.md`
- `operator-lock.md`
- `prune-restart.md`
- `pt-tabu.md`
- `relaxed-bound.md`
- `basin-escape-recipe.md`
- `color-relabel.md`
- `exact-joint-bound.md`
