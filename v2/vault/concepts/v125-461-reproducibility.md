---
name: v125-461-reproducibility
description: "Vol-125 2026-05-18 12:53: 461/480 achieved by ALL 4 ALNS seeds (1, 7, 99, 142) on the seed=110 bf_bw partial, plus seed=111 with seed=42. The 461 ceiling is HIGHLY reproducible. Two structurally distinct 461 basins identified."
metadata:
  type: project
---

# 461 reproducibility — the basin is robust

## Test: seed110 partial × seeds {1, 7, 42, 99, 142} → ALL reach 461

The seed-offset=110 bf_bw partial (232 cells, 426 matched) was attacked with ALNS basic 30min using 5 different ALNS seeds:

| ALNS seed | Final score | Corners (TL,TR,BL,BR) |
|---|---|---|
| 1   | 461 | (1, 2, 3, 0) |
| 7   | 461 | (1, 2, 0, 3) |
| 42  | 461 | (1, 2, 0, 3) |
| 99  | 461 | (1, 2, 0, 3) |
| 142 | 461 | (1, 2, 0, 3) |

**5/5 hits = 100% reproducibility from seed110 partial.** Not a one-shot — the 461 ceiling is genuinely the basin's floor for this partial.

## Plus seed111 × seed=42 → 461 (IDENTICAL to seed110 s42)

The seed-offset=111 partial × ALNS seed=42 also reached 461 — and **byte-identical to seed110 s42's 461** (256/256 same piece+rot).

## Structural analysis — TWO distinct 461 basins

Pairwise piece+rot agreement across the 6 saved 461 boards:

| | s1 | s7 | s42 | s99 | s142 | seed111-s42 |
|---|---|---|---|---|---|---|
| s1 | - | 215 | 215 | 212 | 215 | 215 |
| s7 | 215 | - | **256** | 217 | 252 | **256** |
| s42 | 215 | **256** | - | 217 | 252 | **256** |
| s99 | 212 | 217 | 217 | - | 216 | 217 |
| s142 | 215 | 252 | 252 | 216 | - | 252 |
| seed111-s42 | 215 | **256** | **256** | 217 | 252 | - |

**Findings:**
- s7, s42, seed111-s42 are **IDENTICAL** (256/256) — 3 paths to same 461.
- s142 is 252/256 to that group — same basin, 4 cells differ.
- s99 is 217/256 to that group — same corners (1,2,0,3) but different interior — **second basin within same corner perm**.
- s1 is 215/256 to all others AND uses corner perm (1,2,3,0) — **third 461 basin in a different corner perm**.

So:
- **Basin A** (corner perm (1,2,0,3), interior I): seed110 s7, s42, s142, seed111-s42 — 4 paths
- **Basin B** (corner perm (1,2,0,3), interior II): seed110 s99
- **Basin C** (corner perm (1,2,3,0)): seed110 s1

**3 distinct 461 basins.**

## Fine-offset sweep results (offsets 105-113 × seed=42)

| Offset | Score |
|---|---|
| 105 | 458 |
| 107 | 459 |
| 108 | 457 |
| 109 | 457 |
| 110 | **461** ← record |
| 111 | **461** |
| 112 | 458 |
| 113 | 458 |

Only offsets 110, 111 reach 461 with seed=42. Tight neighborhood.

## Implications

1. **461 is the empirical ceiling from this attack vector** (bf_bw + ALNS basic). Not a single-seed fluke.
2. **3 distinct 461 basins exist** — the basin space at score 461 is at least 3 connected components.
3. **All 3 basins are likely MIP-locally-optimal at halo-2** (per vol-118 rigidity pattern; needs verification).
4. **Going to 462+ likely requires a STRUCTURALLY DIFFERENT attack** (different schedule, escape ops, etc.) — basic ALNS plateaus at 461 across all tested (offset, seed) pairs in this neighborhood.

## Next steps

- **Run ALNS with mega_mix/halfboard on 461 boards** (in flight) — if any reaches 462, that's the next +1.
- **Try schedule v15** on bf_bw (not v17a) to see if different schedule reaches new basin family.
- **Verify halo-2 local-optimality** via cluster MIP on the 461 boards.

## Linked

- [[record-461-2026-05-18]]
- [[record-460-2026-05-18]]
- [[../sessions/vol-125]]
