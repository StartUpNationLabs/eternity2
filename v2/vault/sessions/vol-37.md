# Vol-37 — re-evaluations, structural discoveries, make-canonical operator

**Theme**: After vol-36 close, mid-session re-evaluations (×2 user-prompted)
revealed I was repeatedly defaulting to lottery-style work despite the
saturation evidence. Structural discoveries shipped; no record-break.

## What was attempted

- T1 (planned): PT-from-canonical-454 hot exploration
- T2 (replaced): gradient + Hungarian projection (gh_e2) — novel algorithm
- T3 (replaced): structural-invariant scanner across 7 records
- T4 (replaced): pos 161 synthetic hint A/B in vanilla_fast
- T5 (replaced): make-canonical operator + canonical 454 production
- Repeatedly cancelled lotteries after re-evaluations

## What was measured / kept

- **make-canonical operator** (ml/make_canonical.py + prune_restart
  --pin-all --max-score): produces canonical-respecting boards from
  non-canonical records. vol-32 458 → canonical 446 in 0.1s.
- **canonical 454** (vol-36, vol-37 confirmation): new canonical record
  pathway. Score 454, 5/5 hints, piece-unique.
- **PT-from-canonical-454**: lifts 454 → 455 in 60s, plateau at 455
  for 20+ min. Modest +1 lift.
- **gh_e2** (gradient + Hungarian): shipped as `ml/gh_e2/gh_e2.py`.
  Score formula verified against rescore_board. Algorithm works but
  relaxation gap dominates: soft score climbs to 462, discrete projection
  stays 100-454. From canonical 454 init: stays at 454. **Doesn't break
  records in basic form.** Saved for future iteration with Gumbel-Softmax
  / straight-through estimator.
- **structural_scan.py**: mines 7 verified records (post pin-hints
  retraction). Found:
  - **3 cross-basin invariant cells beyond canonical hints**:
    - pos 0 (TL corner): pid 0 rot 3 — corner-forced
    - pos 1 (top row): pid 4 rot 0 — likely forced by border + pos 34 hint
    - **pos 161 (interior, x=1 y=10): pid 234 rot 0** — novel, not
      hint-adjacent, all 4 edges always perfectly matched.
  - 19 diversity=2 near-invariant cells (4-5/7 majority).
  - Cell-level value-order JSON dump (1024 candidates × 256 cells).
- **vanilla_fast --extra-hint POS:PID:ROT** (new flag) — synthetic
  hint support.
- **Pos 161 A/B** on vanilla_fast --pin-hints:
  - 60s × 8 thread: -8 depth, -17 score (early-pin trap not navigable)
  - 5min × 8 thread: +2 depth, +4 score (modest lift)

## What was refuted

- **Lotteries on saturated 457 attractor**: cancelled mid-execution
  after re-evaluation showed predictable saturation outcomes.
- **gh_e2 in basic form**: relaxation gap means soft optimum doesn't
  correspond to integer optimum. Strong λ traps at 454; weak λ goes
  to relaxed-saturated state with bad Hungarian projection.
- **Pos 161 hint at SHORT budget**: prune-then-fix is harder than
  fix-from-scratch when budget is tight.

## Discoveries that didn't pan out (but kept as records)

- Pos 161 = pid 234 rot 0 hint helps at 5min × 8t budget but only by
  +4 score. Doesn't break 458.
- Canonical 454 from make-canonical operator is a new pathway but
  below existing 457 record.
- PT-from-454 reaches 455 (vs 454 starting), below 457 record.

## Concepts touched

- new: **make-canonical operator** ([[make-canonical]] TODO)
- new: **cross-basin invariants** beyond canonical hints
- new: **gh_e2 relaxation** (refuted in basic form, kept for iteration)
- amended: [[scan-order]] — pos-161 hint depends on budget × scan-order interaction

## Records ledger (no change)

| score | canonical | source |
|---:|:---:|---|
| 458 | 3/5 | vol-32 vanilla_fast → ALNS |
| 457 | 5/5 | vol-32 blackwood_mrv × 3 |
| 456 | 5/5 | vol-32 blackwood_raw seed 2, 4 |
| 454 | 5/5 | vol-36 make-canonical → ALNS seed 5 (NEW pathway) |

**Cold-start canonical best: 457 (unchanged).**
**Cold-start absolute best: 458 (3/5 hints, unchanged).**

## Open at close

1. **Re-evaluation has happened TWICE in vol-37**. Pattern: I default to
   lottery work after each innovation attempt. Vol-38 must have a CONCRETE
   buildable goal, not a "try X then if it fails try Y" plan.
2. **The 458→469 gap requires community-scale technique** (Blackwood
   schedule calibration + days of compute + LP-style bound algorithm).
   Our stack realistically caps at 458-463.
3. **vol-37 spent ~2 hours building tools that didn't break records**.
   Tools are real (structural_scan, make_canonical.py, gh_e2.py,
   vanilla_path) but the headline metric didn't move.

## What vol-38 should NOT do

- ❌ More ALNS lotteries (vol-36 + vol-37 spent 4 separate lottery
  attempts — none breaking records).
- ❌ More schedule calibration (already at corpus data limit).
- ❌ More gradient relaxation variants.
- ❌ More structural scans on the same record set.

## What vol-38 SHOULD do

**One focused build**: pick a SINGLE concrete unbuilt item from BACKLOG.
Ship it. Measure it. Then close vol-38. Do NOT pivot mid-vol.

Candidates (ranked by EV/effort):
1. **No-good CDCL learning** (vol-29 BACKLOG, ~2d work). Standard SAT
   technique never applied to E2. Likely +5-15% search reduction per
   sub-tree; compounding speedup across runs.
2. **Soft unsat-pruner depth-conditional** (vol-34 BACKLOG, ~1d).
   Capiman's unsat database as ValueOrder::UnsatSoft at depth<100.
   Vol-34 measured signal strength.
3. **Verify-record-then-improve toolkit**: an explicit pipeline that
   takes any record → make-canonical → prune-restart → ALNS → verify.
   Productionization of vol-36/37 work.

## Linked

- [[vol-36]] — predecessor
- [[vol-37-re-evaluation]] — first re-eval at 16:48
- [[vol-37-pos161-discovery]] — pos 161 detail
- `ml/structural_scan.py`, `ml/gh_e2/gh_e2.py`, `ml/make_canonical.py`
