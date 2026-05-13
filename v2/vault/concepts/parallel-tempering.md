---
tags: [concept, local-search, metaheuristic]
status: built-extended
origin-vol: 2
---

# Parallel Tempering (PT)

**Status**: `built` (vol-2), warm-start record vol-6
**Origin**: vol-2 (canonical impl), vol-18 (hot-PT T=30 variant)
**Files**: `crates/localsearch/src/pt.rs`, `crates/bench-audit/src/bin/pt_e2.rs`, `crates/bench-audit/src/bin/run_alns_pt`

## Definition

Multiple replica chains running SA at different temperatures `T_1 < T_2 < … < T_K`. Periodically attempt swaps between adjacent-T chains with Metropolis acceptance:

`P(swap i,j) = min(1, exp((β_i − β_j)(E_j − E_i)))`

Higher chains explore broadly, lower chains exploit; swaps shuttle promising states down to the cold chain.

## Headline results

- **Vol-6**: warm-PT with `--pin-perimeter` from a 453 seed → **454/480** (historic cold-then-warm record). Byte-identical across 4 seeds (deterministic ceiling).
- **Vol-18**: hot-PT at T_max=30 from a 456 oracle → **457/480** (current cold-start record).

## Tabu absence (vol-14 finding)

`pt_e2` has **no explicit tabu list**. It relies on 4 implicit anti-cycle mechanisms:
1. Chain swaps (replica exchange perturbs state).
2. Kick moves (occasional large-perturb).
3. Repair-based acceptance.
4. Houdayer strict-improvement filter.

In iso-score plateaus, cold chains drift through revisited states. → `pt-tabu` (Zobrist hash-cons LRU) is the unbuilt fix; see [[pt-tabu]].

## Hot-PT (vol-18)

T_max=30 was needed for the 447→456 transition: the cooperativity gap Δ=-21 means standard PT at T=1 has acceptance p≈10⁻¹⁵. See [[r5f-cooperativity]].

## Iso-score acceptance on plateau

100% acceptance regardless of T on E2 score plateaus (vol-17). Temperature does not order plateau moves; energy ties are not broken. → `lex_break_isoscore` tiebreak shipped in vol-17.

## --pin-perimeter and --pin-cells flags

vol-6 shipped these on `pt_e2`. Pin cells stay fixed throughout the run, the interior is the search space. The 454 record required `--pin-perimeter` from the corpus-derived border + `--start-from` a 453 seed.

## Saturation in fresh basins

`hot_pt` at T=50, 16 chains, on the 440/469 basin (vol-22, PID 66809): 47 min plateaued at 442. Overnight 8h run scheduled vol-23. Per [[basin-escape-recipe]] table.

## Linked concepts

- [[alns]] — outer loop composes with PT
- [[pt-tabu]] — the unbuilt anti-cycle fix
- [[r5f-cooperativity]] — why T must be ≥30 at the 447→456 step
- [[basin-457-pt]] — the basin PT discovered
- [[basin-440-469]] — the basin PT cannot saturate

## Linked memory

- `project_e2_vol14_pt_no_tabu`
- `project_e2_vol18_r5f_cooperativity`
