---
tags: [concept, metaheuristic]
status: built-light
origin-vol: 5
---

# Genetic algorithm (4×4 / 6×6 region crossover)

**Status**: `built` (vol-5); not extended past vol-5
**Origin**: vol-5
**Files**: `crates/ga/`

## Definition

- **Population**: ~50 plateau boards (score ≥ 440).
- **Crossover**: pick a K×K region. Replace child's region with parent 2's same region; reconcile piece duplications by random reassignment.
- **Mutation**: PT polish on the offspring (small SA budget).
- **Selection**: tournament on score.

## Variants

- **GA-light**: 4×4 region crossover, ~10-iter cascades. Reaches 452/480 within a basin family.
- **GA-LARGE**: 6×6 region crossover, 3-hour cascade with PT mutation. Vol-5 best: **453/480** (10 published distinct boards on 2-3 basin families).

## What got measured

- **Within-family** (similar borders): reaches 452-453. Some replicas momentarily touch 454, fall back.
- **Between-family** (different borders): noise. Crossover fails because piece-reconciliation destroys structure.

## Why it stalled at 453

Vol-5 + vol-6 finding: the "30-mismatch budget" stays approximately conserved across local moves (NE1/NE2 soft penalties redistribute but don't reduce). GA crossover at 4×4-6×6 size hits the same Hamming-moat depth ≥ 5 that defeats ALNS at that K.

Larger crossover (8×8+) would be needed to traverse the moat, but cost-per-iteration explodes. Not explored.

## Status post-vol-6

Superseded by vol-6's `pt_e2 --pin-perimeter` which reached **454/480** with a different mechanism (border-diversity sampling + PT).

Could still be useful for **inter-family** transfer if combined with `--start-from` warm starts from each family. Unbuilt.

## Linked concepts

- [[parallel-tempering]] — the post-vol-6 successor
- [[basin-454-vol6]] — the basin GA stalled just below
- [[alns]] — the K-bound moat

## Linked memory

- `project_e2_state` (vol-5 row, vol-6 row)
