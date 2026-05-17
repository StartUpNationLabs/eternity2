---
name: method-vs-record-divergence
description: "Vol-123 insight: record-breaking and method-finding diverge. McGavin's 469 uses Blackwood, a heuristic that won't generalize to 480. The path to SOLVING is to make marginals progressively more accurate. W1 PEPS + cloud compute is the leading candidate."
metadata:
  type: project
---

# Method-vs-record divergence

User clarified vol-123: goal is "the way to solve", not records.

## The divergence

Record-holders (McGavin 469, Verhaard 467, Blackwood 467) all use methods
that are **heuristic** — they don't scale to a SOLVE. They're tuned for
"get high matched edges in available compute" not "find a 480 solution".

Specifically:
- McGavin used Blackwood's algorithm: brute force + 3 pruners + scheduled
  relaxations. 12 days on a workstation. Reaches 469 but no obvious path
  to 480.
- ALNS, simulated annealing, genetic algorithms all suffer the same: they
  improve scores but cannot CERTIFY a 480 or systematically search.

**Our incremental score-improvement attempts (vols 1-122) reproduce this
pattern.** We've measured: 459 → 460 is essentially as hard as 469 → 480.

## The path to actually SOLVING

A method that could SOLVE Eternity II must have one of these properties:

1. **Exact in the limit**: with infinite compute, would find the solution
   guaranteed. (E.g., DLX exact cover, exhaustive search with bounded
   look-ahead.)

2. **Provably correct marginals**: produces marginals that, in the limit
   of more compute, become accurate enough that CSP can complete from them.
   (E.g., PEPS at chi → infinity, generalized BP at region size → infinity.)

3. **Theoretical reduction**: reformulate the problem as something
   provably solvable. (E.g., embed in a known polynomial-time class via
   structure exploit.)

Our W-series candidates fit category (2):
- **W1 PEPS-Lagrangian**: marginals are accurate to O(epsilon) where epsilon
  decreases with chi. At chi → infinity, exact. Memory limits chi at
  canonical scale on laptop.
- **W2 BP-decimation**: marginals are 1st-order approximations. Cannot
  refine without going to GBP/region BP.
- **W3 Vandermonde-LP**: LP relaxation gives marginals via dual variables.
  Tightness depends on the LP polytope formulation.

## Why W1 is the leading candidate

- W1 is **provably correct in the limit** (chi → infinity).
- The 4×4 and 6×6 results demonstrate that W1 actually solves at small scale.
- The bottleneck is compute (chi-truncated boundary MPS at chi=128+ on
  canonical needs 64-128 GB RAM, available on cloud).

**The path to solving E2 via W1**:
1. Run W1 on canonical 16×16 at chi=64-128 with cloud compute (~$50-100).
2. Dump per-cell-piece-rotation marginals.
3. Feed marginals as value-order to CSP (solver-engine, joe_depth150_par).
4. If marginals are accurate enough, CSP completes to 480.
5. If marginals are insufficient, increase chi (more compute).
6. Iteration converges to the solve as chi → ∞.

## Why simply running ALNS forever won't solve

ALNS is a **local search** — it explores the score landscape. The score
landscape of E2 has many local maxima around 459 (vol-65 σ-orbits, vol-22
escape pipelines). Each ALNS run hits these and gets stuck.

To escape, you need either:
- Massive compute (exhaustive search beyond local maxima) → not feasible
- A method that doesn't get stuck (W1/W2/W3 style, exact in the limit)

## Standing 458 strict-canonical record

Vol-122's 458 record was found by combining different basins via signature
matching. It's a strong empirical result but doesn't represent a NEW
algorithmic method.

To beat the community 469 cleanly, we need W1/W2/W3 to converge at
canonical scale.

## Linked

- [[w1-peps-design-derivation]]
- [[w2-bp-pipeline-result]]
- [[SOLVING-E2-VISION]]
- [[w1-was-it-promising]]
