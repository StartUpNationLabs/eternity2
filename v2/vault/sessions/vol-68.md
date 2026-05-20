# Vol-68 — Top-row scaling experiment

**Theme**: Test whether top-row choice determines basin attractor.
**Date**: 2026-05-15.
**Standing record at open / close**: 459/480.

## Headline

Sharp N-row pinning threshold at N=14: pinning McGavin's top 14
rows (224 pieces) → ALNS reconstructs 469 in 60s. Pinning top 13
(208 pieces) → ALNS converges to 455 alternate basin.

## What was attempted

1. Strip-count via DFS: how many valid 16-piece top-rows exist?
2. Empirical: how many distinct top-rows do our records use?
3. McGavin top-row pinning + ALNS extension: does it give 469?
4. Top-N rows pinning (N=1, 2, 4, 8, 12, 13, 14, 15) scaling.
5. Cross-ops test (minimal/basic/full/mega_mix at N=1).

## What was measured / kept

| experiment | result |
|---|---|
| Strip count (canonical top-row) | ≥ 5×10⁸ valid configurations |
| Unique top-rows in 363 saved 455+ records | 47 (exact = basin-components) |
| Most-popular top-row | 91 records, max score 458 |
| McGavin's top-row in our 47 set | NO — it's the 48th |
| ALNS from McGavin top-row only (5min winning5) | 400/480 |
| Same with minimal/basic/full/mega_mix (60s each) | 378/378/398/393 |
| N=1 pin | 400 |
| N=2 pin | 382 |
| N=4 pin | 401 |
| N=8 pin | 418 |
| N=12 pin | 450 |
| N=13 pin | 455 |
| **N=14 pin** | **469 ★** (Hamming 0 to McGavin) |
| N=15 pin | 469 |

## What was refuted

- **Strong "top-row determines basin"**: pinning just McGavin's top row
  gives 400 — far below his 469. Top-row alone is insufficient.
- **Cross-ops fix**: changing our ALNS ops (minimal/basic/full/mega_mix)
  doesn't recover; all give 378-398. Our ENTIRE ALNS family is
  incompatible with McGavin's top-row structure.

## What was kept

- **N=14 threshold**: 224 of McGavin's pieces uniquely determine the
  remaining 32. Our ALNS reconstructs.
- **N=13 alternate basin**: with 208 pieces pinned, ALNS finds a
  455-completion swapping pieces within rows 13-15. Multiple
  completions exist; ALNS picks the wrong one.
- **Strip count is astronomical**: ≥ 5×10⁸ valid top-rows. Our
  pipeline samples 47.

## Concepts touched

- [[top-row-determines-basin]] — refuted strong hypothesis
- [[mcgavin-n-row-scaling]] — NEW concept, sharp threshold
- [[basin-component-landscape]] (parent)
- [[e2-maximally-adversarial-thesis]]

## Open at close

- Test N-row scaling on local-459 and vol-32-458: is the N=14
  threshold universal across basins?
- Find minimal pin-set (smarter than top-N rows) that determines
  unique completion. May reveal "skeleton" of structure.
- Blackwood-then-CSP pipeline running for comparison (60s+120s+120s).

## Linked memory

TBD memory entry for vol-68 N-row scaling.
