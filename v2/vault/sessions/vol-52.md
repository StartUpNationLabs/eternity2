# Vol-52 — lifted-LP per-piece column-gen design document

**Theme**: After 6 negative-result volumes (46-51) on record-breaking
tracks, pivot to research-grade design work. Vol-52 produces a
careful design document for lifted-LP via per-piece decomposition —
the structural alternative to vol-47's failed McCormick approach.

**Status**: CLOSED 2026-05-15 — design document shipped, no code,
captures the LP-tightening path that addresses the integer gap.

## What was shipped

[[lifted-lp-column-gen-per-piece]] — a ~400-line concept
page covering:

1. The problem (vol-50 LP-integer gap motivation).
2. Why per-piece decomposition is structurally different from
   vol-47's McCormick (decomposable subproblems vs monolithic lifting).
3. Lagrangian dual formulation (primal x, y; dual λ per piece).
4. Column-generation alternative (Dantzig-Wolfe equivalent).
5. Worked example sketch at 6×6/5c.
6. Scaling estimate to 16×16/22c: 10 min - 1h per basin.
7. Engineering cost: 7-10 days for a measurable result.
8. Comparison to vol-47 McCormick (table).
9. Open questions for any future build.

## Findings

### F1. Per-piece decomposition is the correct approach

Vol-47 lifted by adding O(n²) auxiliary variables (McCormick on
binary products). Per-piece decomposition KEEPS the same LP variables
but decomposes the constraint structure. Subproblems are independent
and parallel; master is still standard LP.

This is the standard route for integer programming with hard
coupling constraints. We've been on the wrong path with McCormick.

### F2. Expected payoff is partial gap-closure, not record-break

Per-piece column-gen would close the ~12 points of the 20-point gap
attributable to piece-uniqueness joint-infeasibility (vol-50
[[lp-integer-gap-anatomy]]). The remaining ~6 points are in
fractional LP y-values, closeable separately by Gomory/clique cuts.

**This doesn't directly produce a 459 record.** Vol-44 already proved
the 458 board is integer-optimal under 28-cell + 196-cell MIP. A
tighter LP UB confirms (not breaks) the record.

What it DOES produce:
- Optimality certificate per basin (provable integer optimality).
- Tighter CSP search bound for future record-breaking attempts on
  fresh borders.
- Foundation for no-good CDCL learning.

### F3. Engineering cost: 7-10 days

Contained build:
- Reuses good_lp + HiGHS already in v2/.
- Reuses vol-44 border_ub.rs infrastructure.
- Per-piece subproblem solver is trivial enumeration.

Risks: numerical stability of subgradient at 196-dim λ. Mitigation:
column-gen variant gives finite termination.

## Decision: vol-53+ would BUILD this

The design is ready. The build is contained. The expected payoff is
durable optimality certificates per basin.

Vol-52's mode is design-only; vol-53 (or whenever the autonomous
loop next has 7-10 days) can pick this up.

## Vol-52 process notes

This vol-52 was opened MID-AUTONOMOUS-RUN after vol-51 closed with
"recovery is the bottleneck" — recognising that further small-scale
infrastructure experiments would be more comfort-lottery. Pivoting
to math + design is the senior-researcher move per CLAUDE.md.

The doc itself was written in ~30 minutes after the math was
clear in my head. Time budget for vol-52 (2 days max) was used
in ~30 min because the design is structurally simple once McCormick
is ruled out.

## Open frontiers for vol-53+

1. **BUILD per-piece column-gen** (this vol's design): 7-10 days.
2. **LNS-style recovery for vol-51 B1 bound-trigger**: 1-2 days.
3. **Vol-25 perf backlog**: ~20% on joe_depth150_bp; engineering.
4. **No-good CDCL learning**: multi-week, high-EV unbuilt.

## Linked

- [[lifted-lp-column-gen-per-piece]] — the design doc
- [[lp-integer-gap-anatomy]] — vol-50 motivation
- [[lifted-lp-formulation]], [[lifted-lp-column-generation]] — vol-47 predecessors
- [[vol-50]], [[vol-51]] — recent sessions
