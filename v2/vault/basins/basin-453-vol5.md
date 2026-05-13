---
tags: [basin, vol-5, ga-cascade]
status: historic
score: 453
---

# Basin 453-vol5 (GA-LARGE 3-hour cascade)

**Score**: 453/480 — vol-5 GA-LARGE record
**Discovery**: Vol-5 GA-LARGE 6×6 region crossover + PT mutation, 3-hour cascade

## Properties

- 10 published distinct boards on 2-3 basin families.
- 3 of 8 replicas momentarily reach 454; fall back. 454 was achievable but unstable from this approach.
- All 24×5 = 120 rare-color edges matched (100% [[rare-color-rule|invariant]] confirmed).
- All 27 mismatches are abundant-color-only.
- 30-mismatch budget approximately conserved across NE1/NE2 moves.

## What broke past 453

- **Vol-6** pt_e2 --pin-perimeter from a 453-seed + corpus border → 454 ([[basin-454-vol6]]).
- The 453 → 454 jump required: (a) freezing the perimeter (pin-perimeter flag), (b) using a corpus-attested border, not the GA-cascade's border.

## Sister basins

- Multiple 451-452 basins (basin B family) within the vol-5 corpus
- [[basin-454-vol6]] — the +1 successor

## Linked concepts

- [[genetic-algorithm]] — what produced this basin
- [[rare-color-rule]] — the 100% invariant verified here
- [[parallel-tempering]] — what mutation between GA generations used

## Linked memory

- `project_e2_state` (vol-5 row)
