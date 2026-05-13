---
tags: [basin, community, reference]
status: external-reference
score: 470
variant: 1-clue
---

# Basin Blackwood-470 (1-clue community record)

**Score**: 470/480
**Variant**: **NOT canonical 5-clue Eternity II.** 1-clue / unframed E2 variant (Blackwood's `E2ncud`).

## Discovery

Joshua Blackwood, 2020-11 (via libblackwood scenarios `jb466.py` … `jb471.py`). Confirmed via inspection of `data/tomy_EternityII.py` in libblackwood: the `E2ncud` puzzle pins ONLY the central piece — not the 5 canonical hints.

## How the 470 was decoded

Vol-2 inspected Blackwood's Bucas URL. At the 4 corner-hint cells he places pieces 147, 108, 186, 249 (rotations 0/0/0/1), whereas canonical 5-clue mandates pieces 207, 180, 254, 248 (rotations 1/1/1/2). Confirms NOT canonical.

σ-bijection from `pt_color → joshua_color` is uniquely determined and is its own involution on {0, 21, 22}, a 5-cycle on each of three other 5-element sets. See [[reference-blackwood-decoded]].

## Files

- `v2/output/joshua_blackwood_url.txt` — Blackwood's 470 Bucas URL.
- `v2/output/blackwood_decoded.json` — same board re-encoded in our pieces.txt color labelling.
- `v2/crates/benchmark/src/bin/prefix_compare.rs` — diff against any harvested plateau.

## libblackwood three pruners

1. **Edge-pair lookup table** per cell: `(left_color, up_color) → sorted piece list` with conflict-free first.
2. **Monotone color-count curve**: 3 specific colors (in Joshua's labelling: 9, 12, 15) must keep cumulative count above a piecewise-linear curve over depth.
3. **Scheduled relaxations**: 10 specific late depths (197, 203, 210, 216, 221, 225, 229, 233, 236, 238) where one edge mismatch is allowed.

This is the [[blackwood-algorithm|Blackwood algorithm]]. The 10 missing edges in 470/480 ARE these scheduled break points — deliberately planned, not residual error.

## Scenarios jb466 … jb471

Each differs only in **relaxation count**. `jb471.py` exists (9 relaxations) but **no successful run is logged in the public repo**. → Community ceiling for the 1-clue variant is somewhere in [470, 471).

## Why 470 is NOT our target

- We work on canonical 5-clue. The 470 board has wrong corner hints.
- 5-clue ceiling is 469 (McGavin 2020) — see [[community-corpus]].
- Blackwood's solver applied to canonical 5-clue reached 469 via McGavin (different parameter set).

## Linked concepts

- [[blackwood-algorithm]] — the algorithm decoded from this board
- [[community-corpus]] — corpus mining that contextualized this

## Linked memory

- `reference_blackwood_decoded`
- `reference_community_e2_ceiling`
