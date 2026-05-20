# Neuronic — Tiny NN Ranker for Beam Search (V177)

Status: `unbuilt` (design 2026-05-20)
Origin: vol-177 (planned)
Naming: **NEURONIC** — a small neural rule injected into a combinatorial search.

## Idea

Currently V155 and V175 rank beam children by `score + α·prior_sum`. This uses two scalar features. A NN ranker can use MANY features — score, prior_sum, forbidden_2x2_count, border_spectrum_match, mismatch_geometry, used_piece_class_balance — combined nonlinearly.

The NN is TINY (<10k params): a 2-layer MLP trained on (partial_board → final_lifted_score) pairs from our DB. Inference cost: ~10 microseconds per child, vs ~12s per V155 build → negligible overhead.

## Architecture

```
Input feature vector φ(b) ∈ R^F where F ≈ 20-50:
  - depth
  - score (raw matched edges)
  - prior_sum (V155 prior)
  - forbidden_2x2_count
  - border_spectrum amplitudes at k = 5, 7, 12, 13, 16, 19, 26, 29 (V173 SPECTRA)
  - mismatch_count
  - components_of_mismatch_graph
  - per-class piece usage ratios (corner / edge / interior)
  - hint-adjacency match counts (5 hints × 4 adj cells = 20 features)

Network:
  Linear(F → 32) → ReLU
  Linear(32 → 16) → ReLU
  Linear(16 → 1) → score estimate

Loss: MSE between predicted final score and observed final score from
   lifting `b` via 5-min ALNS.

Training data:
  - 1000+ partial boards × ground-truth lifted score (cached from our
    DB of 938+ corpus boards).
  - Generate by truncating known high-score boards at random depths.
  - Plus: V155/V175 builds with their 5-min lift scores.
```

## Why a tiny network suffices

The ranking task is REGRESSION over a 256-cell state — global representations would need a CNN or transformer. But the BEAM search only needs to discriminate between SIBLINGS (children at the same depth from the same parent). These differ by 1-2 cells. A *delta-feature* model (compare φ(child) to φ(parent)) reduces to a small MLP.

Alternative architecture: **pairwise siamese** — compare two siblings, output a sign (which is better). Training: ranking loss (Bradley-Terry) on triplets (parent → better_child, worse_child).

## Two-stage training

1. **Bootstrap**: train on synthetic (truncated_corpus_board, known_final_score) data.
2. **Refinement**: deploy NN-ranked V175, observe new build outcomes (build → lifted score), add to training set, re-train.

This is a soft form of self-play / RL fine-tuning. Each iteration improves the ranker on the actual basins V155-style beam explores.

## Critical concern

If the corpus is biased (49 high459 boards from a few cp families), the NN learns those biases. To avoid memorization:
- shuffle training labels across cp families
- regularize heavily (dropout 0.5, weight decay 1e-2)
- validate on held-out cp families

A NN that just memorizes "high459 cp = (3,2,0,1) → 469" is useless for finding NEW basins. We want it to predict "this NEW partial → ~460 lift" without naming the basin.

## What's still open

- Cross-domain feature inclusion: depth-40 phase transition values, vol-122 K11 signatures, GRAIN / FILAMENT residuals.
- Should ranking happen at every beam depth, or only every K depths?
- Could the NN propose its own destroy ops for ALNS?

## Linked

- [[murmuration-basin-sampling]] (V171) — same diversity goal, different mechanism.
- [[spectral-border-signature]] (V173 — features feed into NEURONIC).
- [[prior-data-augmented-beam]] (V155 — base architecture).
- [[../plans/INVENTIONS_BACKLOG]] (C1 GNN, V167 NN — related but C1 is per-cell, V167 is whole-board).
