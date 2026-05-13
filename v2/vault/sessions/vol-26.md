---
tags: [session, vol-26, ml-gate]
---

# Vol-26 — Learned value-order gate (one binding item)

**Theme**: Imitation-learning model beats MRV by 540× nodes at 6×6/5c —
but the stdio bridge eats the win.

**Note on chronology**: vol-26 was opened and executed BEFORE vol-25 on
the same calendar day (2026-05-13). Vol-25 was a separate engine-perf push
shipped in parallel by a sibling agent (vol-25 head: `06a2163`). When
reading these journals in order, expect the vol-25 close to reference
state that vol-26 had already produced.

## What was attempted

T1 — Learned value-order gate. One binding item, no others (per vol-26
plan).

1. Extended `eternity2-generator::generate_with_solution` to return the
   canonical assembly alongside the puzzle (the implicit solution from
   the Selby-Riordan construction).
2. Built `crates/ml-export/` (new crate) with three bins: `gen-export`
   (JSONL exporter), `measure-difficulty` (MRV difficulty calibration),
   `bench-eval` (evaluator harness).
3. Built `ml/` (new Python project): generator-driven dataset loader, a
   small 2-layer grid GNN (~53k params), imitation training loop, stdio
   inference bridge, evaluator.
4. Added `ValueOrder::Learned` to the engine with a `learned_score_candidates`
   helper that talks to the Python bridge via JSON-over-stdio.
5. Trained on 10 000 synthetic 6×6/5c puzzles → 360k (state, target)
   tuples → 5 epochs CPU (Adam, lr 1e-3, batch 1024), val_acc 23.8%
   (vs 0.7% random).
6. Measured the gate on 200 held-out test puzzles.

## What was measured / kept

| Metric | MRV | Learned |
|---|---:|---:|
| Coverage | 200/200 | 200/200 |
| Median engine nodes | 19 594 | **36** |
| Median wall-clock ms | 11 | 609 |
| Bridge per-node latency | n/a | ~15 ms |

- **Median node-ratio: 0.0018 (≈ 540× reduction).** Algorithmic win is
  unambiguous; the model has internalised the expert search trajectory.
- **Wall-clock: 56× slower.** Bridge IPC + Python torch.no_grad inference
  dominates the saved engine time.
- Gate condition (c) unsatisfiable at 6×6/5c (MRV had zero failures
  within 5s budget).
- See [[../concepts/learned-value-order]] for the full table + analysis.

## What was refuted

- Vol-26 plan's choice to re-implement the generator in Python. The
  Rust generator already does exactly the same construction with
  reproducible SplitMix64 seeding. Re-implementing would have introduced
  a second source of truth. Decision (vol-26 open): use Rust + JSONL
  export. See [[../concepts/synthetic-puzzle-generator]] for the
  reasoning.
- The 200k-param model size suggestion from the plan. 53k params already
  saturate the algorithmic signal at 6×6/5c; bigger wouldn't change the
  wall-clock story.

## What is open

- **Bridge overhead is the unblock.** Vol-27 should pick ONE of:
  ONNX-in-Rust (recommended), PyO3 in-process binding, or hand-rolled
  SIMD forward in Rust. ~1-3 days.
- **Condition (c) needs harder puzzles.** Once bridge is fixed, re-test
  at 7×7 / 8×8 / 5c where MRV has 5-15% failure rate within 5s.
- **Variable-size architecture** if we want canonical-16×16 transfer.
  Today's GNN bakes the size at construction.

## Concepts touched

- [[../concepts/learned-value-order]] (NEW) — the gate result.
- [[../concepts/synthetic-puzzle-generator]] (NEW) — the data pipeline.
- [[../concepts/genetic-algorithm]] (vol-25 amended) — frames why we're
  trying ML now: pure GA refuted at canonical 16×16 by 16 years of
  literature.
- [[../concepts/symmetry-analysis]] (vol-25) — σ-bijection isn't an
  algebraic lever; ML is the next direction.
- [[../concepts/edge-bp-marginals]] — the existing closest analog: a
  learned-from-data value-order via cell-level BP. Vol-26 demonstrates
  that NN-based imitation gives ≥ 540× node reduction vs BP's ~18%
  entropy gain at the comparable scale.

## Open at close

- Audit-at-open compliance: vol-26 explicitly waived this (vol-25 was
  doing the same-day audit). No aged BACKLOG items were resolved this
  vol; that's vol-25's territory.
- Vol-27 inherits: the 540× algorithmic finding + the bridge-overhead
  problem. Vol-27 plan is at [[../plans/VOL-27]].

## Linked memory

- `project_e2_vol26_learned_value_order` (NEW)
