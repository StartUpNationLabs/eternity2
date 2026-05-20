# Three-Basin Iso-Plateau — Universal Local Rigidity at 458–460

Status: `built` (empirically validated across 3 distinct basin families, 2026-05-20)
Origin: vol-179/180/181 cross-validation; finding crystallised vol-181 close.
Files: rationale documented at vault/sessions/vol-181.md, evidence in `output/vol-{169,175,181}/`.

## Definition

The **iso-plateau** is the empirical fact that the strongest local-search
pipeline we have — `alns_only --ops basic_lkh --prior-destroy <prior.json>
--lex-intaglio --repair-kind sa --t 1.0` running 30 minutes with V179 LARGE-K
variants (k ∈ {16, 32, 48}) — **cannot lift any of three distinct ≥458 basins**.

A "basin" here is identified by corner-permutation signature
$\text{cp} = (\text{piece}(0), \text{piece}(15), \text{piece}(240), \text{piece}(255))$ —
the 4 corner pieces in canonical order.

## Tested basins

| Basin | Origin | Corner perm | Initial score | 30min ALNS lift |
|---|---|---|---|---|
| V155→ALNS seed1 | vol-156 / vol-169 | (1,0,3,2) | 460 | **460** |
| V175-LONG-LIFT zigzag_s99 | vol-175 | (3,0,1,2) | 458 | **458** |
| V181 KEYRING row_s42 | vol-181 | (0,3,1,2) | 460 | **460** |

All three runs show the same pattern:

- `best_score_history` has 1 entry (iter=0 only).
- 1100–1300 destroy+repair invocations executed.
- All accepted under SA t=1.0 (the manifold of equal-score boards is large).
- Final board = base board (**0 cell diff** after 30min).
- All ops fired heavily, including LARGE-K k=48 and lex-intaglio.

## Why this matters

Three independent basin families — discovered through different mechanisms (V155
prior beam, V175 multi-scan, V181 keyring) — exhibit the **same locked
rigidity** under canonical hints + local ALNS.

This generalises and operationalises the vol-65/vol-99 σ-cycle indecomposability
finding: not only are the σ-cycles between basins indecomposable into smaller
moves, but every basin we can reach in the 458–460 range is **iso-score-closed**
under our current operator portfolio.

## What we measured precisely

For each basin, post-run analysis showed:

- ALNS oscillates on a manifold of equal-score boards: cells get destroyed and
  repaired to alternative pieces of the same score-contribution, then often
  reverted on the next destroy.
- Lex-intaglio (vol-180) does not break the oscillation: equal-score destroys
  rarely change the forbidden-2x2 count either.
- Prior-escape (β > 0, V169 OPHIDIA) gives nominally targeted destroys but
  same outcome: lands back at score $s$.

## Why local ALNS cannot escape

A successful escape from a 458–460 basin requires a coherent multi-cell move
that *both* breaks the existing equal-score equilibrium *and* lands on a
higher-scoring basin. The σ-cycle data (vol-65) shows the minimum coherent move
is hundreds of cells long. Local ALNS destroys 4–48 cells and repairs them via
matching/lkh-chain, which has no mechanism to coordinate hundreds of placements.

## Implications for the search strategy

**Path to 461+ is not local ALNS on any 458–460 base.** Concrete next angles:

1. **Cross-basin operators**: σ-permutations, full row-band swaps, multi-region
   destroy ≥ 200 cells. Computationally expensive; likely needs warm-start from
   structural insight, not random sampling.
2. **Direct construction targeting fresh cp**: we have covered 3 cp signatures
   with ≥458; there are 24 possible cps. V175 GAUNTLET scan-order proved cp
   diversity is achievable.
3. **Exact methods with anytime budget**: SAT/MIP with long time budget on
   relaxed sub-problems (border-MIP, row-band CSP-fill).
4. **V184 LIGHTHOUSE-soft**: relaxed interface (allow ≤4 mismatches at the
   meeting row, then ALNS-repair) — not yet tried.

## What this is NOT

- NOT a proof that the basins are local optima in any rigorous sense.
- NOT a statement about non-canonical-hint variants of the puzzle.
- NOT a claim that 30min × N seeds is computationally exhaustive — longer
  budgets, larger op portfolios, or warm-start from outside-the-basin
  trajectories are not ruled out. (See CLAUDE.md §10.)

## Linked

- [[prior-guided-alns]]
- [[intaglio-attack-lex]]
- [[sigma-cycle-indecomposability]]
- [[basin-458-cp3012-v175]]
- [[basin-460-cp0312-v181]]

## Linked memory

- `project_e2_three_basin_iso_plateau_2026_05_20`
- `project_e2_v181_460_new_basin_2026_05_20`
- `project_e2_v175_458_new_basin_2026_05_20`
- `project_e2_vol65_oracle_sigma_indecomposable`
