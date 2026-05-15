# Vol-60 — corner-assignment sweep

**Open**: 2026-05-15 (continuing autonomous session post-vol-59)
**Status**: in-progress.

## T3 — corner-assignment sweep (RUNNING)

User question: "by considering we have something like 16 known
starting positions if we pin hints+corners, how could that help?"

Re-derived: there are **24 valid corner-piece permutations** (4! since
each corner has exactly 1 valid rotation per corner-piece).

### KEY ANALYSIS — corner perms across our records

| Record | TL | TR | BL | BR | Perm |
|--------|---:|---:|---:|---:|------|
| FA vol-32 458 | 0 | 3 | 1 | 2 | (0,3,1,2) |
| FB blackwood_mrv 457 ×3 | 0 | 2 | 1 | 3 | (0,2,1,3) |
| vol-35 diverse/full 457 | 0 | 3 | 2 | 1 | (0,3,2,1) |
| **Lottery 458** (vol-56) | **2** | **0** | **1** | **3** | (2,0,1,3) |
| **McGavin 469** | **3** | **2** | **0** | **1** | (3,2,0,1) |

**Across 9 records, only 5 of 24 corner permutations are represented.
19 of 24 are COMPLETELY UNEXPLORED.**

Critically:
- McGavin's 469 basin uses corner permutation (3,2,0,1) — never tried
  by our algorithms.
- vol-56 lottery 458 used (2,0,1,3) — a 3rd unique corner perm
  beyond our two main basin families.

### Hypothesis

Different corner permutations → fundamentally different basin
families. The community 469 ceiling is reachable from corner perm
(3,2,0,1) but NOT from our (0,3,1,2) or (0,2,1,3). Systematic sweep
across all 24 perms tests this.

### Sweep design

24 perms × 5 min CP (vanilla_fast with --pin-hints + 4 extra-hints
fixing the corners) = 24 deep partials. Each represents a distinct
basin family.

Smoke test: 1 perm reaches depth 207, score 426 in 30s. With 5min
budget, depth ≥200 expected per perm. Wall: ~15 min total.

T4: run ALNS lottery on each perm's best snapshot (4 seeds × 5min,
96 jobs total, ~60 min wall).

## Linked

- [[../sessions/vol-59]] — predecessor
- [[../sessions/vol-58]] — vol-58 T5 McGavin MIP
- [[../plans/VOL-60]] — vol-60 plan
