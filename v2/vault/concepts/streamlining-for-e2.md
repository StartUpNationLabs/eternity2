---
name: streamlining-for-e2
description: Streamlined Constraint Reasoning (Gomes-Sellmann 2004) applied to E2 — bet on a structural regularity, impose it as a hard constraint to collapse the search space, search the tiny subspace. Never tried on E2. The sound (solution-preserving) version = patch-level consistency propagator (2×3/3×3 arc consistency) from the forbidden-patch theorem.
status: unbuilt
metadata:
  type: concept
---

# Streamlining for Eternity II

**Origin**: vol-203 (2026-06-09), web research per user directive "find ideas we have not explored to build a SOTA algorithm". Source: Gomes & Sellmann, *Streamlined Constraint Reasoning*, CP 2004; 2026 extension arXiv:2605.19895 (CNN-learned streamliners).

## The technique (and why it's the opposite of symmetry-breaking)

A **streamlining constraint** drives search toward a small, *structured* subspace by imposing a conjectured regularity as a HARD constraint. Symmetry-breaking removes *redundant* solutions; streamlining *bets* that some solution has a structural pattern, then collapses the space to only patterned candidates. If the bet holds → massive speedup (Gomes-Sellmann reached spatially-balanced Latin squares N=18 where CP+symmetry-breaking maxed at N=9 — a doubling). If it fails → relax and retry.

**Crucially, E2 has NO symmetries** (binding directive — hints break them), so symmetry-breaking is forbidden. **Streamlining is not** — it's a different mechanism (conjecture structure, not quotient it) and is unexplored here.

## Why the CNN-learned version (arXiv:2605.19895) does NOT directly fit E2

The 2026 CNN pipeline learns streamliners by enumerating ≥500 *solutions* of a training instance, contrastively training a CNN to detect structural patterns, then LLM-synthesizing constraints. **E2 has 0 known perfect solutions** (the whole problem). The paper itself flags: "problems whose solution space is extremely sparse or empty" are unsuitable. So inductive/learned streamlining is out.

## The E2 adaptation: DEDUCTIVE streamlining (novel)

Derive the streamliner from the puzzle's STRUCTURE + our rigidity theorems, not from a solution corpus. Two tiers:

### Tier 1 — SOUND streamliner (solution-preserving, = a theorem, not a bet)
**"Every 2×3 and 3×2 window must be feasible"** (admit some completion with all internal edges matched). A 480 board has all windows feasible ([[forbidden-patch-theorem-2026-05-19]]: 100% of *random* 2×3 tuples forbidden, but a real solution's are all feasible). So this constraint preserves ALL solutions while being enormously restrictive.

The vault's [[intaglio-pruned-dfs]] showed post-placement patch checks are VACUOUS for edge-strict DFS (completed windows match by construction). The power is in the FORWARD direction: a **patch-consistency propagator** that, when placing a cell, filters candidates whose placement leaves a *partial* 2×3 window with no feasible completion. This is strictly stronger than the engine's single-edge AC-3 ([[concepts] solver-engine propagate_ac3], arc = one shared edge). NEVER BUILT — the engine has edge-AC-3 + class/parity/gacolor/island propagators but no patch-level (2-cell-arc) consistency.

### Tier 2 — CONJECTURAL streamliners (bets; relax if UNSAT)
Impose measured regularities of high-score boards as hard constraints, search the collapsed space, relax on UNSAT:
- Selby-Riordan rare-color rule (rare {1-5} never adjacent within a piece) — already a structural fact (`project_e2_rare_opposite_rule`).
- NS-1 Δ-invariant = 0 (necessary for 480; [[ns1-deficit]]) imposed as a hard global constraint.
- Color-clustering / frame-leaning-interior-piece position patterns.

## Connection to "transformed domain has exploitable features"

The 2010-era E2 literature notes: transforming the domain to block-level pieces yields "orders of magnitude smaller search spaces" with "statistically exploitable features" (non-uniform). Combined with streamlining: build the search over **patch-coherent super-tiles** (a domain element = a small patch pre-certified feasible + extensible), so the domain is the streamlined object by construction. This is [[super-block-bbb]] + patch-consistency, the right synthesis.

## Decisive experiment before building (vol-203/204)

Measure at small scale: how much does a 2×3 (and 3×3) forward-check PRUNE vs edge-strict DFS only? If the pruning is large (e.g. ≥10× fewer nodes to optimum on hard balanced instances), build the patch-consistency propagator in Rust and run on canonical. If small, the patch info doesn't propagate usefully and we pivot.

## Linked

- [[forbidden-patch-theorem-2026-05-19]] — supplies the sound streamliner
- [[intaglio-pruned-dfs]] — why it must be FORWARD not post-hoc
- [[super-block-bbb]] — the transformed (block) domain
- [[lague-rubik-transfer-ideas]] — admissible pattern-DB pruning (complementary)
- [[ns1-deficit]] — a conjectural global streamliner
- [[parquet-overlapping-patch]] — the bound side (capped); streamlining is the search side

## RESULT — 2×2 patch-consistency is too weak (vol-203, 2026-06-09)

Measured the SOUND streamliner (2×2-feasibility forward-check) directly:
- **Along McGavin's true near-solution prefix**: edge-strict candidate counts
  are already tiny (1-9 per cell); 2×2 patch FC gives **0%** reduction (every
  edge-strict candidate is 2×2-completable). `scripts/v203_patch_lp/domain_reduction.py`.
- **On 40 greedy-random (wrong) prefixes**: 2×2 patch FC reduces candidate-sum
  by only **6.2%**, and detects an early wipeout (edge-strict>0 but
  patch-consistent=0) only **1 / 454** cells. `domain_reduction2.py`.

This matches vol-124's 2×2 super-block AC-3 ≈ 8% reduction. **The 2×2 scale is
too local to prune E2 search meaningfully** — consistent with PARQUET (2×2 LP
capped at 480) and F0 (counting vacuous). Canonical E2's row-major branching is
ALREADY very low (~2-3 avg survivors/cell) under edge+uniqueness; little is
left for 2×2 patches to remove.

**Implication.** The sound (Tier-1) streamliner must move to 2×3 / 3×3 scale
(100% of random tuples forbidden) where forced-infeasibility might bite — but
the marginal cells (1-3 candidates) leave little room, so expected gain is
uncertain. The higher-EV path is Tier-2 CONJECTURAL streamliners that collapse
the space by orders of magnitude via a strong global structural bet, not local
consistency. See decision note in [[vol-203]].
