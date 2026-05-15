# Vol-79 — full-puzzle MIP + CAS edge-coverage audit (2026-05-15)

**Theme**: vol-79 was the dustbin run for *whether any of today's leftover
hypotheses produce a bound or a record*. They don't. Standing record
459/480 unchanged.

## What was attempted

1. **Full-puzzle Rust good_lp+HiGHS MIP** (256 cells × 256 pieces × 4
   rotations, 272k binary vars, 21k rows). Started ~4:50 wall-clock.
   Feasibility Jump phase reached best-feasible=41, best-bound=10560
   (objective sum, not edge-count). 0 dual progress at the 100s mark.
   Killed at ~5 min — bound was uninformatively loose; the MIP will
   not produce useful information in reasonable time. Conclusion:
   the LP relaxation of edge-matching at full-puzzle scale does NOT
   yield a non-trivial UB. The `bench-audit/border_lp_ub.rs`
   (border-only) approach gives sound border-LP bounds; full-puzzle
   LP-relaxation gives ~480 (vacuous).

2. **Vol-79 long Blackwood-then-CSP pipeline** with calibrated_v17a
   schedule, 180s + 240s + 180s stages. Stage 1 reached 362/480 +
   depth 192, but stage 2 CSP could NOT pin the 192 Blackwood
   placements (infeasibility under canonical-hint constraints +
   propagators). Fell back to canonical-only hints → 292/480. Stage
   3 ALNS: 304/480 final. **Stage 2 fallback is the structural
   issue**: Blackwood-RAW produces placements that violate
   gacolor / AC-3 / NS-1 constraints, so its 197-cell skeleton
   can't be pinned by joe_csp. This was previously noted in
   vol-15 BLACKWOOD_RAW notes ("AC-3/gacolor/NS-1 are UNSOUND
   under break-index allowance"). Composition Blackwood→joe_csp
   doesn't work for THAT reason; not a new finding.

3. **CAS edge-coverage audit**. Initially conjectured 112 edges
   were missed by CAS shell-objectives → ceiling of 368 or 452.
   Wrote draft vault page. Re-verified empirically with a proper
   edge classifier. **Initial counting was wrong**: ring (256) +
   inter-shell-boundary (224) = 480, all edges covered. CAS
   plateau at 433-436 is a piece-availability bound, not an
   edge-coverage one. Self-corrected the vault page; logged the
   mistake trail per "no quiet deletes".

## What was measured / kept

- CAS objective covers all 480 edges (per-shell breakdown: see
  [[cas-objective-ceiling-452]]).
- CAS plateau is piece-availability under greedy shell commit.
- Full-puzzle LP relaxation gives vacuous (480) UB, confirming
  border-only LP UB (`border_lp_ub`) is the right granularity.
- Blackwood-then-CSP composition refuted again (vol-15 finding
  re-confirmed).

## What was refuted

- The "CAS misses inter-shell edges" hypothesis (within this vol).
- "Full-puzzle MIP gives useful LP bound" (within this vol).
- "Blackwood-then-CSP at long budget produces 459+" (within this
  vol; vol-15 had refuted at short budgets).

## Concepts touched

- [[cas-objective-ceiling-452]] (NEW; corrected mid-write)
- [[concentric-annular-solving]] (parent reference)

## Open at close

- Joint shell-pair MIP for CAS (4× MIP cost; bounded-improvement
  estimate ~440-445 — still below 459, so deferred).
- Reading Blackwood/McGavin actual implementation (vol-14 noted
  this is the gap; 1+ day of code-reading).
- Sound LP/SDP UB < 480: full-puzzle direct didn't work. Possible
  paths: border-LP variants, lifted polytope (CG-cuts), Lasserre
  hierarchy. All ≥ days of work.

## Linked memory

- `memory/feedback_no_false_metrics.md` (relaxed_bound NOT a UB)
- `memory/project_e2_vol15_blackwood_results.md` (vol-15
  break-index unsoundness)
- `memory/feedback_e2_senior_researcher_mode.md` (do the math)

## Bottom line

Vol-79 is a **null result vol**. No record, no new sound bound.
Two hypothesis refutations, one self-corrected vault page.

Honest assessment: today's session-3 (post-22:00) has been
producing variants without new structural insight. The CAS
edge-coverage exercise was a real-math derivation but ended at
"the obvious is true" (480 edges all covered). The "novel
algorithm" pace has saturated; standing 459 stands.

Pivot next: read Blackwood/McGavin actual implementation
in preparation for a proper port (vol-80+). This is the
remaining unexploited gap per vol-14 documented analysis.
