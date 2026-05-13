# RESEARCH_NOTES_20.md — vol-20: breaking the 457 operator-lock

Date opened: 2026-05-13.

## Why this volume exists

Vol-18 reached **457/480** (cold-start record) and ran into a hard wall:
hot-PT at T=30, T=50, T=100 all failed to even *propose* a +1 move from
a 457 board. "Operator-locked" was the verdict.

Catalog audit at vol-20 open (Explore subagent, 2026-05-13):

- **14 ALNS destroy operators, 1 axis.** Every op picks *positions* to
  free. None varies rotation, none varies piece identity, none varies
  a non-positional coordinate.
- **1 representation.** Variables are `(piece, rotation) ↦ (row, col)`.
  No equivalent search on the edge grid, color identities, piece-rotation
  orbits, or row permutations.
- **1 objective.** Matched edge count + (vol-17) component-size tie-break.
  Nothing else.

R5e (vol-18) found that the 447→456 transition is a coordinated 76-cell
σ-cycle move with no monotone single-piece path: every individual cycle
has Δ<0. **Single-axis position-ALNS cannot see that move as anything
but uphill, regardless of temperature.** The 457 ceiling is the same
shape one rung up.

Vol-20 mission: build **operators on new axes** so the search space we
explore at the plateau is genuinely different from what got us to 457.

## Direction map (vol-20 candidates)

Selected for vol-20 execution: **N3, N4, N5, N6**.

| # | Name | Axis | Cost | Status |
|---|------|------|------|--------|
| N3 | Rotation-only sweep | rotation | 30 LOC | **in progress** |
| N4 | S_256 transposition SA | piece permutation | 1 day | queued |
| N5 | Local tensor contraction at stuck cells | exact patch marginals | 1 day | queued |
| N6 | Cross-family backbone extraction | ensemble priors | 2 hours | queued |

Parked for later (full list at end of file): N1 (edge-grid dual ALNS),
N2 (color-relabel SA), N7 (Eulerian color-flow propagator), N8 (real
PT tabu), N9 (piece-orbit atoms), N10 (hardness map).

## Loop

Each entry below follows: **experiment → observe → learn**. Honest n≥3
where claims are made. Single-run results go under "needs replication".

---

## 2026-05-13 — vol-20 opens

Notes file initialized. Starting N3 rotation-only sweep first because
it is a 30-line probe that should have been run before vol-18 closed.

