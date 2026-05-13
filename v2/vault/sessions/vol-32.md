---
tags: [session, vol-32, bug-discovery, insertion-order, unsat-propagator]
---

# Vol-32 — vol-30/31 ML lift refuted; InsertionOrder discovery; unsat-propagator bootstrap

**Theme**: The overnight ML engineering sweep planned for vol-32 was
short-circuited by discovering a one-line engine bug that invalidates
vol-30's "+9 depth lift" and vol-31's "+10/+8 score lift". The +9 was
actually InsertionOrder beating EdgeBpMarginals under joe_depth150_bp —
a free engine axis, not ML. Pivoted mid-session to investigating the
InsertionOrder finding + bootstrapping the unsat-clause-propagator
(BACKLOG vol-33 item) per user instruction "if ML is not that good,
move on".

## What was attempted

Per [[../plans/VOL-32]]: hyperparameter / model-size / score-axis
investigation of vol-30/31's claimed ML lift.

1. **T1** — 49-config EPS × MAX_K sweep on LearnedOnTies (15 min wall-clock).
2. **T2** — model-size ablation driver written (refuted before launch).
3. **T3** — 30-seed PT lottery from depth-174 partial (running at vol-close).
4. **T4** — LOT_TRACE engine instrumentation + Python diagnostics.
5. **T6 (added mid-vol)** — ALNS A/B on 3 partials post-bug-fix.
6. **T7 (added mid-vol)** — unsat-clause-propagator Python prototype.

## What was measured

### T1 — refuted by bug

49/49 configs gave depth 174 with node counts varying 307k-435k. This
*looked* like a real ceiling. Then T4's LOT_TRACE instrumentation
showed zero NN-call events under buggy LearnedOnTies → the model was
never engaged. T1 was sweeping over a no-op.

### Bug discovery

`crates/solver-engine/src/lib.rs:2550`:

```rust
cell_side_edge: if matches!(solver.config.value_order, ValueOrder::EdgeBpMarginals)
    && opts.edge_bp_marginals.is_some()
{ build_cell_side_edge(puzzle) } else { Vec::new() },
```

The initialiser only matched `EdgeBpMarginals` literally. Vol-30 added
`LearnedOnTies` (commit `c1294ed`) with sort + rerank blocks at
lib.rs:4017+ but never extended this initialiser. Under LOT,
`cell_side_edge` stayed empty → BP-sort block (line 4025
`!self.cell_side_edge.is_empty()`) was false → `bp_keys` empty → LOT
rerank block (line 4067 `bp_keys.len() >= 2`) was false. Engine fell
through to InsertionOrder.

Fix at commit `95978a5`: extended initialiser to also match
`LearnedOnTies`. One-line change.

### Post-fix measurements (canonical 16×16, 60s, single-thread, seed=1)

