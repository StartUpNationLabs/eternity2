# ICEBERG — Forbidden-Minimizing Constructive Heuristic

**Status**: `refuted` (Vol-145, 2026-05-19)

## Idea

Like GRAIN but greedy-attach to MINIMIZE forbidden 2×3 patches rather
than MAXIMIZE matched edges.

## Result

3 seeds on canonical, ICEBERG vs GRAIN:

| seed | ICEBERG matched | ICEBERG forbidden | GRAIN matched | GRAIN forbidden |
|------|-----------------|-------------------|---------------|-----------------|
| 42 | 371 | 156 | 360 | 176 |
| 1 | 355 | 174 | 357 | 172 |
| 7 | 354 | 172 | 337 | 190 |

Marginal differences. Not consistently better across seeds.

## Why

At 75% matched, 170+/210 2×3 patches are forbidden — the
discriminatory power of forbidden-count is low. Matched-count remains
dominant. Forbidden-count theorem holds at HIGH-score regimes (461→36,
469→26) but doesn't help constructive heuristics in LOW-score territory.

## Refuted

ICEBERG is GRAIN with marginal tiebreaks. Not a distinct invention.

## Linked

- [[grain-polycrystalline]]
- [[forbidden-patch-theorem-2026-05-19]]
