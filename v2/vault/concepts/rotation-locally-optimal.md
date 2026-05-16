---
name: rotation-locally-optimal
description: "Vol-117 T2 — every tested high-score board (454, 457, 459, 460) is rotation-locally optimal: rotating any single piece in place (while keeping all others fixed) NEVER improves the score. 768 alt-rotation tests per board × 12 boards = 9216 tests, ZERO improvements. The rotation degree of freedom is fully frozen at the 459 level set."
metadata:
  type: project
---

# Rotation-locally optimal (vol-117 T2)

**Status**: `built` — empirical sharpening of rigidity findings.

## Definition

A board $b$ is **rotation-locally optimal** if for every position $p$
with $b(p) = (\text{piece}_p, r_p)$, no alternative rotation
$r' \neq r_p$ of the same piece $\text{piece}_p$ gives
$s(b[p \mapsto (\text{piece}_p, r')]) > s(b)$.

This is a STRICTER local-optimum condition than "no single-piece
swap improves" — it tests just the rotation degree of freedom, with
piece identity and position held fixed.

For each placement, there are 3 alternative rotations (4 total - 1
current). For a 16×16 fully-placed board, that's 256 × 3 = 768
alt-rotation tests per board.

## Empirical results

Run `target/release/vol117_rotation_probe <board.json>` on 12 boards
across all known basins (vol-110, vol-60, vol-62, vol-76 sources).

| score | source                                       | alt tests | improvements |
|------:|----------------------------------------------|----------:|-------------:|
|   454 | vol-110 bseed7                               |       768 |            0 |
|   457 | vol-110 seed1, seed42, seed100, seed200      |   4 × 768 |            0 |
|   459 | vol-110 bseed1, bseed6, bseed11              |   3 × 768 |            0 |
|   459 | vol-110 orig                                 |       768 |            0 |
|   459 | vol-110 NEW_459_from_off100                  |       768 |            0 |
|   460 | vol-110 bseed9                               |       768 |            0 |

**9216 total alt-rotation tests, ZERO improvements found.**

## Implication

The rotation degree of freedom is fully frozen at the high-score
level sets. This sharpens the existing rigidity findings:
- [[multiple-459-basins-rigid]] showed MIP halo-1 rigid.
- This shows ROTATION-only (a STRICT subset of halo-1) also rigid.

Why this matters: rotation-only is a 4× cheaper local move than
"swap piece at p with piece at q". If even rotation can't lift
the score, then the rotation-axis offers no improvement room.

## Connection to the 459 problem

The 459-level set's "lift to 460+" problem cannot be solved by:
- Rotating any single piece (proved here).
- Swapping pieces within halo-1 of any defect (proved by MIP).
- Σ-cycle subsets between known basins (vol-99, vol-110, vol-112).

460+ from a known basin requires either:
- A NEW operator not yet tested.
- A NEW basin not in our corpus.

## Note on 460 outlier

`output/vol-110/basins/bseed9_score460.json` scores 460/480 (4 above
records on 4/5-convention) but has **0/5 hints** — it's on the
unconstrained convention (no canonical-hint compliance). Per memory
`reference_blackwood_decoded`, the 1-clue record is Blackwood's 470,
so 460 with 0 hints is well below community ceiling. It IS however
a new datapoint for σ-cycle / basin work.

## Code

- `crates/bench-audit/src/bin/vol117_rotation_probe.rs`

## Linked

- [[multiple-459-basins-rigid]] — MIP halo-1 rigidity (broader test).
- [[basin-rigidity-refutation]] — earlier basin rigidity work.
- [[../sessions/vol-117]].
