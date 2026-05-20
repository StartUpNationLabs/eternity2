---
name: three-basin-iso-plateau
description: The iso-plateau is the empirical fact that the strongest local-search
status: built
metadata:
  type: concept
---
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

## 1h budget confirms basin lock (vol-187 close)

Extended V181 460 KEYRING ALNS from 30min → 1h: 2400 iterations all
accepted at SA t=1, score history still 1 entry (iter=0, score=460).

The iso-plateau is **NOT budget-dependent**. Doubling wall-clock time
produces zero lift. This rules out "the basin is reachable but we
ran out of time" as an interpretation — the manifold of accepted-equal
boards has measure zero in any lift direction under our operators.

## V187 row-band MIP rigidity proof (vol-187)

LP relaxation + MIP on V181 460 mismatch band:

| Band | Original | LP-UB | MIP-optimal | Status |
|---|---|---|---|---|
| (11, 12) | 72 | 72.00 | (LP-proven) | **MIP-rigid by LP** |
| (12, 13) | 63 | 65.24 | **63** | MIP-rigid (gap closes) |
| (13, 14) | 62 | 63.81 | **62** | MIP-rigid (gap closes) |
| (11, 12, 13) | 94 | 100.86 | ≥92 at 20min | LP gap 6; MIP-search hard |
| (11..14) | 120 | 135.09 | (in progress) | LP gap 15; running |

**All three 2-row bands MIP-proven rigid**: the integrality gap closes
the LP slack to exactly zero. No higher-scoring integer solution exists
on any 2-row swap.

## Linked

### Algorithms & operators
- [[prior-guided-alns]] — V169 OPHIDIA prior-destroy used in tests
- [[intaglio-attack-lex]] — V180 lex-intaglio acceptance used in tests
- [[v179-large-k-destroy]] — V179 LARGE-K destroy variants
- [[keyring-patch-prior]] — V181 KEYRING builder
- [[prior-data-augmented-beam]] — V155 PRIOR builder

### Findings extending or extended by
- [[sigma-cycle-universal-indecomposable]] — the cross-basin obstruction this generalizes
- [[row-level-rigidity]] — vol-186 row-swap rigidity on V181 460
- [[v187-intaglio-mip]] — MIP-proven region rigidity on V181 460
- [[v188-translation-sigma-indecomposability]] — vol-188 σ-transport refutation, V181↔McGavin
- [[mip-local-optimality-459]] — earlier MIP-rigidity finding
- [[corner-permutation-study]] — 18-cp basin taxonomy

### Basins
- [[basin-458-cp3012-v175]] — V175 458 basin
- [[basin-460-cp0312-v181]] — V181 460 basin
- [[basin-459-p06]] — vol-60 459 basin (Cluster A)
- [[basin-461-cp1203-v125]] — V125 461 basin (sibling era)
- [[basin-463-cp2301-v129]] — V129 463 basin (current matched record)
- [[basin-mcgavin-469]] — community ceiling

### Papers
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]]
- [[SYNTHESIS_VOL_188]]

## Linked memory

- `project_e2_three_basin_iso_plateau_2026_05_20`
- `project_e2_v181_460_new_basin_2026_05_20`
- `project_e2_v175_458_new_basin_2026_05_20`
- `project_e2_vol65_oracle_sigma_indecomposable`
