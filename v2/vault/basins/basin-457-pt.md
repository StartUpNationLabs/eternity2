# Basin 457-PT (our locked basin)

**Score**: 457/480 — cold-start record
**Bound**: 461 (gap +4, hard-locked)
**Representative file**: `output/v17_alns_pt/pt_winning5_n4_t1_100_s1_1778663389.json`

## Discovery

Found by hot-PT (vol-18) at T_max=30. All 11 saved PT-457 boards are BYTE-IDENTICAL (one basin found 11 times).

## Properties

- 38 mismatch cells; 23 mismatched edges.
- K=5 operator-locked ([[operator-lock]]).
- 4 duplicate pieces {82, 146, 205, 233} + 4 missing pieces {189, 204, 207, 245} (per [[relaxed-bound]]).
- Min hamming between dup/missing rotations = 2. **Provably hard-locked.**
- ALNS-saturation gap = 4 (the smallest we've seen).

## What can't break it

- All K≤5 local moves (vol-20).
- All bound-ascent + ALNS recovery (vol-21).
- Bound-floor ALNS (vol-22).
- 8-cell, 11-cell exhaustive permutations (vol-21).

## What might break it

- [[prune-restart]] — would close the gap; UNBUILT.
- Another 469-ceiling basin where ALNS-saturation gap closes ([[basin-440-469]] is the candidate).

## Linked concepts

- [[operator-lock]]
- [[relaxed-bound]]
- [[basin-escape-recipe]]