| Mode | Pre-fix depth | Post-fix depth | Real attribution |
|---|---:|---:|---|
| `edge_bp` (baseline) | 165 | 165 | Unchanged |
| `default` (joe_depth150_bp's default = EdgeBpMarginals) | 165 | 165 | Unchanged |
| `insertion` | 174 | 174 | InsertionOrder unchanged |
| `learned_on_ties` | **174 (BUG)** | **165** | Was secretly InsertionOrder; real LOT = baseline |
| `learned` (full NN) | 164 | 164 | Already correct |

| Partial | placed | matched_edges | Attribution |
|---|---:|---:|---|
| edge_bp_165 (baseline) | 170 | 280 | EdgeBpMarginals |
| insertion_174 (vol-30/31 "ML partial") | 179 | 303 | **InsertionOrder, not ML** |
| lot_fixed_v4 (TRUE post-fix LOT) | 170 | **283** | Real ML effect: +3 edges |

### T4 — LOT_TRACE diagnostic (post-fix, 60s on canonical)

- 10,502 events emitted in 60s of engine work.
- **97.2% of events fire the NN** (tie_len ≥ 2).
- **96.5% of events have dom=2** (binary tie-break, not large tie clusters).
- Activity concentrated at depth 120-150 (engine plateau).

### T6 — ALNS A/B (5min × 3 partials)

In progress at vol-close. First result: edge_bp_165 → matched 424/480
at 5min ALNS (winning5 ops, SA repair, seed=1). Reproduces vol-31
baseline (426 ± 1). insertion_174 + lot_fixed_v4 measurements
running; results in vol-33 once captured.

### T3 — Multi-seed PT lottery from insertion_174 (control)

Running 30 seeds × 2 replicas × 15min PT (Houdayer + kicks), parallel-4.
At vol-close: 8 seeds done, scores 438-442. Median ~440. Vol-31's
single-seed 8-replica gave 445 — within range. Final histogram available
post-completion (ETA 00:00).

### T7 — Unsat-clause-propagator prototype

Python prototype shipped (`ml/unsat_propagator_proto.py`):
- 130,180 literals decoded from `output/capiman_e2/e2_info.c` (0.43s).
- Round_1 CNF (125 MB gz): 53,194,585 clauses parsed in 56.6s.
- Forbidden-partner-count distribution: mean 817, max 4317.
- Total directed forbidden-edges from round_1 alone: 106M.
- Memory estimate for full CSR: ~430 MB. Manageable.

Decoder JSON written to `output/vol-32/unsat_propagator/literal_decoder.json`
(3 MB). Rust integration is vol-33 T1.

## What was refuted

- **Vol-30 "+9 depth from LearnedOnTies"** — measurement artifact of
  the cell_side_edge bug. Model never called. Real LOT lift = 0 depth.
- **Vol-30 "invariant across v3/v3b/v4"** — the invariance was that
  none of them were called; model files had zero effect.
- **Vol-31 "+10 / +8 score lifts"** — real numbers, real pipelines,
  but the depth-174 input partial was an InsertionOrder artifact, not
  an ML artifact. Mis-attribution, not measurement error.
- **The vol-30 BACKLOG "learned-on-ties-hybrid: built"** — flipped to
  `refuted`.
- **The vol-31 BACKLOG "learned-on-ties-alns-postfill"** — flipped to
  `refuted (re-attributed)`.
- **`learned-on-ties-basin-escape`** (vol-31 candidate) — `wont-do`
  (premise refuted).
- **`learned-on-ties-hyperparam-sweep`** — `refuted` (model never called).

## What was confirmed (NEW)

- **InsertionOrder beats EdgeBpMarginals by +9 depth under joe_depth150_bp**
  — real engine axis previously hidden by mis-attribution. Vol-12's
  measurement that BP helps (+18.84% interior reduction under simpler
  profiles) may not hold under the heavy joe_depth150_bp propagator
  stack.
- **Real ML lift at canonical**: depth Δ=0 (165 = 165), edges Δ=+3.
  Imitation ceiling at the teacher confirmed (vol-29's result was real;
  it's just the only real ML result at canonical so far).
- **LOT_TRACE diagnostic** is now permanent engine instrumentation
  (env-gated): future regressions like this become trivial to catch.
- **Unsat-propagator data is loadable**: 130k literals, 70M+ clauses,
  rust-integration-ready as a vol-33 binding item.

## Concepts touched

- [[../concepts/learned-value-order]] — major vol-32 amendment at
  bottom of page; status flipped to `built` (6×6) / `partial` (canonical).
- [[../concepts/unsat-clause-propagator]] — NEW concept page (status:
  partial, Python prototype only).

## Open at close

- **insertion_174 + lot_fixed_v4 ALNS results** — pending (ETA 23:13).
- **T3 PT lottery final histogram** — pending (ETA 00:00).
- **lot_fixed_v4 PT lottery** — NOT launched tonight; ~30 min cost.
  Vol-33 if needed.
- **Vol-33 plan**: pivot from ML to (a) unsat-clause-propagator Rust
  integration, (b) joe-iteration-budgeted-prune, (c) characterise
  InsertionOrder generality across engine profiles. Per user note.

## Linked memory

- `project_e2_vol32_lot_bug_refutation` (TO WRITE at close)
- `project_e2_vol32_insertion_order_finding` (TO WRITE at close)

## Linked sessions

- [[vol-30]] — claims of +9 depth lift (REFUTED)
- [[vol-31]] — claims of +10/+8 score lift (mis-attributed)
- [[vol-29]] — imitation ceiling Δ=−1 (UNAFFECTED, correct)
- [[vol-32-bug-discovery]] — the full evidence trail
