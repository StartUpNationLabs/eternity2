# BACKLOG — canonical T-list

**Discipline**: Any `unbuilt` item with `since` ≥ 3 volumes back must be picked or marked `wont-do` at next vol-open.

Status tags: `unbuilt` | `in-progress` | `built` | `refuted` | `wont-do` | `partial`

---

## Algorithm builds (engine-level)

### `mcgavin-prune-restart` — status: `built` — vol-23 (2026-05-13)
Built after 8 vols of deferral. Engine: `SolveOpts.batch_hint_application: bool` lets the engine pin DFS-derived hint sets without false-positive wipeouts. Driver: `crates/bench-audit/src/bin/prune_restart.rs`.

**Empirical (vol-23)**: validated as CP-deepener (cold-start round 1→2 lifts depth 27→152 / score 23→297). But UNDERPERFORMS vanilla cold-start ALNS as a score-maximizer (424 vs 430-450 batch median) because CP fills in FirstSolution mode, taking the first valid completion not the best.

Score lift estimate (1-2 days, +5..10) was wrong in spirit: the CP-deepener does lift CP depth dramatically, but post-ALNS the score is below baseline. See [[prune-restart]] for the empirical detail and `score-optimizing-cp` (new entry) for what would close the gap.

### `pt-tabu-zobrist` — status: `wont-do` — since: vol-17, resolved: vol-24
**Aged 5 volumes; resolved at vol-24 open.** Vol-22 measured PT plateaus at 442/480 on the 440/469 basin across 60s/5min/15min/30min budgets — saturation is the binding constraint, not chain-drift / cycling. Tabu only helps if PT *could* break the saturation gap, which the budget-scan data refutes. Mark `wont-do`; revisit only if a new mechanism (e.g. stronger repair operator) raises the plateau enough that anti-cycle would matter.
- See `concepts/pt-tabu.md` (kept; status updated)

### `joe-2019-sat-postprune` — status: `wont-do` — since: vol-14, resolved: vol-24
Aged 10 vols. ~1-week build to replicate Joe's 11-hour SAT solve on a 2-weeks-of-Blackwood pre-pruned domain. No clear path from here to canonical 5-clue 480 that doesn't already require the upstream Blackwood pre-prune (which we don't have). Mark `wont-do`; the gap-closer we actually need is `score-optimizing-cp` (active vol-24 binding).

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
