---
name: lattice-forced-chains
description: LATTICE (vol-205) — tested whether color/scarcity uniqueness forces UNCONDITIONAL piece placements for any 480 solution. Result — ZERO unconditional forced adjacencies (single colors appear 20-49× each), all 196 interior pieces orbit-4, all 4 corners fit all 4 corners. E2 has no exploitable deterministic structure beyond piece-class. Mechanistic root of 15-year unsolvability.
status: refuted
metadata:
  type: concept
---

# LATTICE — forced-chain closure from scarcity (vol-205)

**Status**: `refuted` (2026-06-09). E2 has essentially ZERO unconditional forced
placements; constraint-propagation closure pins nothing beyond piece-class.

**Origin**: vol-205, chosen from the vol-204 scarcity finding (the (N,W)-pair
scarcity: 33% of pairs have a unique server → piece-theft). Hypothesis: the
scarcity graph forces a large deterministic sub-structure of any 480 solution.

**Files**: `scripts/v205_forge/lattice/forced_adjacency.py`, `pair_forcing.py`.

## What we tested
Whether, FOR ANY 480 SOLUTION (where every interior edge matches), color/pair
uniqueness forces specific adjacencies or placements — an unconditional
search-space reduction (the strongest kind: removes possibilities, not just
guides search). Per user directive (search-space reduction > speed).

## Result — no unconditional forcing exists

1. **Single-color partner counts are large** (`forced_adjacency.py`): each of the
   22 interior colors is presentable by **20-49 distinct pieces** on each side.
   ⇒ **0 forced horizontal and 0 forced vertical adjacencies**. No piece-side has
   a unique matched partner.
2. **All 196 interior pieces have rotation-orbit size 4** (`pair_forcing.py`) —
   maximal placement flexibility, zero rotational symmetry to exploit.
3. **All 4 corner pieces fit all 4 corners** — none is pinned to a specific
   corner unconditionally (each rotates to present its 2 border sides at any
   corner).
4. The (N,W)-pair scarcity (vol-204) is real but only **conditionally** binding
   (a cell demands a specific pair only once its neighbors are placed) — it does
   not yield unconditional pins.

## Why this matters — the mechanistic root of unsolvability

This is the deductive complement to the vault's empirical "no universal
piece-position backbone" (0 cells with 5/5 agreement across high boards). E2 is
**constructed** (Selby-Riordan) to have **no exploitable deterministic structure
at any local scale**:
- no forced single-color adjacency,
- no forced corner/piece placement,
- no sub-480 LP/MIP bound at 2×2 scale ([[parquet-overlapping-patch]]),
- no global supply violation detectable early ([[watershed-frontier-flow]]),
- only a *conditional* (N,W)-pair scarcity that manifests as piece-theft.

Constraint propagation (AC-3, gacolor, island — all in the engine) therefore
pins ~nothing; the search cannot be deterministically shrunk. **This is why every
local/exact method plateaus and why 15 years of solvers haven't cracked it on a
single machine.**

## Implication — where solving power must come from
Since E2 has no local deterministic structure, no reachable sub-480 bound, and
local search is σ-locked, the realistic routes to a SOLUTION are:
1. Massive distributed exact search (community 200-core × 30-day regime) — the
   only demonstrated route to 469; not single-machine.
2. A fundamentally new GLOBAL formulation capturing the STATISTICAL structure
   (the "transformed domain has statistically exploitable features" hint), e.g.
   the constructive Lagrangian (N1) or window-MaxSAT-with-reservation (N2)
   backlog items — these don't need deterministic forcing.

## Linked
- [[watershed-frontier-flow]] — the scarcity finding that motivated this
- [[parquet-overlapping-patch]] — bound side (also capped)
- [[streamlining-for-e2]] — conjectural (non-deterministic) streamliners remain open
- [[three-basin-iso-plateau]] — empirical "no backbone" counterpart
- memory: `project_e2_v204_death_mechanism_2026_06_09`
