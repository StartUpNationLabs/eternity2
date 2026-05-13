---
tags: [reference, decoded]
status: documented
---

# Reference — Blackwood 470 decoded

Mirror of memory `reference_blackwood_decoded`. Authoritative content lives in [[basin-blackwood-470]] and [[blackwood-algorithm]].

## Key facts (one-liners)

- Blackwood's **470 record is on the 1-clue variant**, NOT canonical 5-clue.
- Confirmed via `data/tomy_EternityII.py` in libblackwood (`E2ncud` puzzle pins only central piece).
- Blackwood's bucas URL has wrong corner pieces (147/108/186/249 rotations 0/0/0/1) vs canonical (207/180/254/248 rotations 1/1/1/2).
- σ-bijection (pt_color → joshua_color) solved via AC-3 in 2 iterations; involution on {0, 21, 22}, 5-cycle on three 5-element sets.
- libblackwood's three pruners: edge-pair lookup, monotone color-count curve, scheduled relaxations.
- jb466.py … jb471.py exist; jb471 (9 relaxations) has no successful logged run → 1-clue ceiling ∈ [470, 471).

## Files

- `v2/output/joshua_blackwood_url.txt`
- `v2/output/blackwood_decoded.json`
- `v2/crates/benchmark/src/bin/prefix_compare.rs`

## Linked

- [[basin-blackwood-470]] — basin page with full details
- [[blackwood-algorithm]] — the algorithm decoded from this
- [[community-corpus]] — corpus mining that surfaced this
- [[basin-mcgavin-469]] — the CANONICAL 5-clue community ceiling (not this)
