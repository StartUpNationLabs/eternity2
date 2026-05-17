---
name: j1-multi-band-beam-search
description: "J1 extension: when multiple band-0 configurations achieve perfect score, try each as a starting point for band 1. Effectively beam-search at the BAND level too."
metadata:
  type: project
---

# J1 — Multi-Band Beam Search

## Observation (user-prompted, 2026-05-17)

The PoC achieves **perfect band-0 score (46/46)** with beam=5000 at
canonical 16×16. The beam keeps 5000 states at the final column, of
which (per measurement) **many** achieve the perfect 46 score.

These are **alternative configurations of band 0** that all tile rows
0 and 1 perfectly. They differ in:

- Specific pieces chosen at each cell.
- Rotations.
- Color sequences at the row-1 boundary (= what band 1's top row sees).

When we chain sequentially, we commit to ONE band-0 configuration — but
band 1 might require DIFFERENT band-0 colors to be perfect itself.

## Multi-band beam algorithm

State at the **chain level** is a band-$r$ completion, not a column-level
state.

```
ChainState = (r, bottom_row_pieces, accumulated_score, used_pieces_set)
```

At each step from $r \to r+1$:

1. For each ChainState at level $r$, solve band $r+1$ with the top row
   fixed to that ChainState's bottom row.
2. The band $r+1$ solver returns its OWN beam of top-$K_{band}$
   configurations.
3. For each (ChainState_r, band_{r+1}_config) pair, create a new
   ChainState at level $r+1$.
4. Beam-prune ChainStates by accumulated_score, keeping top $K_{chain}$.

Total ChainStates at level $r$: $\leq K_{chain}$.

Total band solves: $K_{chain} \cdot (n-1)$.

For $K_{chain} = 10$, $n = 16$: $10 \cdot 15 = 150$ band solves.
Each band solve costs $\sim 5$ s (per chain run timings).
Total wall: $\sim 750$ s $= 12.5$ min.

## Tractability vs single-chain

| Variant | Chain states tracked | Band solves | Wall-clock |
|---|---|---|---|
| Single chain | 1 | 15 | ~85s |
| Multi-band beam $K_{chain}=10$ | 10 | 150 | ~750s |
| Multi-band beam $K_{chain}=50$ | 50 | 750 | ~1h |

## Critical question

Does multi-band beam find a HIGHER total score than single chain?

The single chain achieved 423/449 on 240 cells (16 cells missing in
band 14 failure). Per-band degradation pattern:

- Bands 0-6: 46/46 (no loss).
- Bands 7-9: 45/46 (-1 each).
- Bands 10-13: 43, 42, 41, 35 (rapid decay).
- Band 14: 0 (failed).

The degradation happens AFTER band 6, suggesting band 6's bottom row
makes band 7 sub-optimal. Multi-band beam would try ALTERNATIVE
band-6 bottom-rows to see if any allows band 7 to remain perfect.

## Math

Let $f_r(s)$ = best total score achievable from ChainState $s$ at level $r$.

$$
f_r(s) = \max_{c \in \text{band\_configs}(s)} \left( \text{score}(c) + f_{r+1}(\text{next\_state}(s, c)) \right)
$$

This is dynamic programming over ChainStates. Beam-prune approximates.

## Expected outcome

If degradation is "borrow from future" (band 6 commits a row good for
6 but bad for 7), multi-band beam should AVOID those configurations
and pick band-6 bottoms that better serve band 7.

Hypothesis: total score with $K_{chain}=10$ reaches $> 450$ (vs single
chain 423). Could exceed 459 with sufficient beam.

## Implementation

Extends J1 chain script. Track top-$K_{chain}$ at chain level, each
ChainState recursively calls band-solver with appropriate fixed top.

## Linked

- [[j1-column-dp-design]]
- [[j1-poc-perfect-band-results]]
- [[j1-chain-band-decomposition-math]]
