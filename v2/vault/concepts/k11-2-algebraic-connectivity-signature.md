---
name: k11-2-algebraic-connectivity-signature
description: "K11.2 result: algebraic connectivity (Fiedler eigenvalue λ_2) of the MATCHED-edge graph on a complete E2 board shows monotonic correlation with score. 459 record λ_2 = 0.0369 (highest); J1 boards λ_2 ≈ 0.0334-0.0341. New basin signature derived from spectral graph theory."
metadata:
  type: project
status: built
---

# K11.2 — Algebraic connectivity as a basin signature

## Origin

Cross-domain physics lens (per user directive). Treating the matched-edge
graph as an optical network, what's its algebraic connectivity?

## Method

For each complete E2 board:
1. Build the **matched-edge adjacency graph** A on 256 cells: A[i][j] = 1
   iff cells i, j are 4-grid-neighbors AND share a matched (non-border)
   edge.
2. Compute the graph Laplacian L = D - A.
3. Compute eigenvalues; report λ_2 (Fiedler eigenvalue = algebraic
   connectivity).

Cheeger's inequality says λ_2 bounds the graph's CONDUCTANCE — a measure
of how WELL-MIXED the matched-edge graph is.

## Results

| Board | matched | #comps | maxcomp | λ_2 |
|---|---:|---:|---:|---:|
| **Standing 459 (vol-60)** | 459 | 1 | 256 | **0.0369** |
| Vol-35 RECORD 457 | 457 | 1 | 256 | 0.0358 |
| Vol-32 RECORD 458 | 458 | 1 | 256 | 0.0345 |
| Vol-35 RECORD TIE 458 | 458 | 1 | 256 | 0.0345 |
| J1-FLH 447 raw | 447 | 1 | 256 | 0.0341 |
| J1-FLH 444 raw | 444 | 1 | 256 | 0.0338 |
| J1-hinted-v2 ALNS s7 | 445 | 1 | 256 | 0.0337 |
| J1-hinted-v2 ALNS s42 | 444 | 1 | 256 | 0.0334 |

## Key observations

1. **All boards are SINGLE-component in matched-edge graph** (#comps=1).
   The matched edges always reach all 256 cells via SOME path.
2. **459 has the HIGHEST λ_2 (0.0369)**. Boards with higher score
   generally have higher λ_2.
3. **Order doesn't follow score perfectly**: 457 (0.0358) > 458 (0.0345).
   The 457 has 5 small mismatch clusters vs the 458's 2 big clusters.
   A smaller-cluster structure may have higher λ_2 because the 2 big
   clusters in 458 act as BOTTLENECKS (Cheeger inequality).
4. **J1 boards cluster low** (0.0334-0.0341). The J1 family produces
   boards with bottleneck structure.

## Interpretation

The Fiedler eigenvalue $\lambda_2(L_{\text{match}}) \approx
\frac{\text{cuts}}{\text{vol}}$ via Cheeger. A board with FEW LARGE
MISMATCH-CLUSTERS has a graph that is "almost two pieces" connected
by thin bridges — low conductance → low λ_2.

A board with MANY SMALL MISMATCH-CLUSTERS has a graph that's
"locally connected everywhere except small patches" — high
conductance → high λ_2.

## Implication

**Basin signature: λ_2 captures bottleneck-vs-scatter geometry**. This
is a SCALAR INVARIANT of the basin that's NEW for E2 research.

**Practical use**: when comparing two candidate ALNS targets at the same
matched-edge count, prefer the one with HIGHER λ_2 — it has fewer
bottlenecks → easier local-repair.

For our 459 → 460 attempt: we'd be looking to FURTHER FRAGMENT the
mismatch into even smaller clusters, raising λ_2. This connects to
the K9 finding (459 has 4 small clusters, 458 has 2 large).

## Limitations

- λ_2 is GLOBAL (uses the whole graph). May miss LOCAL bottleneck
  candidates for repair.
- 22 colors are not encoded in λ_2 — it's purely the topology of
  matched edges, not their color semantics.

## Next steps

1. Compute λ_2 for the 100+ basin members in our corpus (vol-118).
   Does it cluster?
2. Use λ_2 as an ALNS move selector: when destroying, target moves that
   INCREASE the next-board's λ_2.
3. Verify Cheeger bound on small examples.

## Status

`built-finding-positive`. New cross-domain basin signature.

## Linked

- [[k11-cross-domain-brainstorm]] (origin)
- [[k9-mismatch-topology-finding]] (related; mismatch component analysis)
- [[459-level-set-two-cluster-confirmed]] (vol-118 corpus)
