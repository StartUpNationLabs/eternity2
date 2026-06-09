---
name: parquet-overlapping-patch
description: PARQUET (vol-203) — 2×2 feasible-patch LP relaxation for an unconditional sub-480 bound. Result — sound but capped at 480 on canonical; the per-edge color-mass LP is already near-tight on geometric obstructions; 2×2 cuts barely move the fractional LP. Negative bound result; repositions leverage to constructive search.
status: refuted-as-bound
metadata:
  type: concept
---

# PARQUET — overlapping-patch relaxation

**Status**: `refuted-as-bound` (vol-203, 2026-06-09). The 2×2-patch LP does
NOT crack 480 on canonical. Sound and correct; just not tight enough at the
2×2 scale. The base per-edge LP it builds on is a useful by-product (a strong
cheap UB oracle).

**Origin**: vol-203. Motivated by [[forbidden-patch-theorem-2026-05-19]]
(99.88% of random distinct 2×2 piece-tuples are infeasible; a 480 board has 0
forbidden patches) — the smallest object encoding piece-atomicity + local
edge-coupling that every prior LP/MIP relaxation relaxes away.

**Files**: `scripts/v203_patch_lp/` — `e2lib.py` (independent loader/scorer,
verified McGavin 469/480), `f0_blocks.py` (aligned-block enum), `f2_patch_lp.py`
(base per-edge LP), `f4_patch_sound.py` (sound 2×2 patch tightening),
`brute_small.py` (B&B exact small solver), `make_hard_balanced.py`. Math:
[[MATH_NOTES_2026-06-09_PARQUET]].

## Definition

Three formulations, loosest→tightest:
- **F0** aligned-block max-K packing (counting). Vacuous: alphabet supply
  ample, per-color budget = 480 with zero slack, all colors even.
- **base per-edge LP**: assignment polytope `z[c,(p,r)]` (1/cell, 1/piece,
  border baked in) + edge match `m[e]` with color-mass linking
  `t[e,k] ≤ min(Σ_{A shows k} z, Σ_{B shows k} z)`, `m[e] ≤ Σ_k t[e,k]`.
  Objective `max Σ m[e]`.
- **PARQUET cut** (sound): per 2×2 window q, `Σ_{e∈q} m[e] ≤ 3 + Σ_a w[q,a]`
  with `w[q,a] ≤ z[cell,(p,r)]` for each of feasible patch a's 4 cells,
  `Σ_a w ≤ 1`. Says: all 4 internal edges matched ⟹ a feasible patch active.

## What we measured (vol-203)

Soundness gate passed: known solutions score perfect (24/40/60/112);
integer model = exact true max (40,38,37,37,58); LP-UB ≥ true max always.

On **color-balanced** unsat-perfect instances (the canonical regime):

| instance | #edges | true max | base LP | PARQUET |
|---|---:|---:|---:|---:|
| g5_bal_k1 | 40 | 38 | 38.41 | 38.34 |
| g5_bal_k2 | 40 | 37 | 38.32 | 38.11 |
| g6_bal_k1 | 60 | 58 | 58.00 | 58.00 |

- The **base per-edge LP is already within ~1** of true max on geometric
  obstructions — far stronger than the vault's "per-color = 478/480", because
  it couples color availability to the actual assignment at both endpoints.
- 2×2 patch cuts tighten only by ≤ 0.2 (fractional LP relaxes around them).
- **Canonical 16×16 base LP = 480.000** — perfect color balance + rotation
  freedom saturate every edge fractionally; no 2×2 cover cut removes that
  fractional 480 point.

## What was refuted

**2×2-patch LP relaxation cannot bound canonical E2 below 480.** The 2×2
scale is too local; the balanced fractional 480 point survives all 2×2 cuts.
(NOT a refutation of the patch *idea* generally — 2×3/3×3 cuts or the integer
solve or SDP level-2 remain open; see math note.)

## Why it matters anyway

1. Confirms (independently of Anjou's seqAMO work) that the *bound* direction
   is hard: aggregate/local relaxations all give 480.
2. The base per-edge LP is a **strong cheap UB oracle for sub-boards/windows**
   — directly reusable as an admissible bound in an IDA* constructive search.
3. Repositions the research: leverage is constructive search with
   invariant-preserving move restriction + admissible pattern-DB pruning
   ([[lague-rubik-transfer-ideas]]), not LP bounds. → vol-204 KEYSTONE.

## What's still open (bound side)

- Lasserre/SOS level-2 on 2×2-patch monomials.
- 2×3 patch cuts via column generation.
- Per-window integer subproblem → board cutting plane (Anjou seqAMO-as-cut).

## Linked

- [[forbidden-patch-theorem-2026-05-19]] — the motivating theorem
- [[lague-rubik-transfer-ideas]] — where the leverage moved
- [[super-block-bbb]] — aligned-block predecessor (PARQUET added overlap + soundness)
- [[intaglio-attack-lex]] — forbidden-patch as ALNS tiebreaker (predecessor use)
- [[MATH_NOTES_2026-06-09_PARQUET]] — full derivation + results
- memory: `project_e2_corrected_state_2026_06_09`, `reference_anjou_experiments_2026_06_09`, `project_e2_small_puzzle_pieceid_trap`
