---
name: seifer-2025-analysis
description: "Vol-125 T38b inspection of e2solver (Seifer, Weizmann Institute, December 2025). Identifies their NEW techniques: nucleation, selection waves, graph-to-sequence neural network, D-Wave quantum annealing integration."
metadata:
  type: project
---

# Seifer 2025 e2solver — technique inventory

Cloned from https://github.com/Pr4Et/EdgeMatchingPuzzleSolver on 2026-05-18.

## Their methods (from README + code inspection)

| Key | Method | NEW for us? |
|---|---|---|
| w | Deduction (CSP propagation) | Standard — we have it (AC-3 + alldiff) |
| **h** | **Nucleation** (grow from seed outward) | **NEW — could be very useful** |
| f | Fix faults / show population | Mismatch analysis — we have similar |
| q | Discrete solver | Generic backtrack — standard |
| p | Probabilistic solver | Possibly randomized DFS — not detailed |
| **k** | **Search-replacement of 4 tiles** | Similar to our near_basin σ-cycle attack (T30) |
| r | Random fill | Trivial — we have |
| **,** | **"Choose best corners and neighbors"** | Interesting heuristic — needs inspection |
| **~** | **Selection waves** (relaxed solution) | **NEW — propagating messages** |
| **1-9** | **D-Wave QA** | NEW — quantum annealing path |
| **.** | **AI method** | **NEW — neural net inference** |

## Detailed analysis of novel techniques

### Nucleation (key 'h')

Code at line 3706+ uses "strategy" variable with 3 modes:
- strategy 1: "stop nucleation with the first dead end"
- strategy 2: "skip pieces that could not fit the nucleation"
- strategy 3: "suggest"

Mechanism: pick a SEED tile (likely a hint or high-rarity piece), GROW
the placement outward by extending to compatible neighbors. When dead-end
hit, either backtrack (strategy 1) or skip (strategy 2).

This is essentially **BFS-based constructive search** vs our DFS. Could give
different local minima. **Build-priority: HIGH.**

### Selection Waves (key '~')

Backed by `Python_Selection_Waves_Salesman/TSPP.py`. Message-passing on a
directed graph:
1. Each edge has a delay
2. Messages travel along edges, decrementing delay counters
3. When multiple messages arrive at a node simultaneously, ONE is chosen
   (randomly), others get delayed +1 (collision resolution)
4. Convergence: a message that visits all nodes = full TSP-like tour
5. Generates a "relaxed solution" (grand_options) for the puzzle

This is essentially a **stochastic discrete message-passing inference** —
similar in spirit to belief propagation but with hard arbitration. Could
be a novel relaxation for E2.

**Build-priority: MEDIUM** (needs porting from Python + integration).

### Graph2Seq Neural Network (key '.')

`code/Python/Graph2seq/` contains:
- 15 MB of trained PyTorch weights (encoder + decoder)
- DirectionalAttentionEncoder with edge-type-aware multi-head attention
- Transformer decoder predicting pairwise edge placements

Architecture: takes graph representation of puzzle pieces (nodes =
pieces, edges = piece-side compatibility), outputs grid placement.

**Build-priority: HIGH** — can directly RUN their trained model on
canonical E2 and see what placement it suggests. If their model is
decent, integration cost is low (just call inference).

### Search-replacement of 4 tiles (key 'k')

We already do this as `near_basin_attack.py` (T30 — found that McGavin's
469 is optimal on bottom-row 4-cell σ-cycle). They likely have a similar
operator. **Status: parallel discovery, no new info.**

### "Best corners and neighbors" (key ',')

Suggests they have a heuristic for picking optimal corner permutation +
neighboring pieces. We have corner-perm sweep (vol-124 W11). Likely similar.

## D-Wave Leap accessibility

Free tier: 1 min QPU + 20 min hybrid per month (per https://cloud.dwavesys.com/leap/signup).
Trial = 1 month. Open-source contributions earn more.

For E2 cluster decomposition (vol-44 had 22 clusters ≤ 500 vars each), 1
minute QPU is sufficient for ~100-1000 cluster queries.

**Action**: NEEDS USER-SIDE SETUP (signup + API token). I'm not running
this autonomously to avoid burning user's free quota without permission.

## Priority order for porting

1. **Graph2Seq inference** (T42a): clone their model, run inference on
   canonical E2, see what placement it predicts. Lowest risk, fastest payoff.
2. **Nucleation** (T42b): port to our Rust BB&B as alternative MRV order.
3. **Selection waves** (T42c): port TSPP.py to E2, see if it gives novel
   relaxed solutions.
4. **D-Wave hybrid** (T42d): defer until user provides API token.

## Sources

- https://github.com/Pr4Et/EdgeMatchingPuzzleSolver
- https://zenodo.org/records/18109266 (DOI)
- D-Wave Leap signup: https://cloud.dwavesys.com/leap/signup
