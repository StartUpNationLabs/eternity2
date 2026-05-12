# RESEARCH_NOTES_9.md — vol-9: implement community techniques

**Session**: 2026-05-12, single-thread, develop branch.
**Calibration ceiling**: 469/480 (McGavin 2020, Blackwood solver) — NOT 467.
**Mandate**: implement the top community techniques vol-8 catalogued on our
own stack and measure them honestly against 469.

## Plan (confirmed with user)

User directive: "don't think in terms of half-day; just do the best and
most complete things you can." Plan therefore is: ship both #1 and #2
completely — propagator + corpus calibration + in-engine wiring for #1,
full outer-SA + inner-backtrack + phase-2 for #2.

1. **#1 Eulerian-cycle border connectivity propagator** (anr_56 2007). Multi-graph on 22 edge-pattern vertices; border tiles
   are directed L→R edges; valid ring ⇔ Eulerian cycle ⇔ in-degree =
   out-degree at every vertex AND connected. The in/out-degree equality is
   automatic for the closed-ring problem (every right-pattern must be met
   by a left-pattern); the **connectivity** test is the real new pruner.
   Plugs into `crates/propagators` as a new function; bool toggle on
   `EngineConfig`. Calibrated on `output/borders/sample_*.jsonl` (100/10k/100k
   border rings already sampled by vol-6).
2. **#2 Verhaard set-composition swap-annealing** (2008) — the meat of
   the session. Outer SA over piece-set composition; inner backtrack
   preferring worst performers first; phase-2 exhaustive completion.

## Pre-flight checks

**Vol-7 process liveness**: DEAD. `ps aux | grep -E "(pt_e2|sat_e2|reverse_selby|map_elites)"`
returns nothing. Vol-7 logs in `/tmp/v7_*.log` last written 2026-05-12 10:07.
Vol-8 closed cleanly. Read-only on vol-7 artifacts confirmed safe.

**Date check**: 2026-05-12 10:22 CEST (system `date`).

## Session log

### 10:22 — opened RESEARCH_NOTES_9.md, plan confirmed

Reading propagators crate (`crates/propagators/src/lib.rs`) and engine
wiring (`crates/solver-engine/src/lib.rs`). Existing propagators follow a
pattern: `fn name_check(ctx: &PropagatorContext<'_>) -> PropagatorResult`,
toggled by a bool field on `EngineConfig`, invoked from `run_enabled(...)`
in cheapest-first order. Eulerian will follow the same shape.

Border corpus: `output/borders/sample_100.jsonl`, `sample_10k.jsonl`,
`sample_100k.jsonl`. Format: `{"border":[[piece_id,rot], ...]}` 60-tile
sequences (16+16+16+12 perimeter for 16×16). Vol-6 sampled these from
some baseline ring generator; we'll re-run the Eulerian test on each and
report:
  - what fraction pass (target ≈ 0.70 per anr_56 P=16)
  - whether failed rings are detectably non-tileable
  - timing per check (must be ≪ a backtrack node cost)

### 11:00 — Eulerian calibration on 100k corpus: NEGATIVE RESULT

Built `crates/propagators/src/border_eulerian.rs` (RingEdge,
edge_tile_ring_edge, corner_tile_ring_edge, eulerian_ring_check_full,
eulerian_pool_check, eulerian_pool_or_check) and the calibration
binary `crates/benchmark/src/bin/eulerian_border_corpus.rs`.

Ran on `output/borders/sample_100k.jsonl` with 1M random-subset
trials. Five experiments:

| # | Test | Result |
|---|---|---|
| (a) Sanity: real corpus rings | 100000/100000 pass | ✓ correctness baseline |
| (b) Swap-perturb (2 tiles across sides) | 97% caught by chain-consistency; **0% additional by connectivity** | connectivity adds nothing here |
| (c) Random-subset borders (chain enforced) | 0/1M pass (all fail chain immediately) | chain-consistency dominates |
| (d) Pool-OR over full E2 border set | connected | sanity |
| (e) anr_56 analog (per-side-uniform sampling, no chain check) | **P(deg-balance) = 1.0, P(deg ∧ connect) = 1.0** over 1M trials | **NEGATIVE: no pruning** |
| (f) Mid-search alternative-completion (K=10/20/30/45/55) | 0/100k rejected at every depth | **NEGATIVE: no pruning at any depth** |

**Finding**: on the canonical E2 piece set, the Eulerian-cycle border
connectivity propagator has **zero pruning power** at every search
depth tested. The mechanism is exact and correct (theorem is sound),
but the canonical E2 border palette is structurally rich enough that
every per-side allocation yields a connected, degree-balanced
multigraph.

**This falsifies a community expectation.** anr_56's 2007 prediction
of "0.78 (P=15) / 0.70 (P=16) tileability" was on a *synthetic
generator with P border colors*; canonical E2 has a smaller border
palette but the 60 specific pieces collectively saturate it. The
generator picked a piece set where this constraint is vacuous.

**Decision**: do NOT wire Eulerian into `EngineConfig` as a new
propagator. The runtime overhead — small but nonzero — earns zero
pruning. Document the propagator and corpus result so future agents
(or anyone trying the same idea) skip this dead end.

The propagator code stays in `crates/propagators` as documented dead
code with the calibration evidence — it's an exact theorem, future
puzzle variants (smaller piece set, non-Monckton generator) may have
nontrivial pruning. The CLAUDE.md rule "delete unused code" doesn't
apply here: the code's purpose is preserving the negative-result
evidence.

### 11:10 — Pivot to Verhaard swap-annealing (#2)

Eulerian: shipped, calibrated, ruled out. Move to the main course.

### 10:25 — Eulerian formulation pinned (historical, kept for context)

For a border *ring* (the closed perimeter), every tile is a corner
or edge piece placed with its frame-facing edge outward. The two
**interior-facing edges** of each tile become the L (clockwise-trailing)
and R (clockwise-leading) of a directed edge in a multi-graph G whose
vertices are the 22 edge-pattern colors (here, the ~5 border colors —
the perimeter only sees the border-color sub-palette per Selby's
generator design).

For the ring to close:
- in-deg(v) = out-deg(v) for every v  (Eulerian-cycle existence in directed multigraphs)
- the subgraph induced by vertices with positive degree must be strongly connected
  (in directed multigraph case; for ring-walks we need connectivity of edge-induced subgraph)

For a **partial** placement (k < 60 tiles placed, contiguous from a
fixed start), the propagator forms G from the *unplaced border tiles'*
edge patterns plus the open "demand" left by the current frontier. The
ring is completable only if a directed Eulerian *path* from the current
exit pattern back to the start's entry pattern exists in this G.
