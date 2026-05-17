---
name: k10-kuramoto-design-issues
description: "K10 Kuramoto coupled-oscillator for E2 — design analysis reveals the mapping isn't natural. Each cell would need a continuous phase, but the puzzle is fundamentally discrete (piece-id + rotation). Kuramoto-on-E2 collapses to XY model that doesn't map back to piece assignments."
metadata:
  type: project
---

# K10 — Kuramoto Coupled Oscillators (design issues)

## Origin

Per cross-domain directive, considered modeling E2 as a Kuramoto coupled-
oscillator network. Each cell = oscillator with phase $\theta_c$. Matched
edge = phase alignment.

## Design problem

The Kuramoto model:
$$
\dot{\theta}_i = \omega_i + K \sum_j W_{ij} \sin(\theta_j - \theta_i)
$$

For E2, we'd need:
- $\theta_c \in [0, 2\pi)$ per cell.
- $W_{ij}$ = +1 if cells $i, j$ are adjacent AND should match colors.
- Each piece-rotation should encode a specific phase pattern.

**The mapping breaks**: a cell's phase $\theta_c$ corresponds to WHICH
PIECE+ROTATION at that cell. But there are 256 pieces × 4 rotations =
1024 discrete states. Phase $[0, 2\pi)$ is continuous. Discretizing
phase into 1024 bins loses Kuramoto's continuous-relaxation advantage.

## Where Kuramoto-like dynamics WOULD work

The XY-model relaxation: assign each cell a continuous phase, minimize
$\sum_{i,j adj} (1 - \cos(\theta_i - \theta_j))$. This is well-defined
but DOES NOT MAP BACK to discrete piece-rotation choices.

## Conclusion

K10 Kuramoto-on-E2 does not provide new operational structure. The
discrete-continuous mismatch is fundamental. Refuted as a useful
cross-domain lens.

## What DOES work (per K11.2 and K11.4)

Graph-spectral methods (algebraic connectivity λ_2) and
information-theoretic compression of the mismatch map BOTH gave
NEW basin signatures. These don't try to RELAX the discrete problem;
they ANALYZE the discrete configuration via continuous tools.

## Status

`refuted-design`. Not pursuing implementation.

## Linked

- [[k11-2-algebraic-connectivity-signature]] (what worked)
- [[k11-4-mismatch-zlib-signature]] (what worked)
- [[k11-cross-domain-brainstorm]] (origin)
