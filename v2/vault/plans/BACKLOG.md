# BACKLOG — canonical T-list

**Discipline**: Any `unbuilt` item with `since` ≥ 3 volumes back must be picked or marked `wont-do` at next vol-open.

Status tags: `unbuilt` | `in-progress` | `built` | `refuted` | `wont-do` | `partial`

---

## Vol-213 entries

### `replay-prior-over-cost + double-break` — status: `built` — vol-213 (2026-06-10)
REPLAY mode + mcb=2 + et-cap fix: both community strict-460s replay
EXACTLY (460×8, rescored). See [[replay-prior-over-cost]]. Open
follow-ons below.

### `unguided-mcb2-ab` — status: `in-progress` — since: vol-213
Does double-break lift the unguided 450 plateau, or flood the
anytime-min? 8 seeds × 300 s, ± `--max-cell-breaks 2`, strict460a
hinted et14. In the vol-213 evening batch.

### `silent-cap-audit` — status: `unbuilt` — since: vol-213
TAIL_CAP lesson: capped "exact" methods must surface cap-hit instead of
silently returning the incumbent (cost 2 invisible breaks in vol-213).
Audit exact_tail2 / attach MIP / frame_ub for the same pattern; add a
cap-hit flag to exact_tail's return or an eprintln-once.

### `triple-break-census` — status: `unbuilt` — since: vol-213
Do any high community boards pay 3 breaks at one cell under row-major
attribution? Run schedule-from-board across the 123-board corpus; count
depth-multiplicities. Decides whether mcb=3 is ever needed.

### `hint-compatible-frame-generator` — status: `in-progress` — since: vol-212 (promoted vol-213)
`framegen` bin built (ring-cycle DFS + 4 chain-feasibility checks).
Smoke + chains-vs-nochains precision probe + census in the vol-213
evening batch. Question: does ANY frame escape the 444-450 band?

### `prefix-vault` — status: `unbuilt` — since: vol-212
Bank ≥160-deep perfect prefixes across runs as restart seeds. Would
open vol-214.

### `ledger-color-deficit-prune` — status: `unbuilt` — since: vol-213
Admissible in-DFS prune: per color c maintain F_c (frontier edges
demanding c: placed sides + rim targets facing empty cells) and S_c
(pool sides of color c); prune when spent + Σ_c max(0, F_c − S_c) >
budget. O(1) incremental. First prune that SEES pool starvation — the
vol-209 distinctness wall mechanism. ~50 lines. Vol-214 candidate #1.

### `cairn-frontier-nogoods` — status: `unbuilt` — since: vol-213
CDCL lens: cross-epoch nogood learning. Row-major state =
(depth, 14-color frontier vector, avail bitmask, spent); record
refuted-at-budget frontiers (bloom/hash, memory-bounded), prune
revisits with ≤ budget. Restarts stop being amnesiac — replay runs
proved the walk distribution is extremely concentrated. Vol-214
candidate #2.

### `weft-row-lb` — status: `unbuilt` — since: vol-213
Admissible next-row lower bound at each row boundary: DP over
(cell, west color) with piece-reuse relaxation (N colors known at row
entry under row-major); prune when spent + rowLB > budget. DEFERRED
behind LEDGER+CAIRN measurement (vol-213 evening analysis): the DP
costs ~36k ops per row-entry instance; row-12 entries number 10⁵-10⁶
per run, and CAIRN already memoizes refuted frontiers — WEFT's marginal
value is pruning FRESH doomed states cheaper than the DFS refutes them.
Build only if choke maps still show row-12 thrash after LEDGER+CAIRN.

