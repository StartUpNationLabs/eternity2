---
name: vol122-cfcc-color-flow-propagator
description: "Vol-122 K3 — Color Flow Capacity Constraint (CFCC) PoC POSITIVE. New CSP propagator checks per-color frontier-demand vs unplaced-piece-supply. 2-2.7× node reduction on 7×7/c4-c5 and 8×8/c5."
metadata:
  type: project
status: built
---

# Vol-122 K3 — Color Flow Capacity Constraint (CFCC)

## Idea (new invention)

At each CSP search node, compute:

  demand_k = # frontier slots (placed-cell side facing unplaced cell) showing color k
  supply_k = sum of color-k edges across UNPLACED pieces

If demand_k > supply_k for ANY color k → INFEASIBLE → prune.

## Different from existing methods

- **AC-3 / gacolor**: propagate pairwise color compatibility per edge.
  Don't aggregate per-color demand vs supply across the whole frontier.
- **NS-1 (vol-11)**: multiset-equality deficit; static measurement.
- **vol-44 LP-UB**: per-color UB at start of search, not live.

CFCC is a **live cardinality propagator** on top of AC-3, checking
GLOBAL color supply at every search node.

## Results

| Puzzle | NO CFCC nodes | CFCC nodes | Speedup | CFCC prunes |
|---|---|---|---|---|
| 5×5/c4 | 11050 | 11050 | 1× | 56 |
| 6×6/c4 | 38844 | 38789 | 1× | 200 |
| 6×6/c5 | 1989 | 1989 | 1× | 2 |
| 7×7/c4 | 2.0M | 0.81M | **2.47×** | 4901 |
| 7×7/c5 | 1.6M | 0.77M | **2.11×** | 2307 |
| 8×8/c5 | 1.6M | 0.61M | **2.66×** | 7947 |

Wall-clock is 2× SLOWER currently because the demand-recompute is
O(n) per node. Incremental update (track demand delta on each placement)
would make this O(4) per node = net 2-3× speedup.

## Implications

For canonical 16×16, expect:
- Demand-vs-supply check at all 256 placements.
- Per-color (23 colors) ratio approaches 1.0 deeper in search.
- Late-stage prunes especially valuable (the deeper the better).

Combined with existing AC-3 / gacolor / NS-1, CFCC adds an orthogonal
propagator. Expect 1.5-3× additional speedup over current engine.

## Status

`PoC-positive` — needs incremental implementation in Rust for net speedup.

## Next steps

1. **Rust implementation as engine propagator**: add `cfcc` toggle to
   `EngineConfig`. Implement incremental demand-update on each
   place/unplace.
2. **Benchmark** vs current joe_depth150_par on canonical 16×16.
3. **Combine with FSMC** (J6) — both are orthogonal pruning mechanisms.
4. **Compare with NS-1** (vol-11) which is multiset-equality but global.
   Probably complementary.

## Linked

- [[vol-122]]
- [[INVENTIONS_BACKLOG]] — add K3 entry
- [[vol122-fsmc-rust-scaling-wall]] (J6, orthogonal)
- [[ns1-deficit]] (vol-11, related)
