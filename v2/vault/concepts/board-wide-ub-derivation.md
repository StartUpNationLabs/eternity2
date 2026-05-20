---
name: board-wide-ub-derivation
description: Math derivation — combining per-row-window MIP UBs to derive a sound board-wide UB < 480 on canonical E2. Vol-105 T3 design.
metadata:
  type: project
status: partial
---

# Sound board-wide UB derivation from row-window MIPs

**Status**: `partial` — math worked out; row-window MIPs running vol-105.
**Related**: [[mcgavin-top4-mip-bounded]] (vol-86, top-4 ≤ 123).

## Definitions

Let the 16×16 board's 480 edges be partitioned into:
- `E_int(W_i)`: edges with both endpoints in row-window `W_i`.
- `E_bdy(W_i, W_j)`: edges with one endpoint in `W_i` and the other in
  `W_j` (only defined when `W_i, W_j` are adjacent in the partition).

For a partition into K disjoint row-windows:
- Total = Σ |E_int(W_i)| + Σ_{i,j adj} |E_bdy(W_i, W_j)|

For the standard 4-disjoint-4-row partition of a 16-row board
(W_0 = rows 0-3, W_1 = rows 4-7, W_2 = rows 8-11, W_3 = rows 12-15):
- |E_int(W_i)| = 4 rows × 15 + 3 inter-row × 16 = 60 + 48 = **108**
  per window. Σ = 4 × 108 = **432**.
- |E_bdy(W_i, W_{i+1})| = 16 per adjacent pair. 3 adjacencies = **48**.
- 432 + 48 = **480** ✓ (matches total edge count).

## Per-window MIP

For each window W_i, run the cluster-MIP from a reference board B:
- Pin cells outside W_i to B's pieces.
- Let pieces in W_i permute freely (Option A — within-cluster).
- Maximize `obj_in(W_i) + obj_bdy(W_i)` where `obj_bdy` counts edges
  to the pinned outside.

The MIP's LP relaxation gives a sound UB:
- `UB_LP(W_i) ≥ MIP-Opt(W_i) ≥ best feasible found`.

Vol-86 (top-4 of McGavin): `UB_LP(W_0) = 123, MIP-opt unknown, best
feasible = 116`.

## Combining

Two combinations to consider:

### Combination A: Pessimistic-on-boundary

Claim: `total_board_score ≤ Σ UB_LP(W_i) - (number of double-counted
boundary edges)`.

Each `obj_bdy(W_i)` counts edges from W_i to W_{i±1}. When summed
over all four windows, each cross-window edge is counted in BOTH
windows' obj_bdy (since W_i ↔ W_{i+1} appears in obj_bdy(W_i) and
obj_bdy(W_{i+1})). So:

Σ UB_LP(W_i) = Σ |E_int(W_i)|_LP + 2 × |E_bdy_total|

But total board = Σ|E_int| + |E_bdy_total|. So:

Σ UB_LP(W_i) = total_board_LP + |E_bdy_total|

Bound: `total_board_LP ≤ Σ UB_LP(W_i) - 48`.

Vol-86 alone: top-4 UB = 123 (one window). For 4 disjoint windows
with mean UB ≈ 120, sum ≈ 480. Adjusted: 480 - 48 = **432**. But
that's lower than achievable! Something is wrong.

### Error in combination A

The boundary edges in `obj_bdy(W_i)` count the W_i-to-out-of-W_i
edges where the out-of-W_i cell is *pinned* to its current board
value. These are NOT "all cross-window edges achievable" but
"cross-window edges given the pinned outside".

When we sum the per-window UBs (each computed against the SAME
reference board pinning), the cross-window edges that ARE matched in
B contribute to both `obj_bdy(W_i)` and `obj_bdy(W_{i+1})`. The MIP
doesn't add to them; they're constant under the per-window MIP.

So actually: `Σ UB_LP(W_i) = Σ UB_int(W_i) + 2 × |E_bdy_matched_in_B|`.

