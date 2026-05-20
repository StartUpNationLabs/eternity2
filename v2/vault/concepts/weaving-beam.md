---
name: weaving-beam
description: V150 random-seed sweep: 50k seeds × 0.7s/seed → max 408/480.
status: built
metadata:
  type: concept
---
# WEAVING-Beam (V151) — Layered Beam Search From-Scratch

**Status**: `designed` 2026-05-19. Builds on V150 base.

## Genesis

V150 random-seed sweep: 50k seeds × 0.7s/seed → max 408/480.
Distribution heavy-tailed: log(N)-like growth. To reach 420 needs
~10⁶ seeds (22 min). To reach 440 needs ~10⁹ (~16 days). Pure random
sweep won't reach 463 record.

V151 invention: replace the single-greedy random-sweep with
**beam-search**. Keep top-K partials at each depth; expand all K with
all valid next-cell candidates; prune to top-K.

Mathematically equivalent to V150 at K=1, exhaustive at K=∞. Right K
trades compute for quality.

## Math

Let scan-order be $\sigma : \{0, ..., 255\} \to \{0, ..., 255\}$
(row-major or column-major).

State at depth $d$: $s = (\pi, U, \text{score})$ where
- $\pi: \{\sigma(0), ..., \sigma(d-1)\} \to (\text{piece}, \text{rot})$ — partial placement.
- $U \subseteq \{0, ..., 255\}$ — used piece IDs.
- score = matched-edges count given $\pi$.

Initial state: empty partial $s_0 = (\emptyset, \emptyset, 0)$.

Transition $s_d \to S'_{d+1}$:
$$S'_{d+1}(s_d) = \{s_d \cup (\sigma(d), p, r) : (p, r) \in C(s_d)\}$$
where $C(s_d)$ = valid (piece, rotation) at position $\sigma(d)$
given $\pi$ and not in $U$. "Valid" = satisfies border constraints
+ matches **at least zero** placed neighbors (mismatches allowed).

Score update on transition: $\text{score}(s_{d+1}) = \text{score}(s_d) + \Delta$
where $\Delta$ = matched edges between $\sigma(d)$'s newly-placed
piece and its already-placed neighbors.

Beam: $S_{d+1} = \text{topK}_K(\bigcup_{s_d \in S_d} S'_{d+1}(s_d))$.

Final: $\arg\max_{s \in S_{256}} \text{score}(s)$.

## Complexity

At each depth $d$:
- $|S_d| \leq K$.
- $|C(s_d)|$ depends on $d$: corners (d<4): 4 piece-class candidates × 4 rotations × class-filter. Border (d<60): ~56 candidates. Interior (d>60): ~196 candidates × 4 = ~784.
- Children at depth $d+1$: up to $K \times |C|$.
- Sort + truncate: $O(K |C| \log(K|C|))$.

Total: $O(256 \cdot K \cdot 784 \cdot \log(K \cdot 784))$ ≈ $K \cdot 256 \cdot 10000$ ≈ $K \cdot 2.5M$.

At K=1024: 2.5G ops ≈ 2-10 seconds in Rust.

## Diversity

Pure top-K-by-score collapses: after ~20 depths, many of the K states
share an identical high-scoring prefix. Diversity preservation options:

1. **Used-mask deduplication**: hash $(U, \text{last-few-cells})$ and
   only keep one representative per hash bucket. Cheap.
2. **Lexicographic-distinct-prefix**: require that no two beam states
   have identical first-k-placements. Stronger.
3. **Random selection from top-2K**: keep top-K but randomize selection
   from the top-2K. Soft diversity.

Start with (1); add (3) if collapse is observed.

## Falsifiable claims

| Claim | Expectation |
|-------|-------------|
| K=1 reproduces V150 baseline (max ~408 in 50k random seeds) | Yes by construction; K=1 = greedy, but with single seed |
| K=64 beats K=1 single-seed max by ≥ +5 | Yes; beam is strictly stronger than greedy at K=64 |
| K=1024 reaches max ≥ 430 in 60s | Hypothesised |
| K=1024 reaches max ≥ 463 (current record) | Aspirational; would be a from-scratch record break |

## Connection to existing concepts

- V150 WEAVING: K=1 special case.
- DFS row-major: K=1 with edge-strict (mismatch not allowed); we
  relaxed to allow mismatches.
- Beam search on TSP / SAT / etc: well-known. **The novelty is
  applying beam search to EDGE-MATCHING POLYOMINO PACKING with
  bounded inventory.** Inventory constraint distinguishes this from
  pure beam-search-on-CSP (which allows reuse).

## Day-1 deliverable

`crates/bench-audit/src/bin/v151_weaving_beam.rs` — Rust binary.
Args: `--puzzle`, `--beam-width K`, `--scan {row,col}`, `--budget-ms`.
Output: best score, # beam states explored, final beam diversity.

## Linked

- [[weaving-consensus]] (V150 parent)
- [[vol-151]]
- [[INVENTION_NAMES_2026-05-19]]
