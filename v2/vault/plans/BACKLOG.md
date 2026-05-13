# BACKLOG — canonical T-list

**Discipline**: Any `unbuilt` item with `since` ≥ 3 volumes back must be picked or marked `wont-do` at next vol-open.

Status tags: `unbuilt` | `in-progress` | `built` | `refuted` | `wont-do` | `partial`

---

## Algorithm builds (engine-level)

### `mcgavin-prune-restart` — status: `built` — vol-23 (2026-05-13)
Built after 8 vols of deferral. Engine: `SolveOpts.batch_hint_application: bool` lets the engine pin DFS-derived hint sets without false-positive wipeouts. Driver: `crates/bench-audit/src/bin/prune_restart.rs`.

**Empirical (vol-23)**: validated as CP-deepener (cold-start round 1→2 lifts depth 27→152 / score 23→297). But UNDERPERFORMS vanilla cold-start ALNS as a score-maximizer (424 vs 430-450 batch median) because CP fills in FirstSolution mode, taking the first valid completion not the best.

Score lift estimate (1-2 days, +5..10) was wrong in spirit: the CP-deepener does lift CP depth dramatically, but post-ALNS the score is below baseline. See [[prune-restart]] for the empirical detail and `score-optimizing-cp` (new entry) for what would close the gap.

### `pt-tabu-zobrist` — status: `unbuilt` — since: vol-17 (mentioned), vol-21 (T7)
**Aged 5 volumes.** Vol-14 memory `e2_vol14_pt_no_tabu` flagged this. PT chains have no anti-cycle mechanism; iso-score plateaus cause drift.
- See `concepts/pt-tabu.md`
- Est. 4-6 hrs

### `joe-2019-sat-postprune` — status: `unbuilt` — since: vol-14 plan
Future: 1-week build. Park as `wont-do` for now? Decide at vol-23 open.

### `piece-orbit-as-atom` (N9 from vol-20) — status: `unbuilt` — since: vol-20
Treat pieces in same edge-multiset orbit as fungible. There are only 5 such orbits in canonical E2 (10 pieces of 256). Low value. Likely `wont-do`.

### `multi-cell-bound-ascent` (vol-22 T3) — status: `unbuilt` — since: vol-22
3-cycle and 4-cycle moves in bound-landscape, not just 2-swaps. Plateau at bound 470 might break.
- See `concepts/bound-ascent.md`
- Est. 1 day

### `bound-floor-alns-with-per-step-check` — status: `partial` — since: vol-22
Vol-22 T1 was the per-RUN version (null). Per-STEP version requires modifying ALNS internals.
- See `concepts/bound-ascent.md`
- Est. 1-2 days (invasive)

### `kissat-rc2-maxsat` (vol-22 T3, user-Q) — status: `unbuilt` — since: vol-22
z3 cannot solve our MaxSAT (UNKNOWN on 60-cell clusters in 180s). Need a real MaxSAT solver. Gives exact joint bound.
- See `concepts/exact-joint-bound.md`
- Est. 4-6 hrs

### `score-optimizing-cp` — status: `unbuilt` — since: vol-23
Vol-23 finding: prune-restart's CP fills cells in FirstSolution mode, taking ANY valid completion. To turn prune-restart into a record-breaker we need CP that OPTIMIZES score (matched-edge count) while satisfying constraints. Two routes:
- (a) MaxSAT formulation (uses existing `sat-encoder` crate; blocked on `kissat-rc2-maxsat`).
- (b) Branch-and-bound CP with edge-match objective baked into the search (modify recurse() to track upper-bound and prune when upper < best-so-far).
- Est. 1 day for route (b); shipped sat-encoder already supports route (a).

---

## Search / exploration

### `cooperative-pair-swap` (vol-21 T2) — status: `unbuilt` — since: vol-21
Compose Δ=-1 swap pairs sharing an endpoint into 3-cell moves. The vol-21 Python prototype found none, but the Rust + bigger window was never tried.
- Note: vol-20 cycle_scan already covered K≤5 cycles. This is K=3 with cooperativity, may overlap. AUDIT before building.

### `color-relabel-search` (vol-21 T4) — status: `unbuilt` — since: vol-21
Joint search over (placement, color-permutation π ∈ S_23). Score-preserving symmetry; might change heuristic rankings.
- See `concepts/color-relabel.md`
- Est. 4-8 hrs

### `forced-perturb-meta-op` (vol-21 T6) — status: `unbuilt` — since: vol-21
Inject Δ=-k jolts into PT chains. Vol-20 basin_hop tested k=1,4. Larger k not tried beyond manual.
- Est. 2-3 hrs

### `diverse-457-search` (vol-21 T5) — status: `partial` — since: vol-21
"Lottery" for finding non-byte-identical 457s. Vol-22 didn't run it; instead the basin-escape recipe found different >457-ceiling basins. Still valuable as separate axis.
- Est. 0 build, overnight compute

### `bound-ascent-then-blackwood-cp` (vol-22 T2) — status: `unbuilt` — since: vol-22
Use bound-ascent's high-bound edge structure as VALUE-ORDER for Blackwood CP starting from canonical hints. Most novel composition.
- Est. 1 day

### `gap-recording-instrumentation` (vol-22 T4) — status: `unbuilt` — since: vol-22
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
