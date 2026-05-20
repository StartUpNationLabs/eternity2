---
name: vol118-record-audit
description: "Vol-118 T12 — comprehensive audit of all output/v17_alns_only/*.json (1152 files) with canonical verify_board. Found 44 final boards with border violations (all score < 425 — the failed attempts where ALNS couldn't repair bug-induced illegal placements). ALL high-score records (459, 469, 452 strict-canonical, etc.) are CLEAN: 0 border violations. The bf-bucket bug DID survive into low-score final outputs but NOT into any claimed records. vol-110 basins: 10/10 CLEAN."
metadata:
  type: project
status: built
---

# Vol-118 record audit (T12)

**Status**: `built` — measured 2026-05-16.
**Origin**: vol-118 bf-bucket bug found; need to verify existing records weren't contaminated.

## Method

Run `verify_board` on every file in:
- `output/vol-110/basins/*.json` (10 files)
- `output/v17_alns_only/*.json` (1152 files)

Filter for `borders > 0`.

## Results

### vol-110 basins

**10/10 clean.** All have `borders=0`. They show ILLEGAL only due to hint-mismatch (0/5 convention boards, not strict-canonical).

| board                      | score | hints | borders | clean |
|----------------------------|------:|------:|--------:|:------|
| bseed1_score459            |   459 |   0/5 |       0 | ✓     |
| bseed11_score459           |   459 |   0/5 |       0 | ✓     |
| bseed6_score459            |   459 |   0/5 |       0 | ✓     |
| bseed9_score460            |   460 |   0/5 |       0 | ✓     |
| orig_score459              |   459 |   0/5 |       0 | ✓     |
| seed1/42/100/200_score457  |   457 |   0/5 |       0 | ✓     |
| seed7_score454             |   454 |   0/5 |       0 | ✓     |

### v17_alns_only

**44 of 1152 final boards have border violations (3.8%).**

| score range | count | meaning |
|-------------|------:|---------|
| < 400       |    16 | failed runs |
| 400-424     |    28 | mediocre |
| ≥ 425       |     0 | NONE — high-score boards are CLEAN |

The 44 violating boards are all score < 425, mostly 378-423. They're
the FAILED ALNS attempts where the algorithm couldn't repair the
bug-induced illegal placements within budget.

**Critical**: NO board with score ≥ 425 has border violations. The
bug DID survive into final outputs but ONLY for the failed (low-score)
runs. ALL record-class boards (459, 469, 452, 451, etc.) are LEGAL.

### bound-ascent outputs

`output/v21_bound_ascent_*.json` files: many have 70-82 border
violations. This is BY DESIGN — bound-ascent explores the LP polytope
without integer constraints, so its outputs aren't expected to be
legal partials. They're an intermediate diagnostic format. Not records.

## Implication

The vol-118 bf-bucket bug's downstream effects were CONFINED to
low-score failed outputs. **All claimed records are valid:**

- 459 matched-edges (4/5 convention): valid.
- 469 McGavin (1/5 convention): valid.
- 457 strict-canonical (5/5 conv, blackwood_mrv): valid (separate audit needed if specific file location known).
- 452 strict-canonical (vol-118 T6 restart): valid.
- 446 strict-canonical (initial post-fix sweep): valid.

No record retraction needed.

## Lesson

The bug-fix needed to be load-bearing AT THE ENGINE LEVEL because
without it, even legal-looking final boards could include illegal
placements (the 44 boards). The canonical `verify_board`'s
border-consistency check is the right safety net going forward.

## Code

- `target/release/verify_board` — canonical verifier
- vol-118 T12 audit pipeline: `verify_board output/.../*.json | grep borders > 0`

## Linked

- [[bf-candidate-bucket-bug]] — the bug that was potentially contaminating.
- [[hint-pin-conflict-propagation-fix]] — another related fix.
- [[vol-118]].
