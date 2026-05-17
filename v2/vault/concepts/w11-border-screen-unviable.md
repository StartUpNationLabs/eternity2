---
name: w11-border-screen-unviable
description: "Vol-124 conclusion: SAT-screen-per-border on canonical E2 cannot be a primary engine. Border space is ~10^7-10^9, per-border SAT is ~1.9s → enumeration would take ~22 single-thread years. W11 retires as a primary attack; remains useful as post-hoc verification (yes/no on a candidate in <2s)."
metadata:
  type: project
---

# W11 SAT-screen-per-border — unviable as primary engine

## Conclusion

**SAT-screen-per-border cannot be the primary attack on canonical E2.**

User observation (vol-124, 2026-05-17): *"There are billions of
possible puzzle borders."* Confirming:

| Quantity                                | Value          |
|-----------------------------------------|----------------|
| Border-DP space size (literature est.)  | 10^7 – 10^9    |
| Our coverage at chains-per-side=10      | 240 borders    |
| Coverage fraction                       | ~0.0024 %      |
| Per-border SAT time (kissat 5s budget)  | ~1.9s          |
| Full-enumeration single-thread time     | ~22 years      |
| Full-enumeration 1000-core time         | ~8 days        |

All-UNSAT at this coverage is not evidence of UNSAT globally — it is
just confirmation that the first ε% of the space is UNSAT.

## What W11 IS good for

- **Post-hoc verification.** When another algorithm proposes a
  candidate border, kissat returns SAT/UNSAT in <2s. This is a real
  capability and was not previously in the toolbox.
- **Sanity-check tests.** Detects encoder-correctness regressions
  (vol-124 found the pinned-pinned bug because of these tests).
- **Local proofs of infeasibility.** Halo-N UNSAT proofs on the 459
  basin showed it's truly locked (vol-123).

## What W11 is NOT

- A way to enumerate the right 480-border.
- A way to find new high-score basins.
- A way to decide solvability of canonical E2.

## Strategic implication

The next research direction is **whole-puzzle SAT** with a much
tighter encoding: symmetry breaking, LP-derived implication clauses,
multiple CDCL solvers. The 1h kissat run on the current encoding
(vol-124 background, PID 72166, no border pinning) is the baseline.

## Linked

- [[w11-sat-correctness-validated]] (encoder works)
- [[w11-sat-verified-border-enum]] (original invention page; amend)
- [[w-sat-459-unsat-findings]] (the local-halo UNSAT findings)
- [[../sessions/vol-124]] (full session)
