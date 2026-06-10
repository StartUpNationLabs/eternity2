---
name: irreducible-hard-region-conjecture
description: "vol-208 meta-finding — every spatial decomposition of canonical E2 concentrates the difficulty into a Θ(n)-sized 'hard region' that exceeds the exact-solvable window (~112 cells), because piece-uniqueness is a GLOBAL irreducible coupling. Explains why ALL decomposition approaches in 208 vols (strips/bands J1, MOSAIC blocks, scaffolds, bidirectional A5, CAS rings) plateau ~447-462: the easy part fills freely, the hard part is too big to exact-complete and too coupled for heuristics."
status: built
metadata:
  type: concept
---

# The irreducible-hard-region conjecture (vol-208)

**Origin**: vol-208 (2026-06-10), the meta-conclusion of the TRANSEPT strip-
assignment investigation + the completability-threshold measurement. A synthesis,
not a single experiment.

## Statement
> For canonical 5-clue E2, **every spatial decomposition** into a sequence of
> regions (rows, bands, strips, blocks, concentric rings, corner-quadrants)
> concentrates the combinatorial difficulty into a **single "hard region" of size
> Θ(n) = Θ(16)** that (a) **exceeds the exact-solvable window** (~112 cells / 7
> rows, measured) and (b) is **too globally-coupled** (via piece-uniqueness) for
> heuristic completion to reach ≥ the from-scratch ceiling. Therefore no
> decomposition yields a tractable exact solve, and all plateau ~447–462.

## The evidence chain (all vol-208 unless noted)
1. **The easy part fills freely.** Sequential strip-fill (and KEYRING, MOSAIC, J1)
   fill the first ~10 rows / ~160 cells PERFECTLY from the rich pool
   ([[transept-strip-assignment]] Q3; [[completability-decision-threshold]]: <11ms
   exact down to 144 placed). The board is "near-free" until depth ~150.
2. **The hard region is Θ(n) and exceeds the exact window.** The residual difficulty
   localizes to the LAST region (bottom ~6 rows / 96 cells in strips; the meeting
   ring in bidirectional; the last corner in MOSAIC). Exact PERFECT-completion
   EXPLODES just past 112 free cells (128 free → >1.4M nodes, >3s,
   [[completability-decision-threshold]]). The hard region (~96–128 cells) sits
   right at / past the exact-solvable boundary. It cannot be shrunk below Θ(n)
   because any cut of the board leaves a Θ(n) interface.
3. **The hard region is globally coupled, not locally fixable.** Piece-uniqueness
   couples it to the whole board: scarce (N,W)-pair servers (33% unique,
   [[watershed-frontier-flow]]) spent in the easy part doom the hard part
   (piece-theft). The coupling caps co-realizable scarce demands at 92 but boards
   realize ~31 — the binding constraint is the global assignment, not anything
   local ([[scarcity-skeleton-shared-core]]).
4. **No assignment pre-pass resolves it.** TRANSEPT proved no SELECTIVE assignment
   objective exists (corpus prior vacuous: pieces float; color-balance vacuous:
   every partition satisfies it). So you cannot pre-allocate pieces to make the hard
   region easy.

## Why this explains 208 volumes of decomposition failure
Every decomposition family in the vault hits this:
- **J1 strips/bands** → band-12/14 wall (refuted). = hard region at the bottom.
- **MOSAIC blocks** → 448, defects in last corner. = hard region in last block.
- **Anjou scaffolds** → ~429–462, reconciliation seam loses 80–100. = hard region at the seam.
- **CAS concentric rings** → 433 greedy ceiling. = hard region at the inner ring.
- **Bidirectional A5** (unbuilt) → meeting ring is Θ(n), same problem.
- **KEYRING+ALNS** → ~460. = ALNS can't fix the globally-coupled tail.
All distribute the SAME irreducible Θ(n) hard region differently; none eliminate it.

## Status: CONJECTURE (strong empirical support, not proven)
- Empirically robust across 6 decomposition families + the exact-window measurement.
- NOT a theorem: "exceeds the exact window" is machine/algorithm-specific (a faster
  exact solver, e.g. a tuned Rust seqAMO-MaxSAT, might push the window to ~130–150
  cells — but the hard region is ~96–128, so even a 1.5× window improvement only
  reaches the boundary, not past it for the full bottom). The Θ(n)-interface part IS
  rigorous (any board bisection has a 16-cell+ interface); the "too coupled for
  heuristics" part is the empirical ceiling, not proven.
- **Implication**: a record/solution via single-machine decomposition is unlikely.
  The realistic paths remain: a NEW from-scratch paradigm that lands in a high novel
  basin WITHOUT a sequential hard-region (MOSAIC-class, but higher), or
  distributed-exact search.

## What would REFUTE it (falsifiable)
- A decomposition whose hard region is provably o(n) (sublinear) — none known.
- An exact solver whose window exceeds ~160 cells on canonical E2 (would let the
  full bottom-8 be exact-completed) — current edge-strict DFS explodes at 128;
  seqAMO-MaxSAT untested at that exact scale (worth measuring in vol-209).
- A heuristic that completes the globally-coupled tail to a NEW ≥464 basin — the
  KEYSTONE sweep is the current test.

## Linked
- [[transept-strip-assignment]] — the strip investigation that surfaced this
- [[completability-decision-threshold]] — the exact-window measurement (112 cells)
- [[watershed-frontier-flow]] — the global piece-theft coupling
- [[scarcity-skeleton-shared-core]] — 92-vs-31 (binding = global assignment)
- [[mosaic-window-maxsat]] — the one constructor that reaches NOVEL basins (the
  paradigm that might escape, if biased higher)
- [[sigma-cycle-universal-indecomposable]] — the local-move side of the same coin
- memory: `project_e2_vol208_conclusion_2026_06_10`
