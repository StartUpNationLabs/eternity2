# Session — vol-02

**Theme**: Prefix-determinism trap. Blackwood-1-clue σ-decoding.
**Raw**: [[archive/raw/RESEARCH_NOTES_2|RESEARCH_NOTES_2.md]]

## What was attempted

- Local-CP region repair on plateau boards.
- Houdayer cluster moves on PT replica pairs.
- Diverse-prefix harvest via shuffled CP.
- σ-bijection decode: map Blackwood's 470 board into our color labelling.

## What was measured / kept

- **[[prefix-determinism]] trap discovered**: the deterministic 449/480 CP prefix is **globally infeasible** to extend past 449. The plateau is **upstream of SA**, not a local-search failure.
- Blackwood's 470 record is on **1-clue variant** (no 5 canonical hints), not canonical Monckton. Decoded via AC-3 σ-bijection in 2 iterations; full mapping in `output/blackwood_decoded.json`. See [[reference-blackwood-decoded]].
- Best constrained 5-clue partial: **450/480** (6/20 samples, pinned harvest from seed `0x171560a05f574f4b`).
- New flags: `pt_e2 --pin-perimeter`, `--pin-cells` (full use vol-6).
- Bucas URL rendering pipeline.

## What was refuted

- **Local CP region repair**: provably infeasible; deterministic border after CP is globally inconsistent with interior completion.
- **Houdayer-offline**: all swaps `joint_delta = 0`; no improving moves on the replicas tested.
- **Diverse-prefix harvest**: random-shuffle CP gives 443-444, lower than deterministic 449. Variance increases, mean drops.
- **Consensus-seeding**: lands back in the 452-basin family. No diversification gained.

## Concepts touched

- [[prefix-determinism]] (introduced)
- [[houdayer-cluster]] (introduced, tested as no-op on these replicas)
- [[parallel-tempering]] (canonical impl + `--pin-perimeter` flag)
- [[community-corpus]] (σ-bijection foundation)

## Open at close

How to break the prefix-determinism trap? Vol-4 will find the answer (frame-first decomposition).

## Linked memory

- `reference_blackwood_decoded`
