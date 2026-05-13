---
tags: [session, vol-28, ml-transfer-refuted]
---

# Vol-28 — cross-domain transfer REFUTED at canonical 16×16

**Theme**: Position-relative model shipped. Trains to 97.3% val_acc on
6×6/5c synthetic. Transfers as **CONFIDENT WRONG GUIDANCE** at canonical
16×16/22c — depth regression −108 under `joe_depth150_bp`, regression on
its own 6×6/5c training distribution too.

## What was attempted

T1 — Variable-size GNN (T1A from the vol-28 plan). Single binding item.

1. `ml/model_v2.py` — `PositionRelativeModel`: size-agnostic (nb_idx +
   valid_mask as runtime args) and piece-count-agnostic (24-color
   embedding shared across all sizes, per-candidate scoring head).
2. `ml/dataset_v2.py` — `(state, target_pos, cand_edges, target_idx)`
   tuples. Candidates: 1 expert + N-1 negatives sampled from
   pieces+rotations whose edges match the target cell's border-mask
   AND placed-neighbour facing-sides.
3. `ml/train_v2_cached.py` + `preprocess_v2.py` — bake the dataset to
   .pt once (~5 min), then ~30s/epoch over 360k samples.
4. `ml/export_v2.py` — ONNX export with dynamic axes for batch +
   n_cells + n_cands. Verified at both 6×6 and 16×16.
5. `crates/solver-engine/src/bridge.rs` — `LearnedScorer` becomes a
   V1/V2 enum dispatched by sidecar `.meta.json` `version`.
6. `crates/solver-engine/src/lib.rs::learned_score_candidates` —
   builds v2 inputs (cell_feats + nb_idx + valid_mask + cand_edges)
   when the loaded scorer is v2.
7. `crates/ml-export/src/bin/canonical_eval.rs` — canonical-E2
   cold-start measurement bin with `--profile` and `--mode`.

## What was measured

| Profile + Value-order | Max Depth | Nodes | Backtracks |
|---|---:|---:|---:|
| border_first_lcv + MRV (LCV) | 65 | 5.3M | 1.5M |
| border_first_lcv + edge_bp | 87 | 7.4M | 2.3M |
| **joe_depth150_bp (default)** | **165** | **254 k** | **44 k** |
| joe_depth150_bp + Learned (v2) | **57** | 248 k | 137 k |
| border_first_lcv + Learned (v2) | 60 | 643 k | 121 k |

Plus a SANITY-CHECK regression at 6×6/5c on the same 200 test puzzles
the v1 model passed cleanly at vol-27:

| Model | Solved | Median nodes |
|---|---|---:|
| v1 (vol-27) | 200/200 | 36 |
| v2 (vol-28) | **186/200** | **19 129** |

The v2 model is **worse than v1 on the SAME 6×6/5c data**, despite
training to 97.3% val_acc on its own training distribution.

## What was refuted

- **Cross-domain transfer of the imitation signal**: the model trained
  at 6×6/5c does not produce useful guidance at canonical 16×16/22c.
  Confidently wrong, not noisy-wrong.
- **The training task as currently specified**: cross-entropy over
  border-and-neighbour-filtered candidate sets does NOT match the
  inference task (score the engine's propagator-pruned domain). The
  97.3% val acc is misleading.

## Root cause analysis

Two distribution mismatches:
1. **Train/inference candidate distribution mismatch.** Training
   negatives passed only border + placed-neighbour filters. Engine
   asks the model to score the bitset-domain-pruned candidates,
   which pass additional propagators (piece-uniqueness, gacolor, AC-3,
   etc.). The inference distribution is a different beast.
2. **Color embedding cardinality.** 24-dim embedding; 6×6/5c saw only
   colors 0–5. At canonical, colors 0–22 — 16 embedding slots carry
   untrained noise.

## Concepts touched

- [[../concepts/learned-value-order]] (amended vol-28): adds the
  cross-domain-transfer REFUTED section + the 6×6 regression sanity
  check.

## Open at close

- vol-29 T1B (16×16-specific model trained on cold-start CP expert
  trajectories of our own engine on canonical E2). **Distribution-matched
  by construction**, dodges both root-cause problems above.
- vol-29 T1C (LearnedOnTies hybrid). Cheap engineering experiment;
  same transfer risk as v2. Status: untested.

## Linked memory

- `project_e2_vol28_transfer_refuted` (NEW)
- `project_e2_vol27_onnx_gate_pass` (vol-27 still valid)
