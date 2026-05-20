---
name: j1-backward-multiset-constraint
description: "Backward multiset constraint for J1: when row r commits its bottom-color vector, that vector must be a multiset-subset of the available pieces' rotated-top-color vector. Backward induction reveals this constraint at every band."
metadata:
  type: project
status: built
---

# J1 — Backward multiset constraint

## Setup

J1 forward beam search at band $r$ commits to the bot-row's bottom-color
vector $\mathbf{b}_r \in \mathcal{C}^{16}$. This vector must satisfy:

$$
\forall c \in \{0..15\}: \exists p \in \mathcal{R}_{r+1}(\text{state}) \text{ such that } p \text{ has top color } b_{r,c} \text{ in some valid rotation}.
$$

Where $\mathcal{R}_{r+1}$ is the piece pool available for row $r+2$
(after band $r+1$ consumes its share).

## Multiset formulation

Let $M(\mathbf{b}_r)$ = multiset of $b_{r,c}$ over $c = 0..15$.
Let $T(\mathcal{R})$ = multiset of (piece, rotation, top-color) tuples
where bot-color of the rotation = 0 (border-bottom for ROW 15) or some
other constraint for inner rows.

For band $r$ at the bottom-row interface, the feasibility condition is:

$$
M(\mathbf{b}_r) \preceq T(\mathcal{R}_{r+1}) \quad (\text{multiset inclusion})
$$

This means: the multiset of needed-top-colors (= bot-color of current
band's bot-row) must not exceed the multiset of available top-colors
from the future piece pool (when those pieces are rotated to have
bot=0 for border, or any rot for inner).

## What J1's forward beam doesn't see

J1's beam doesn't track the future piece pool's MULTISET; it only tracks
the SET of used pieces (via `PieceSet`). The supply-LP bound used by
[[inv-b4-hall-color-pair-refuted]] is the right tool but it
operates at the LP level, not within the beam.

## Backward induction

The constraint propagates BACKWARD:
- Band 14 needs: bot=0 (border), top=row 14 bot. This is the row-14/15 interface.
- For band 14 to be feasible: M(row 15 needed-tops) ⊆ T(piece pool after band 13).
- For band 13 to be feasible given band-14 feasibility: row 14 bottoms must
  be expressible from a piece pool that ALSO has enough "right" pieces
  for row 15.
- ... and so on backward.

This is a constraint-propagation problem: each band imposes a constraint
on the pieces it can use AND a constraint on what the bot-row's color
multiset must be.

## Polynomial-time check

Given a J1 board partial up through band $r$, computing the feasibility
of band $r+1$ requires checking $M(\text{bot-row}) \preceq T(\mathcal{R})$.
This is $O(|C|)$ where $|C|$ = #colors (= 22 for canonical E2).

## v3 algorithm (sketch)

Define **multiset-aware FLH**: at each band $r$, when choosing among
top-$K$ states, compute:

$$
\text{multiset\_score}(s) = \sum_c \min(1, \text{count}_T(b_{r,c}, \mathcal{R}_{r+1}(s)) - \text{count}_M(b_{r,c}, \mathbf{b}_r))
$$

Sum is +1 per column whose needed-top has at least 1 free piece that
could match. If a column's needed-top has 0 free pieces, multiset_score
goes negative (or 0 with sign indicator).

State selection: `flh_score * 100 + multiset_score * 10`.

## Cost

Per state: $O(|C| + 16) = O(|C|)$. For top-K states at last band:
$O(K \cdot |C|)$ = $O(100 \cdot 22) = O(2200)$ ops per band. Trivial.

## Expected gain

If multiset-FLH consistently produces band-14-feasible states, J1-hinted
v3 should complete to 256 cells with 5/5 hints. Score uncertain.
Optimistic: 420-440. Pessimistic: 410-420 (no gain).

## Caveats

- Even if M(needed) ⊆ T(supply), the pieces might not be POSITION-compatible
  (left-right matching within row 15). Multiset is necessary but not sufficient.
- Bidirectional matching (multiset on TOP and BOT simultaneously) is harder.

## Status

`design-complete-implementation-pending`.

## Linked

- [[j1-hinted-v2-corner-color-bug]]
- [[j1-forward-look-heuristic]]
- [[inv-b4-hall-color-pair-refuted]]
