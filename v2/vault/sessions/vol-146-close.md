# Vol-146 Close — McGavin 469 attack inert

7 ALNS jobs × 30min × {3 McGavin 469 records, 1 463 record} × {baseline, +forbid}:

| Board | Init | Best | Δ |
|-------|------|------|---|
| McGavin 469 (baseline) | 469 | 469 | 0 |
| McGavin 469 (+forbid) | 469 | 469 | 0 |
| McGavin-top14-469 (baseline) | 469 | 469 | 0 |
| McGavin-top14-469 (+forbid) | 469 | 469 | 0 |
| NEW-469-swap (baseline) | 469 | 469 | 0 |
| NEW-469-swap (+forbid) | 469 | 469 | 0 |
| from 463 (+forbid) | 463 | 463 | 0 |

**ZERO improvement across all 7 jobs.** McGavin 469 and the new 463
are deep local minima under ALNS+ForbidDestroy at 30min budget.

Confirms post-pivot pattern: short-budget local-search at record-tier
boards is structurally blocked. Both 461→469 and 469→480 gaps require
coupled global permutations.

## Linked
- [[forbidden-patch-theorem-2026-05-19]]
- [[intaglio-forbidden-patterns]]
