# Current Volume — Vol-189 — CORTEZ: Corner-Perm-Targeted Search

**Theme**: directly target corner-perm signatures that have ≥458 in DB but NO ≥460. There are 15 such cps; finding even ONE ≥460 in a new cp validates that the algorithm pipeline reaches new basins given the right cp target.

## Naming

**CORTEZ** — for the "explorer searching unknown shores" metaphor: each unexplored corner-perm is a basin not yet visited at ≥460 quality.

## Why this angle

Per vol-129 PALIMPSEST: 18 corner-perms carry ≥458 boards. Of these, only 3 have ≥460 in the DB:
- cp=(3,2,0,1) — McGavin 469
- cp=(1,2,0,3) — V125 461
- cp=(0,3,1,2) — V181 460

**15 corner-perms have ≥458 but no ≥460**. These are unexplored basin families. The V181 KEYRING pipeline successfully reaches NEW ≥460 basins — V181's 460 was the first ever in its cp. There's no a-priori reason it can't do the same in the 15 other cps.

But V155/V175/V181 builders DON'T select for cp — they go where the corpus prior + scan order leads. To force exploration of a target cp, we need:

1. **Corner-perm-fixed beam search**: place corners FIRST (at positions 0, 15, 240, 255) before any interior placement, and pin them to the target cp.
2. **Continue with V181 KEYRING** ranker: patch + pheromone + position prior.
3. **Sweep**: target each of the 15 cps × 3-4 seeds.

## Math (KEYRING-FRESH builder)

Standard V155 beam visits positions in scan order. We modify:

1. First placement decisions: corners 0, 15, 240, 255. Beam state = (4 chosen corner pieces in target cp, rotations).
2. Subsequent placements: same as V181 KEYRING with the corner-constrained edge propagation.

For each target cp = (p_NW, p_NE, p_SW, p_SE):
- Force piece p_NW at position 0 with valid rotation (W=BORDER, N=BORDER).
- Same for p_NE at 15 (E=BORDER, N=BORDER), p_SW at 240 (S=BORDER, W=BORDER), p_SE at 255 (S=BORDER, E=BORDER).
- These are exactly the 4 corner pieces; each has a unique rotation that places the borders correctly.

Then beam search continues over remaining 252 positions.

## Binding items (3 max)

1. Build V189 CORTEZ builder = V181 KEYRING + corner-perm pinning.
2. Sweep 15 unexplored cps × 4 seeds × 30min ALNS = 60 jobs (parallel 8 at a time).
3. Any ≥460 in new cp → record. Any ≥461 → BREAKTHROUGH.

## Compute estimate

60 builds × ~5 min each + 60 ALNS × 30 min = 5 hours × 8 cores = ~40 wall-clock minutes if all parallel. Realistic: 1-2h.

## Days budget

1 day.

## Linked

- [[cortez-corner-perm-targeted]] (TBD)
- [[vol-188]]
- [[vol-181]] (V181 KEYRING)
- [[basin-460-cp0312-v181]]
