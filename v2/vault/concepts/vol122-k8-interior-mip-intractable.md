---
name: vol122-k8-interior-mip-intractable
description: "Vol-122 K8 TIMF (Targeted Interior MIP) result: 30min HiGHS timeout. No feasible integer solution found. MIP intractable at canonical scale."
metadata:
  type: project
status: refuted
---

# Vol-122 K8 — Interior MIP intractable at canonical scale

## Setup

Targeted Interior MIP (TIMF) on vol-122 perm0_444 board:
- Fix 60 border cells.
- Search integer-optimal interior assignment over 196 cells × 196 pieces × 4 rotations = ~153,664 binary x variables + ~7-8k y variables.
- Total 13,188 rows × 159,908 cols × 899,200 nonzeros.
- HiGHS solver, 4 threads, 1800s time limit.

## Result

After 1816 seconds:
```
status: Optimal
objective (II + IB matches): 0.0
+ 60 BB = total: 60
```

The "Optimal" status is misleading — HiGHS returned without finding any
feasible integer solution. Objective 0 means it couldn't place any piece
(violates the cell-coverage `=1` constraints), so the reported optimum
is invalid.

## Interpretation

**The interior MIP is intractable at canonical scale within practical
time budgets.** Confirms what vol-44 / vol-62 noted: integer MIPs on
canonical-size E2 problems with full piece freedom are too large for
modern solvers within minutes.

## What it rules out

Using interior MIP directly to find an integer-optimal arrangement
given a fixed boundary — at least with HiGHS, default settings, 30 min.

## What's still possible

- Longer compute (hours/days).
- Stronger LP relaxation + cutting planes.
- Column-generation / Benders decomposition.
- Region-restricted MIPs (vol-119's corpus-restricted MIP is this:
  works because vars-to-pieces is restricted to a known corpus).

## Status

`intractable-at-canonical-scale`

## Linked

- [[vol122-25-edge-gap-is-all-interior]] (the question this MIP tried to answer)
- vol-44 LP-UB (per-cell-pair, LP only)
- vol-119 corpus-restricted-region-mip-locked (succeeds with restricted vars)
