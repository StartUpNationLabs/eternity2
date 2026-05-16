---
name: bf-candidate-bucket-bug
description: "Vol-118 CRITICAL bug found by user 2026-05-16. The blackwood-fast candidate-bucket index incorrectly pushed every (piece, rotation) into tbl=0 (interior fit), allowing edge pieces to be placed at interior positions with BORDER edges facing inward. Bug found by visual inspection of 232-cell partial bucas render. Fixed by routing each piece-rotation to EXACTLY ONE bucket based on its (right_is_border, bottom_is_border) pair. Existing complete-board records (459, 469) immune; bf PARTIAL outputs before ALNS were affected."
metadata:
  type: project
---

# bf candidate-bucket bug (vol-118 CRITICAL)

**Status**: `refuted` (the bug existed since vol-15 build; fixed
in commit 4cfbcda 2026-05-16).

## What the bug was

`crates/blackwood-fast/src/lib.rs::RowMajorIndex::build` populates a
`buckets[4 × 65536]` array. Indexed by `(tbl, ref_key(top, left))`:

- tbl=0: candidates for "interior fit" (no right/bottom border)
- tbl=1: candidates for "bottom-row fit"
- tbl=2: candidates for "right-col fit"
- tbl=3: candidates for "bottom-right corner fit"

**The bug**: for every (piece, rotation), the build pushed it
INTO tbl=0 unconditionally:

```rust
buckets[flat_key(0, key)].push(pr);                     // always
if bottom_is_border { buckets[flat_key(1, key)].push(pr); }
if right_is_border  { buckets[flat_key(2, key)].push(pr); }
if right_is_border && bottom_is_border { buckets[flat_key(3, key)].push(pr); }
```

So an edge piece (1 BORDER edge) with `bottom_is_border=true` ended
up in BOTH tbl=0 AND tbl=1. When the DFS is at an interior cell
(tbl=0) and the (top, left) colors happen to match the edge piece,
it gets selected and placed with its BORDER edge facing inward.

The same bug existed in `build_relaxed_index()`.

## How it was discovered

User visually inspected the 232-cell par-bf partial bucas render
and noticed many obviously broken edges. Investigation found 8
border violations at positions 208, 209, 211, 212, 224, 225, 227, 228
(all interior, rows 13-14).

These were edge pieces (1 BORDER edge) placed at interior cells with
the BORDER edge facing INWARD:

| pos | piece | base edges | rot | rotated | class |
|----:|------:|-----------:|----:|--------:|------:|
| 209 |    26 |  (0,1,2,1) |   2 | (2,1,0,1) |  edge |
| 211 |    51 |  (0,1,1,1) |   1 | (1,0,1,1) |  edge |
| 212 |    42 |  (0,3,1,2) |   3 | (3,1,2,0) |  edge |
| 225 |    18 |  (0,2,2,2) |   0 | (0,2,2,2) |  edge |
| 227 |    29 |  (0,1,2,1) |   1 | (1,0,1,2) |  edge |
| 228 |    15 |  (0,2,4,1) |   3 | (2,4,1,0) |  edge |

## Fix

A piece-rotation now goes into EXACTLY ONE bucket per
(right_is_border, bottom_is_border) pair:

```rust
match (right_is_border, bottom_is_border) {
    (false, false) => buckets[flat_key(0, key)].push(pr),  // interior
    (false, true)  => buckets[flat_key(1, key)].push(pr),  // bottom-row
    (true,  false) => buckets[flat_key(2, key)].push(pr),  // right-col
    (true,  true)  => buckets[flat_key(3, key)].push(pr),  // bot-right corner
}
```

## Verification

After fix:

| board                          | placed | matched | border violations |
|--------------------------------|-------:|--------:|------------------:|
| 232-cell BEFORE fix            |    232 |  418/433 | **8**            |
| 231-cell AFTER fix             |    231 |  414/431 | 0                |
| 459 record (vol-110 bseed1)    |    256 |  459/480 | 0                |
| 469 McGavin                    |    256 |  469/480 | 0                |

**Existing complete-board records were immune** — complete-board
ALNS/Hungarian repair always removes illegal placements during
score-maximization. Only PARTIAL bf outputs before ALNS were
contaminated.

## Impact assessment

Affected outputs (potentially):
- All `bf_bw*` partial dumps since vol-15 (raw, schedule, hinted variants).
- Vol-116, vol-118 T5/T5b strict-canonical pipeline scores (449/450/452)
  — partially built on contaminated partials. Final scores need
  re-verification with the fix in place.

NOT affected:
- Existing 459 records (vol-110 basins, vol-60 RECORD_TIE, etc.).
- McGavin 469.
- vol-32 458 cold-start.
- Any complete-board final scores from `solve_blackwood` / `alns_only`.

## Lesson

A subtle bucket-fan-out bug can hide for many volumes because:
1. Complete-board scoring catches the illegal placements (they
   cost score, so optimization removes them).
2. Verify scripts didn't check the "no BORDER edge facing
   interior neighbor" constraint.
3. Visual inspection (bucas render) was the only way to catch this.

Per CLAUDE.md "diff first" rule: should have visualized partials
before reasoning about them.

Future safeguards:
1. Add a `verify_record.sh` check for border-consistency violations
   in PARTIAL boards.
2. The bf engine should also assert at debug-build time that no
   illegal placement is made.

## Linked

- [[blackwood-fast]] — affected crate.
- [[hint-pin-conflict-propagation-fix]] — another vol-117/118 bf bug.
- [[../sessions/vol-118]].
