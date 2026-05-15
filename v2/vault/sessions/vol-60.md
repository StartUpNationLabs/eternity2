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

## T3 — initial sweep (v1) results (perms 0-7 only)

8 of 24 perms completed before script restart issue. Findings:

| perm | TL | TR | BL | BR | depth | best partial score | matches record |
|------|---:|---:|---:|---:|------:|-------------------:|---------------|
| p00 | 0 | 1 | 2 | 3 | 207 | 426/480 | (no match) |
| p01 | 0 | 1 | 3 | 2 | 207 | 426/480 | (no match) |
| p02 | 0 | 2 | 1 | 3 | 207 | 426/480 | **FB blackwood 457** |
| p03 | 0 | 2 | 3 | 1 | 207 | 426/480 | (no match) |
| p04 | 0 | 3 | 1 | 2 | 210 | 433/480 | **FA vol-32 458** |
| p05 | 0 | 3 | 2 | 1 | 210 | 433/480 | **vol-35 457** |
| p06 | 1 | 0 | 2 | 3 | 210 | 433/480 | (no match) |
| p07 | 1 | 0 | 3 | 2 | 210 | 433/480 | (no match) |

### Critical observation

Within each (TL, TR) group, BL/BR varies but score is IDENTICAL. This
is because **row-major scan order doesn't reach BL/BR cells (240, 255)
at depth 210** — only TL+TR have been placed, BL/BR pieces remain in
the "reserved" pool via piece-uniqueness but don't yet constrain.

So **24 perms collapse to 12 distinct (TL, TR) test points** in 5min
budget. To exercise all 24 distinctly, need depth ≥ 256 (impractical
at vanilla_fast) or a different scan order.

The 12 (TL, TR) combinations:
- (0,1), (0,2), (0,3), (1,0), (1,2), (1,3),
- (2,0), (2,1), (2,3), (3,0), (3,1), (3,2)

Sweep v1_run2 covers the remaining 16 perms (= 8 more (TL,TR) pairs).

## Process corrections this vol

1. **alns_only was missing --extra-hint** (mirrors vanilla_fast).
   Fixed: added the flag with the same semantics. The vol-60
   corner-sweep ALNS phase needs this so corners stay pinned.

2. **Scripts were overwriting outputs**. Fixed:
   `vol60_corner_sweep{,_v2,_alns}.sh` now use `VOL60_RUN_TAG`-based
   timestamped output dirs.

Both per user feedback this turn.

## Linked

- [[../sessions/vol-59]] — predecessor
- [[../sessions/vol-58]] — vol-58 T5 McGavin MIP
- [[../plans/VOL-60]] — vol-60 plan
- memory: `feedback_fix_broken_code`, `feedback_never_overwrite_results`