The COMBINED max score across all windows (with each window pinned
against B's other windows) ≤ Σ UB_int(W_i) + |E_bdy_in_B|. Not a
bound on the global max!

The per-window MIP gives:
- For each window i, the BEST you can do for matched_edges_within_or_touching_W_i if you're ONLY allowed to permute W_i (rest = B).
- This is a "local move" UB, not a global UB.

### Correct combination: cross-window edges as a separate term

Define for the global MIP a partition of edges. The sound bound is:

total_score = Σ matched(E_int(W_i)) + matched(E_bdy_total)

For a permutation where each W_i is permuted independently:
- matched(E_int(W_i)) ≤ UB_int(W_i) (LP relaxation of internal-only
  objective).
- matched(E_bdy_total) depends on BOTH W_i and W_{i+1} configurations.

For a true board-wide UB, we'd need:
- A UB on E_int(W_i) for each i — by LP relaxation with no boundary
  pinning, allowing the OUTSIDE to also vary.
- A UB on E_bdy_total — by a similar relaxation.

The simplest TRUE board-wide UB chain:

`score ≤ Σ_i UB_int_freeoutside(W_i) + |E_bdy_total|`

where `UB_int_freeoutside(W_i)` is the LP UB on internal edges of W_i
when only the W_i-piece-set is constrained (not the actual outside
pieces). This requires SEPARATE MIPs (no pinning of outside).

That's harder. Vol-86 used PINNED outside (which is fine for a
*local* bound around McGavin).

### Practical approach for vol-105 T3

Compute, for each W_i, the per-window UB **with pinned reference =
McGavin 469**. Report `(W_i, UB_LP_i, MIP_feasible_i, McGavin_actual_i)`.

Compute, for each W_i, the per-window UB **with pinned reference =
local-459**. Same triple.

The PINNED-OUTSIDE per-window UBs are valid for the question
"given the rest of the board fixed at THIS reference, what's the
max for this window?" — i.e., local rigidity from each window's
perspective.

If on local-459, UB_LP(W_3) < some value X, that means rows 12-15
contribute AT MOST X edges to global score (with rows 0-11 fixed at
local-459). So global score ≤ (current_rows_0_11 + X).

This IS a SOUND UB on "local-459 modulo bottom-4 permutation". It's
the same form as vol-86's UB on McGavin modulo top-4.

## Important correction to vol-86 claim

The PAPER 2026-05-16 states "first sound UB below 480 on canonical E2"
(citing vol-86: top-4 ≤ 123, total ≤ 476).

This is a sound UB on the SUBSET of solutions with rows 4-15 pinned to
McGavin's pieces in those positions. That's a SUBSET of canonical
5-clue solutions, not all of them. **An UB on a SUBSET is sound and
meaningful, but it's not an UB on the full puzzle.**

The PAPER's bound is "every solution that AGREES with McGavin on rows
4-15 scores at most 476". A 480 solution that differs on rows 4-15 is
NOT bounded by this argument.

To make a true unconditional UB ≤ 479, we'd need an UB that applies to
every canonical 5-clue solution — likely via Lagrangian
decomposition + per-window LP UB, summed correctly. Vol-105 T3 is
exploratory; the unconditional UB remains open.

## What vol-105 T3 measures

For each of 4 disjoint windows W_i (rows 0-3, 4-7, 8-11, 12-15) on
McGavin 469:
- LP-UB(W_i | McGavin-rest) — sound UB on W_i contribution.
- Sum over 4 windows = a sound UB on McGavin's global score modulo
  per-window permutations.

This is a SOUND UB IFF McGavin's actual permutation is what's
implicit in the pinning — i.e., the bound says "from McGavin, no
single-window permutation reaches > X".

The 4-window-sum is NOT a board-wide UB; it's a McGavin-local-rigidity
bound. But it's structurally meaningful: tells us how much "slack"
exists per window.

## Open: a true board-wide UB

To get a TRUE board-wide UB, we'd need:
- Free all 4 windows simultaneously, but then the MIP is the FULL
  board MIP (intractable at 16×16).
- OR: Lagrangian decomposition — couple windows via dual prices.
  Per IDEAS doc, this is the SDP/Lasserre route (untested at
  canonical scale).

## Linked

- [[mcgavin-top4-mip-bounded]] — vol-86 reference
- [[vol-105]]
- IDEAS doc: SDP relaxation (untried)
