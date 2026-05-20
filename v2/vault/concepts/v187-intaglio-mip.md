---
name: v187-intaglio-mip
description: Naming: INTAGLIO-MIP — the engraver's exact cut on the mismatch band, by integer linear programming.
status: unbuilt
metadata:
  type: concept
---
# V187 INTAGLIO-MIP — Full Mismatch-Band MIP

Status: `unbuilt` — design only.
Origin: vol-187 (after V186 row-rigidity refutations).
Naming: **INTAGLIO-MIP** — the engraver's exact cut on the mismatch band, by integer linear programming.

## Motivation

V186 proved V181's 460 is row-locally rigid up to 3-row joint swaps (beam-DP at K up to 50000). But beam-DP is **incomplete** — it could miss valid chains the beam cutoff drops. Only an exact solver (MIP) can prove the basin is *truly* rigid at the relevant scale.

Also: V186 stopped at 3 rows because beam-DP becomes intractable at 4+ rows. MIP scales much better for these joint problems.

V187 builds an **exact integer linear program** that searches the full mismatch band (rows 11..14 = 64 cells) for the optimal joint placement.

If MIP returns the original placement: rigorous proof of 4-row local optimality.
If MIP returns a +1 placement: V186 missed it AND we have a record.

## MIP formulation

### Decision variables

Let $V$ = set of cells in the mismatch band: rows $r \in \{11,12,13,14\}$, columns $c \in \{0,..,15\}$ → 64 cells.

Let $P$ = set of free pieces: 256 minus pieces placed in rows $\{0..10, 15\}$ → 64 pieces.

For each $(v, p, r) \in V \times P \times \{0,1,2,3\}$:

$$
x_{v,p,r} \in \{0, 1\}
$$

$x_{v,p,r} = 1$ iff piece $p$ in rotation $r$ is placed at cell $v$.

### Constraints

**C1 (cell-uniqueness)**: each cell holds exactly one (piece, rotation):
$$
\sum_{p \in P, r \in \{0,1,2,3\}} x_{v,p,r} = 1 \quad \forall v \in V
$$

**C2 (piece-uniqueness)**: each piece used at most once across the band:
$$
\sum_{v \in V, r \in \{0,1,2,3\}} x_{v,p,r} \leq 1 \quad \forall p \in P
$$

(The band has 64 cells and 64 free pieces, so C2 is equality at optimum.)

**C3 (border alignment)**: cells at $c=0$ have W-edge BORDER, cells at $c=15$ have E-edge BORDER. Forbid $(p, r)$ assignments that violate.

**C4 (north boundary)**: cells at $r=11$ must have N-edge matching row 10's S-edges. Forbid $(p, r)$ that violate.

**C5 (south boundary)**: cells at $r=14$ must have S-edge matching row 15's N-edges. Forbid $(p, r)$ that violate.

### Objective: maximize matched edges within the band + on its boundaries

We model E-W match indicators $y_{v,v'}$ for horizontally adjacent cell pairs:

$$
y_{(r,c),(r,c+1)} = 1 \iff E(\text{piece at }(r,c)) = W(\text{piece at }(r,c+1))
$$

Similarly N-S match indicators $z_{v,v'}$ for vertically adjacent cell pairs (rows 11-12, 12-13, 13-14).

Linearise via:

$$
y_{v,v'} \leq \sum_{(p,r) : E(p,r) = \text{color } c^\star} x_{v,p,r}
$$

(more elaborate: enumerate compatible (p_1, r_1, p_2, r_2) pairs and sum the joint indicators).

Or, simpler: use **edge-color flow** variables on the boundary.

For simplicity, we use a **bilinear-implied** formulation: $y_{v,v'} = \mathbb{1}[\text{edges agree}]$ computed via a McCormick linearisation per adjacent pair.

### Objective

$$
\max \sum_{(v,v') \text{ H-adj}} y_{v,v'} + \sum_{(v,v') \text{ V-adj}} z_{v,v'} + \text{(N-match row 11)} + \text{(S-match row 14)}
$$

The constant terms from N/S boundary matches that DO hold in any feasible solution are added to the objective.

### Symmetry / warm-start

The current board's row 11..14 placement is a feasible solution with score = original-band-contribution-score (94 for rows 11-13, 89 for 12-14, ~120 for 11-14).

Warm-start the MIP with this solution; HiGHS will improve if possible.

## Implementation plan

1. Parse the V181 460 board, identify rows 11-14 cells + free pieces.
2. Build HiGHS model with x, y, z variables.
3. Set warm-start = original.
4. Solve with time limit 30 min.
5. Check returned objective vs warm-start objective.

## Expected outcome

If MIP returns same score as original → V181 460 is **4-row MIP-locally rigid** in the full mismatch band. This is the strongest possible structural rigidity proof at row-band granularity.

If MIP returns better → record break + V186 row-swap was beam-incomplete.

## Compute estimate

Variables: $|V| \times |P| \times 4 = 64 \times 64 \times 4 = 16384$ binary x.
Plus $\sim 16 \times 3 \times |\text{color}| = $ a few thousand y/z variables.
Constraints: ~64 + 64 + 64 (border, north, south) + 16384 (border-bad-rot forbids) + linearisation.

HiGHS can handle 10⁵ binary vars with LP relaxation guidance.

## Linked

- [[row-level-rigidity]]
- [[basin-460-cp0312-v181]]
- [[three-basin-iso-plateau]]
- [[vol-186]]
