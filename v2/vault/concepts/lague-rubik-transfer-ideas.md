---
name: lague-rubik-transfer-ideas
description: Algorithmic ideas transferred from Sebastian Lague's Rubik's Cube solver (staged subgoals, domino reduction = invariant-preserving move restriction, IDA* + pattern-DB admissible bounds, conservation-law parity pruning) to Eternity II.
status: unbuilt
metadata:
  type: concept
---

# Lague Rubik's Cube → Eternity II transfer ideas

**Origin**: vol-203 (2026-06-09). User added `vault/Sebastian Lague Rubiks Cube Optimization.md` as "food for thought" on algorithm optimization.

Lague's solver evolves COP (staged human method) → domino-reduction + IDA* with pattern databases, dropping avg solve from 13s/56-moves to 33ms/20-moves. His repeated thesis — **"searching faster doesn't get you far; the real trick is searching less"** — is exactly the user's E2 directive ("search-space reduction > search speed"). The transferable techniques:

## 1. Domino reduction = invariant-preserving move-set restriction (DEEPEST IDEA)

Once all edges are *oriented*, Lague **forbids the face turns that could un-orient them**, collapsing the group from ⟨all moves⟩ to ⟨moves preserving orientation⟩ (the "domino" subgroup ⟨U,D,L²,R²,F²,B²⟩). The puzzle becomes a strictly smaller sub-puzzle.

**E2 analog (new invention seed):** reach a partial invariant — e.g. a region that is **forbidden-patch-free** (0 forbidden 2×2/2×3, per [[forbidden-patch-theorem-2026-05-19]]) — then **restrict all subsequent moves to those that preserve that invariant**. This is *constructive* basin-locking, the dual of the (refuted) destructive basin-hopping. Crucially it sidesteps [[sigma-cycle-universal-indecomposable]]: instead of trying to *cross* between locked basins (impossible incrementally), build *into* a good basin by only ever making invariant-preserving extensions.

The connection to σ-cycles: the σ-cycle theorem says the residual symmetry group of a near-solution is large and dispersed. Domino-reduction is the move-group restriction that makes such a group *tractable to search within*. We have never restricted the E2 move group by a structural invariant — only by geometry (cell order).

## 2. IDA* with pattern-database admissible bounds

Lague precomputes lookup tables: "min #moves to fix this edge-orientation pattern" etc., and prunes with `h = max(table lookups)`. Tables are tiny (2048 entries) yet give huge pruning.

**E2 analog:** an IDA*-style MaxScore search with an **admissible lower bound on remaining mismatches**, precomputed as a pattern database keyed on a cheap sub-signature:
- forbidden-2×2 / 2×3 count (each forbidden patch ⟹ ≥1 future mismatch; [[forbidden-patch-theorem-2026-05-19]]).
- NS-1 Δ-invariant ([[ns1-deficit]]; Δ∈{0,1,2,4} correlates with score).
- per-color local deficit.
The `max` of several admissible signatures = a strong, cheap prune. **We have never used an admissible remaining-mismatch heuristic to prune E2 DFS** — current pruning is edge-strict feasibility only.

## 3. Conservation-law parity pruning

Lague: "impossible to solve a cube with just one edge flipped — the 12th edge's orientation is determined by the others." A parity conservation law halves the space and forbids whole classes of partial states.

**E2 analog:** the NS-1 Δ-invariant IS such a conservation law (Hopfer 2022; ours vols 50,119). Δ=0 needed for 480. It has been *measured* but never used to *prune*: forbid any partial whose Δ already exceeds the target during construction.

## 4. Staged shaped scoring that never breaks earlier stages

Lague scores cross > F2L-corner > F2L-edge > OLL > PLL, deliberately so a later subgoal can't sacrifice an earlier one; he adds explicit *penalties* for the "right place, wrong orientation" trap.

**E2 analog:** concentric/scaffold builds (border → frame → bands) with the discipline that inner-region reward < outer-region reward, plus explicit penalties for known traps (consensus-trap pieces, [[palimpsest-historical-consensus]]). Anjou's scaffold work (G1-G6) plateaued at 462 partly from *un*-shaped reconciliation; the Lague lesson is the scoring discipline.

## 5. Multi-path phase-1 (don't greedily reach the intermediate goal)

Lague enumerates *many* phase-1 (domino) solutions because a shorter phase-1 can force a worse phase-2. **E2 analog:** enumerate many borders/frames and pick by downstream interior quality, not border score — validates [[inv3-border-dp-seed]] (A1) and B3.

## Synthesis with PARQUET (vol-203) findings

PARQUET showed the per-edge LP is near-tight on small geometric obstructions but =480 on canonical (perfect color balance saturates it), and 2×2 patch cuts barely tighten the fractional LP. **Conclusion: the LP-bound direction is capped; the leverage is constructive search, not bounds.** Lague's techniques are exactly the constructive-search upgrades E2 has never tried: invariant-preserving move restriction + admissible pattern-DB pruning + conservation-law pruning.

## Next invention (vol-204 candidate): KEYSTONE

A from-scratch constructive solver that (1) builds region-by-region, (2) maintains a forbidden-patch-free invariant on the placed region, (3) restricts extensions to invariant-preservers (domino-style), (4) prunes with an admissible remaining-mismatch pattern-DB (forbidden-patch + Δ-invariant), (5) IDA*-deepens. The hypothesis: invariant-preserving construction reaches high-score basins that destructive local search is σ-locked out of.

## Linked

- [[forbidden-patch-theorem-2026-05-19]]
- [[ns1-deficit]]
- [[sigma-cycle-universal-indecomposable]] (why constructive > destructive here)
- [[intaglio-attack-lex]] (forbidden-patch as objective — predecessor)
- [[inv3-border-dp-seed]] (multi-path phase-1)
- [[reference_anjou_experiments_2026_06_09]] (memory; Anjou scaffold law)