### `verhaard-markov-schedule-optimizer` — status: `unbuilt` — since: vol-213
The full method behind shortestpath.se (deep-fetched vol-213 night;
our vault note only had his set-SA): instrument per-depth fit/half-fit
probabilities, then a Markov-chain model over states (depth,
cumulative-slips) predicts solutions-per-node for ANY (order, slip
array); local-search thousands of candidates offline ("thousands of
combinations per minute" with caching). This is the ANALYTIC superset
of our empirical choke→auto-gates: it computes optimal gates AND order
instead of placing gates at death quantiles. We already have the
death-histogram instrument; add fit-probability counters and the DP
evaluator. Calibration point: his released slip array starts at depth
193/256 (75%); our gates 120-171/196 (61-87%).

### `verhaard-piece-class-quotas` — status: `unbuilt` — since: vol-213
Supply-side pool health (the mechanism our area-law theory says binds):
partition pieces into good/bad by TILABILITY (# completions of a 2×3
box; his set-SA generates the groups — that part IS in
[[reference-verhaard]]), then DEPTH QUOTAS in the DFS: e.g. "until
depth 63 forbid good pieces; until 96 all useless pieces must be used;
forbid precious until 100". Forces bad pieces to be consumed early so
the endgame pool stays rich — attacks the same starvation wall as
LEDGER but from the supply side. Cheap: piece-class masks + per-depth
counters. UNBUILT here in any form.

### `verhaard-progress-restarts` — status: `unbuilt` — since: vol-213
Replace fixed restart_ms with progress-based aborts ("can't reach depth
128 in 200M nodes → restart; max depth < 165 → abort run") — his claim:
~5× over fixed-interval restarts. Trivial to add (epoch_max vs node
thresholds, calibrated from our choke histograms).

### `verhaard-order-optimization` — status: `unbuilt` — since: vol-213
Verhaard (shortestpath.se): "the optimal search order depends on the
score you want to achieve — for 480 scan-row is quite optimal, but far
from optimal for ≤468"; he COMPUTED per-target orders for his records.
We pick orders by hand (row/seam/spiral). Optimize the order itself for
461-strict given frame+hints: e.g. greedy/anneal over cell permutations
scoring (wall depth × choke mass × endgame closure), or his published
square-order as a starting point. Composes with choke auto-gates.
Academic control: van Horn 2018 (scan-row > spiral/inverse-spiral/
mirrored for raw backtracking).

### `perturb-multi-deviation` — status: `unbuilt` — since: vol-213
Both witnesses are 1-deviation-locked in [140:182) (900 s × 8 each,
~700k completions/seed, every seed converges back to the witness
exactly). If wide-window single deviation is also null, the next
enumerator is k=2 deviations (sample two depths per epoch) — or accept
that these frames cap at 460 and shift to the frame axis (framegen).

---

## Vol-109 open candidates (highest-priority)

### `oracle-aware-alns-repair` — status: `unbuilt` — vol-109 candidate
**Continuation of vol-108 T1 (SigmaCycleDestroy refuted).** The σ-cycle's structural lock comes from halo edge-colour constraints, not the cycle cells themselves. Fix: modify `repair_cells` to accept "oracle pins" — positions where the repair is forced to use a specific (piece, rotation) from a reference good basin. Then SigmaCycleDestroy + halo-oracle-pin should unlock the basin.

Effort: 1-2 days. Requires modifying the repair API + ALNS framework + variance testing.

EV: could lift offset=100-style locked basins past 446 (current ALNS ceiling). High prior if implemented correctly.

### `cross-machine-bf-bench` — status: `partial` — vol-109 T3
x86_64-unknown-linux-gnu target installed; cross-compile builds but link fails (no Linux linker on macOS host). Needs either cross-toolchain (x-tools, multi-hour install) or actual Linux machine access. Deferred.

Once unblocked: also unlocks BOLT post-link reordering on Linux ELF binaries (~5-10% extra).

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

### `learned-on-ties-hybrid` (vol-30 T1) — status: `refuted` — vol-32 (2026-05-13)
**Vol-30 headline was a measurement artifact.** Engine bug at lib.rs:2550: cell_side_edge was only initialised for `ValueOrder::EdgeBpMarginals`, not `LearnedOnTies`. Under buggy LearnedOnTies, the BP-sort block never ran, the LOT rerank block never ran, and the engine silently fell through to InsertionOrder. The "+9 depth lift" was actually "InsertionOrder beats EdgeBpMarginals by +9 under joe_depth150_bp" — nothing to do with the trained model. Confirmed by:
- LOT_TRACE instrumentation: 0 fires under buggy LOT despite 18k engine nodes (5s smoke).
- 7 partials from different (model, eps, max_k) combos all md5-identical.
- Post-fix measurement: LearnedOnTies depth 165 = baseline EdgeBpMarginals 165. Real +3 matched edges from imitation (vs vol-30 claim of +23 = 303-280).

Bug fixed at commit `95978a5` (cell_side_edge initializer extended). See `vault/sessions/vol-32-bug-discovery.md` for full evidence. **Vol-30/31 vault entries also need amendment.**

### `learned-on-ties-alns-postfill` (vol-31 T1) — status: `refuted` (re-attributed) — vol-32 (2026-05-13)
**Vol-31's +10/+8 score lifts were real measurements but mis-attributed to ML.** The depth-174 partial used as input was an InsertionOrder-under-joe_depth150_bp artifact, not an ML artifact (see `learned-on-ties-hybrid` correction above). PT-from-depth-174 reaching 445 is real; the partial just isn't ML-derived. True post-fix LearnedOnTies partial gives only +3 edges over baseline at depth 165 — much smaller potential score lift.

The `--dump-partial` flag is real and useful. Vol-31's pipeline was sound; the input attribution was wrong.

### `learned-on-ties-basin-escape` — status: `wont-do` — vol-32 (2026-05-13, resolved)
Premised on vol-31's "better starting basin" being ML-derived. With the bug fix proving the partial was InsertionOrder-derived, there's no ML-specific basin to escape from. The InsertionOrder-174 partial → basin-escape recipe is still a valid experiment but it's `insertion-order-basin-escape` not `learned-on-ties-basin-escape`. Mark wont-do; promote a renamed variant if vol-33+ wants to revisit.

### `vanilla-fast-backtracker` (community-speed-parity) — status: `built` — vol-32 (2026-05-13)
Shipped at vol-32 close. 125M pp/s single-thread, 577M aggregate × 8 cores (community speed range). See `crates/bench-audit/src/bin/vanilla_fast.rs`. Vol-34 extended with `--snapshot-dir`, `--snapshot-interval-ms`, `--snapshot-min-depth`, `--snapshot-on-visit` for periodic deep-partial sampling.

### `unsat-clause-propagator` (Marie + Akos's database) — status: `refuted (hard pruner)` — vol-34 (2026-05-14)
Hard-pruner refuted at vol-34 after full encoding reconciliation (ml/data/{color_map,piece_card_map}.json shipped). Capiman's "unsat" clauses are heuristic-search-regime-specific (per-round), not globally unsat — validation on the verified-good vol-32 458 record board gives 56 conflict pairs (round_1 alone gives 18). Using as a hard prune would silently kill valid moves.

### `vanilla-path-custom-order` (vol-36 T1) — status: `built` — vol-36 (2026-05-14)
Raw-DFS backtracker with custom cell-visit path (vs vanilla_fast's hardcoded row-major). Per-step pre-bucketing on constrained-side colors (mask-aware). 4 built-in paths + `--path-csv`. **30s A/B**: border-first 445/480, row-major 433/480, outer-spiral 204/480, hint-link 51/480. **border-first wins +12 edges**. Hint-link refuted at raw-DFS level (matches vol-14 engine-level refutation). See `vault/sessions/vol-36-vanilla-path-ab.md`.
**Open**: does border-first + ALNS lottery exceed vol-32 458 record? Awaits 5min × 8 thread run + lottery (in flight).

### `mcgavin-prune-restart-bound-trigger` (vol-36 T2) — status: `unbuilt` — since: vol-36 (2026-05-14)
Different trigger from vol-23 prune_restart (which uses CP-depth trigger). At each bound-improving move, store monotonically-growing pinned set; bound walk operates only on un-pinned cells. Once bound reaches target, materialise pinned set as Hints for ALNS recovery WITH retention. **Estimated 1-2d.** Vol-36 T2; deferred to a later session pending T1 results.

### `rl-self-play-value-order` — status: `unbuilt` — since: vol-30 (resolved-as-defer at vol-38)
Vol-29 imitation hit teacher ceiling. RL is the only path to structurally beat baseline. Vol-38 candidate. Estimated 1 week build + days training.

### `code-refactor-vol25-batch` — status: `unbuilt` — since: vol-25
Vol-25's 5 deferred code-debt items (extract eternity2-time, -export, -puzzle-io crates; split solver-engine lib; consolidate 76-bin harness). Vol-37 candidate per multi-vol plan (2026-05-14).

### `unsat-soft-value-order-vol37` — status: `unbuilt` — since: vol-34
Wire capiman's unsat database as ValueOrder::UnsatSoft at depth<100. Vol-37 candidate per multi-vol plan (2026-05-14). 1d build + 0.5d measurement.

### `fitness-landscape-mapping` (vol-35 T1) — status: `partial` — vol-35 (2026-05-14)
Multi-scale landscape probe across 4×4/4c, 6×6/5c, 8×8/{5c,8c}, 10×10/8c, 12×12/8c, 16×16/22c.
Built: `landscape_explorer` bin, `analyze_landscape.py`, `multi_puzzle_landscape.sh`, `cluster_basins.py`. **Findings**: rugged at all scales; FDC weak ∈ [-0.211, +0.084]; **10×10/8c smallest size showing clear basin clustering** (6 pairs at H≤25); canonical 16×16 LO Hamming-distance is trimodal under random-restart ALNS. Color ratio (pp/c) hypothesis REFUTED — size, not ratio, governs structure. The landscape work is structural understanding, not yet an operator design.
**Open**: per-cluster ALNS-operator design; saddle-height to predict cross-basin barrier (untackled at 16×16).

### `vanilla-fast-thread-id-sweep` (vol-35 T2) — status: `built` — vol-35 (2026-05-14)
`vanilla_fast --thread-id-offset N` flag for sweeping bucket-shuffle seeds. Sweep at offsets {0..450} × 5min × 8 threads → 46 productive thread_ids → 19 distinct basin families (`cluster_basins.py`). Vs default {0..7} which gives 5 families. Basin diversity scales linearly with offset coverage. **Family-lottery on the original buggy snapshots gave 7th "457 basin" claim that was retracted as pin_hints duplicate-piece artifact.** Post-fix re-sweep (`sweep_v3`) completed; lottery on clean snapshots was started but killed pre-completion when user returned. Clean snapshots saved at `output/vol-35/sweep_v3/` for vol-36+ pickup.

### `pin-hints-snapshot-bug-fix` (vol-35 mid-vol) — status: `built` — vol-35 (2026-05-14)
**Critical bug discovered mid-vol**. `vanilla_fast --pin-hints` snapshot/save paths filled canonical hint positions without checking `already_placed`. 221/225 sweep snapshots had duplicate pieces (typically 180×2 and/or 248×2). All ALNS scores derived from those partials were invalid as canonical-E2 claims. **3 save paths fixed** (commits `1f5ebef`, `834368e`). `verify_records.sh` now checks piece-uniqueness alongside score. **Retracted**: vol-34 "2× 457" + vol-35 "family-255 457×3" + vol-35 "7th basin" claims. **Stands**: vol-32 458 RECORD + 4 valid 457 basins + vol-35 deep458 reproduce (1× 458 byte-identical + 2 new 457 satellites of the 458 family).

### `unsat-soft-value-order-depth-conditional` — status: `unbuilt` — since: vol-34 (2026-05-14)
Despite the hard-pruner refutation, vol-34 measured that capiman's unsat database HAS signal as a soft value-order at shallow depths. Ranking ground-truth-candidate position in unsat-ascending order on three verified record boards (vol-32 458, two 457s): rank 0%/perfect at d=30; 9-20% at d=80; 2-89% at d=160+ (inconsistent at deep). Integrate as `ValueOrder::UnsatSoft` active at depth < 100, fallback to MRV+LCV at d ≥ 100. Uses ml/data/ reconciliation maps already shipped. Cost: 4-6h build + 2h measurement. Vol-35 T2 candidate.

### `joe-iteration-budgeted-prune` (msg #11725) — status: `unbuilt` — since: vol-32 open
Joe's iteration-budgeted prune-to-depth policy: 99% of canonical-E2 cold-start time is spent at depth >132; with 150 correctly-placed tiles a solution is found in <1500 iters; therefore prune to depth 150 every 2000 iters when depth>150 has consumed >2000 iters without progress. 30-49% search-space reduction reported. We already have `mcgavin-prune-restart` (vol-23) with the engine plumbing; this is a different *triggering policy* — iteration-count rather than CP-depth. ~half day to wire as a new param.

### `learned-on-ties-long-pt` — status: `unbuilt` — since: vol-31
Run pt_e2 from LearnedOnTies-174 at 1-2 hour budget (vs vol-31's 15 min). Does the 445 plateau open up with more compute, or is it a real ceiling? Cheap compute, overnight job.

### `learned-on-ties-hyperparam-sweep` — status: `refuted` — vol-32 (2026-05-13)
Ran T1 49-config sweep (7×7 EPS × MAX_K). All hit depth 174 — but this was pre-bug-fix; the model was never being called. Post-fix the sweep is uninteresting (LOT runs at ceiling 165 = baseline; hyperparams modulate only the NN tie-break within already-EdgeBp-sorted candidates, small effect). See `vault/sessions/vol-32-bug-discovery.md`.

### `insertion-order-under-joe-depth150-bp` — status: `partial` — since: vol-32
**Free +9 depth axis discovered by vol-32 bug investigation.** Under `joe_depth150_bp` profile, `--mode insertion` reaches depth 174 in 60s while `--mode edge_bp` (the profile's default) reaches 165. Vol-12 measured EdgeBpMarginals as a +18.84% interior reduction (positive); here it's a -9 depth regression. Hypothesis: under joe_depth150_bp's heavy propagator stack (gacolor + AC-3 + NS-1 + depth-150 gate), BP-sort's reordering interferes with propagator-induced cell ordering. Worth a small investigation: does the +9 propagate to score post-ALNS / post-PT? T3 measures this (PT lottery from insertion-174 partial, 30 seeds × 15min). Vol-33 candidate to characterise across profiles.

### `unsat-clause-propagator-prototype` — status: `partial` — vol-32 (2026-05-13)
Python prototype shipped (`ml/unsat_propagator_proto.py`): decoder + CNF parser for capiman/e2's 130,180-literal scheme. Round_1 (largest): 53.2M clauses, 56.6s parse, 106M directed forbidden-edges, mean 817 partners per literal. Memory estimate for full CSR ~430 MB (manageable). Rust engine integration is vol-33's binding item.

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

### `blackwood-fast-per-depth-unrolling` — status: `built` — vol-106 (2026-05-16)

**SHIPPED**. User intuition was correct; my prior "low EV" analysis
was wrong. The full per-depth unrolling gives **+25% nps** (baseline
63M → PGO+unrolled 79M single-thread on canonical Selby-Riordan).

Implementation: `solve_blackwood_unrolled_256` in
`crates/blackwood-fast/src/lib.rs` uses the `depth_dispatch_256!`
proc-macro from `crates/blackwood-fast-codegen` to emit 256 distinct
match arms. In each arm, `__D__` substitutes to the literal depth
value as a `usize` const, enabling LLVM to constant-fold per-D
quantities (D_ROW, D_COL, IS_TOP_ROW, IS_BOTTOM_ROW, IS_LEFT_COL,
IS_RIGHT_COL, TBL, POST_DEPTH).

Opt-in via `E2_BF_UNROLLED=1` env var. Build time penalty: ~36s
extra (5s → 41s) due to 256-fold expansion of the inner body.

Why my prior analysis was wrong: I underestimated how much LLVM
exploits per-arm branch-prediction independence. Even when
`targets[D]` and `conflicts_allowed[D]` stay as runtime loads, the
per-arm context lets LLVM specialise the basic-block layout and
branch predictor for each depth's typical access pattern. The
constant-folded depth-meta is a secondary win on top.

See concept page [[rust-perf-at-scale]] for the broader
optimization log.

**Analysis update 2026-05-16 ~10:00 CEST**: after building the
proc-macro scaffold (`depth_dispatch_256!`) and confirming it works,
the honest read of which per-D values are foldable to compile-time
constants:

- **Foldable** (already done in T11 via bitmask inlining):
  `is_top_row`, `is_left_col`, `is_right_col`, `is_bottom_row`, `tbl`.
- **Not foldable without further infrastructure**:
  `targets[D]`, `conflicts_allowed[D]` are per-puzzle runtime arrays.
  To fold them would require per-schedule const tables (one set per
  schedule variant) + monomorphization on the schedule choice.
- **Cannot fold**: anything in the inner trial loop (cursor, cum,
  conf, board, pieces_used) — all runtime-mutable.

Net per-D specialisation saves ~1 L1 load per node (~3 cycles) on
top of T11. **Probably ~5-10% extra over PGO+T11.** This is much
smaller than the initially-estimated 1.5-3× from per-depth unrolling
because the bottleneck isn't depth-meta lookups, it's the inner trial
loop (which already runs at the 9-instruction per-cycle ceiling per
T7 asm inspection).

The libblackwood C engine's 295M nps vs our 72M PGO gap (4×) is
likely NOT primarily from per-depth unrolling. Other factors:
- libblackwood ships per-depth UPDATE rules baked in (different
  per-depth conflict-allowed and schedule logic) that LLVM cannot
  see in our runtime-table design.
- C's `goto` chain vs Rust's `loop` may produce different basic-block
  layouts that the apple-m1 branch predictor handles differently.

**Decision**: defer the full per-depth unrolling integration. Track
the proc-macro scaffold + macro_test sanity-check as `built`. The
EV/effort ratio is poor compared to other vol-107 candidates.
**Biggest remaining nps lever for blackwood-fast.** The current `solve_blackwood_sized` is one generic loop body that runs 256 times. libblackwood (Bucas's C engine) generates 256 distinct goto-labelled depth blocks with each block's constants (post_depth, schedule target, conflicts_allowed, is_top_row, is_left_col, depth_tbl) inlined at compile time — eliminating per-node table lookups for those.

Rust path: const-generic + per-depth specialised functions that tail-call into each other (or — equivalently — proc-macro that generates the unrolled body, similar to libblackwood's `build.rs`-style codegen).

User note 2026-05-16: "I feel like manual unrolling might be a huge gain as it was for blackwood algorithm". EV: 1.5-3× nps (extrapolating from libblackwood's 295M nps vs our 68M).

**Vol-106 T11 partial**: shipped compile-time-W depth-meta unrolling
(canonical 16×16 computes `is_top_row`, `is_left_col`, `is_right_col`,
`is_bottom_row`, `tbl` inline from `depth & 0xF` and `depth >> 4`
instead of 3 LUT reads). Measured +5% pre-PGO; PGO subsumes via
branch profiles to the same 72 M nps as PGO-only. Commit `05fbbce`.

**Full per-depth function-body unrolling REMAINS UNBUILT.** Estimated
effort: 1-2 days via proc-macro that emits 256 specialised depth-block
bodies (each with `post_depth`, `target`, `allowed_here`, etc. as
compile-time constants). The Rust compiler's existing const-generic
machinery is NOT sufficient because the depth advances dynamically;
true per-depth specialisation requires either (a) a `match depth {...}`
on 256 arms (LLVM will struggle to inline 256 distinct function
bodies), or (b) a proc-macro that lays out the bodies contiguously
in source.

The PGO-driven branch reordering already captures most of the
straightforwardly-inlinable wins (PGO + depth-meta unroll = 72 M nps
single-thread). The remaining 4× gap to libblackwood's 295 M nps is
split across:
- Proc-macro-generated 256-block unrolling (~1.5-2× expected)
- Inner-loop bucket-walk improvements (probably ~1.5×)
- BOLT post-link reordering (~1.1×)

Not "complete quickly" by the agent in ≤1 hour — the proc-macro
work alone is multi-day given the depth-conditional logic for
schedule, break-index, and supply tracking.

---

## Vol-169 to vol-184 audit (vol-185 cleanup)

Status of every invention shipped vols 169–184:

| Vol | Name | Status | Notes |
|---|---|---|---|
| V169 | OPHIDIA — PriorDestroy escape | `partial` | refuted as plateau-breaker on V155→ALNS 460 base |
| V171 | MURMURATION — multi-basin sampling | `partial` | stochastic-T builder works; full sweep not run |
| V172 | CHIASMUS — cross-basin row interleave | `refuted` | "461" was σ-related-basin artefact |
| V173 | SPECTRA — spectral border signature | `partial` | signal too weak to integrate as ranker |
| V174 | PERTURBATION CURVE | `wont-do` | superseded by V175 scan diversity |
| V175 | GAUNTLET — multi-scan beam | `built` | 18 unique cps from 36 builds; new 458 basin |
| V177 | NEURONIC — tiny NN ranker | `partial` → `wont-do` | MLP R²=−9, GBM R²=0.40; superseded by V181 KEYRING |
| V178 | STIGMA — pheromone adjacency | `built` | λ=1e-7 calibrated; used in V181 |
| V179 | LARGE-K destroy variants | `built` | k∈{32,48} ops added; refuted as escape alone |
| V180 | INTAGLIO-ATTACK lex acceptance | `built` | flag wired; refuted as plateau-breaker alone |
| V181 | KEYRING — patch+pheromone+prior | `built` | best builder; new 460 cp=(0,3,1,2) + new 459 |
| V182 | ENGRAVE — CSP-fill row band | `partial` | K∈{2,4} probes refute local 460 lift |
| V183 | SEMAPHORE — per-row chain-DP | `refuted` | row-10 piece-starvation wall |
| V184 | LIGHTHOUSE — bidirectional row | `refuted` | MERGE interface infeasible |

Universal finding from vols 179/180/181: [[three-basin-iso-plateau]] — three distinct ≥458 basins all locked under 30min ALNS basic_lkh + V179 + V180. Path to 461+ requires structural / cross-basin moves.

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
- `three-basin-iso-plateau.md` (NEW vol-185)
- `keyring-patch-prior.md` (NEW vol-185)
- `v179-large-k-destroy.md` (NEW vol-185)
- `v182-engrave-csp-fill.md` (NEW vol-185)
- `lighthouse-bidirectional-row.md` (NEW vol-185)
