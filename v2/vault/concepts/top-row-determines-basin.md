# Top-row choice determines basin component (vol-68 finding)

**Status**: `built` — vol-68 (2026-05-15).
**Origin**: empirical analysis of 363 saved 455+ records.

## The finding

Across 363 saved records at score ≥ 455:
- **47 unique top-row arrangements** (16 cells in row 0).
- Top-row uniqueness exactly matches basin-component count (47).

Top-row use distribution:
| top-row rank | record count | max score |
|---|---|---|
| 1 | 91 | 458 |
| 2 | 20 | 457 |
| 3 | 18 | 456 |
| 4 | 14 | 457 |
| 5-10 | 10-13 each | 456-458 |

The 10 most-popular top-rows have max scores 456-458.

**McGavin's top row is the 48th — UNREACHABLE by our pipeline.**

## Mechanism

The top row's choice exposes a specific S-color signature (16-tuple
of bottom-side colors). This S-signature determines:
- The space of valid row-1 piece arrangements
- The downstream geometry of the entire interior

Different top-rows lead to different basin attractors. Our 47
basin-components correspond 1-to-1 with our 47 pipeline-reachable
top-rows.

## Why this is significant

1. **The basin landscape is parameterized by top-row choice.** Not
   by corner perm alone (vol-60 found 24 corner perms only). The
   FULL 16-cell top-row arrangement is the relevant control.

2. **Our pipeline samples a tiny fraction of valid top-rows.**
   Vol-68 strip count showed ≥ 10⁷ valid top-rows exist. We only
   reach 47.

3. **McGavin's algorithm finds a different top-row family.**
   His top-row uses pieces like 27, 38, 47, 53 — not in our typical
   set. His algorithm's search heuristic discovers a different
   top-row attractor.

## Implication for new algorithms

**Force-bias the top-row search.** Instead of letting CP/ALNS pick
top-row, EXPLICITLY enumerate diverse top-row candidates and run
the pipeline from each.

Concretely: take McGavin's top row + sample N other top-rows from
the 10⁷-strip space (with diversity bias), and run ALNS from each.
The ALNS-from-McGavin-top experiment is the proof-of-concept.

## Linked

- [[basin-component-landscape]] (parent — 47 components)
- [[basin-permutation-group]]
- [[e2-maximally-adversarial-thesis]] (axis 6 + axis 5)
