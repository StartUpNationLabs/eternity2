# RESEARCH_NOTES_17.md — vol-17 live log

Session start: 2026-05-12 22:58 CEST · agent: autonomous overnight (~8 h)
Branch: `develop` · Prev volume: vol-16 closeout commit on `develop`.

Vol-17 is back on **new algorithms, math, research**. Vol-16 shipped the
4.6× engine throughput + Cat-2 Stage A trait scaffolding; vol-17 picks up
where vol-15 hit the cliff. Plan in `RESEARCH_NOTES_17_PLAN.md`; ideas A–L
ranked by EV.

## Carry-in (one paragraph each)

* **vol-16 closeout** (`project_e2_vol16_closeout.md`):
  21 commits, BLACKWOOD_RAW 80k→367k nps (4.6×), joe 2.4k→7k nps (2.9×),
  `score_board` O(n²)→O(n) algorithmic win, bench-audit dedup −652 LoC,
  Option A architectural decision committed in V2_DESIGN.md.
* **vol-15 results** (`project_e2_vol15_blackwood_results.md`):
  Blackwood algorithm shipped end-to-end. Canonical-E2 seed-1 best after
  cliff-fix + propagator drop = **416/480 vs baseline 439/480 (Δ=−23)**.
  Schedule curve is mistuned — calibration from community 469 is the
  vol-16+ unblock. Discovery: **+260 ALNS lift from Blackwood seeds**
  vs baseline's +147 — motivates the Blackwood-then-CSP pipeline.
* **vol-17 Blackwood-then-CSP** (`project_e2_vol17_blackwood_then_csp.md`):
  user-proposed Variant A (sequential pipeline). Critical caveat:
  break-mismatched partials may violate AC-3/gacolor/NS-1 invariants
  when pinned.
* **vol-17 plan** (`RESEARCH_NOTES_17_PLAN.md`): 12 ideas A–L; default
  ordering A→L→K→D→B→H. Bars T1=calibrated Blackwood + ≥454,
  T2=+1 algo, T3=>446, T4=+2 algos + publishable result.
* **CLAUDE.md project traps**: no_std core; clock shim per crate; wasm-opt
  flags; perf tests `#[ignore]`; `#![forbid(unsafe_code)]`; Cat-2 trait
  migration must preserve `undo_words_arena`.

## Day-zero state checks

* `ps aux` ⇒ no running solver background processes.
* `git status` ⇒ clean (stale: frontend/dist + v12_run log files).
* `date` ⇒ 22:58 CEST.

## Community corpus reality-check (matters for idea A)

Index has 124 boards, but on **canonical Eternity2** only:

| score | boards |
|---|---:|
| 480 | 1 (McGavin 228701155, 2023-10) |
| 469 | 1 (McGavin 172011298, 2020-09) |
| <469 | (rest of the 124) |

This is N=1 + a saturator. The Blackwood-decoded references
(`groups_183676823`, `groups_197822677`, the JBlackwood+Jef family) all
encode on Blackwood's **own** puzzle variant — different piece set, so the
empirical heuristic-color curve does NOT directly transfer. The
calibration recipe ("median / 25th percentile across boards") collapses to
"the single observed curve from McGavin's 469" + 480 tail.

Implication: idea A becomes "fit the curve from ONE 469 board + saturator
+ Blackwood's reported 469-recipe as a cross-check". I'll still build the
infrastructure to ingest multiple boards (in case more corpus shows up,
and so the tooling is reusable), but lower my expected-improvement bar
from "≥454 cold-start" to "≥425 cold-start". The structural T1 (≥454)
target may need to come from L (cold portfolio) instead.

## Plan for the night (revised live)

1. **Idea A (Blackwood calibration)** — build the calibration tool from
   community 469 (+ 480) board. Even with N=1 the curve is empirical
   truth — currently we use Blackwood's own scaled curve, which is a
   transferred prior from a different piece set. Should still narrow the
   schedule cliff.  Wall-budget: ~2 h.
2. **Idea L (cold portfolio, ≥8 seeds)** — at the new 4.6× throughput,
   run baseline `joe_depth150_bp_par` on 8 seeds, 5 min CP + 5 min ALNS
   each. Variance data we've never had + a cheap T1 hedge. Background
   running while step 1 wraps up.  Wall-budget: ~2 h once kicked off.
3. **Idea K (Blackwood-then-CSP pipeline)** — Variant A: BLACKWOOD_RAW →
   place-as-hints → joe_depth150_bp_par → ALNS. Sound under no-break
   ablation. Wall-budget: ~2 h.
4. **Idea D (Zobrist for PT)** — small clean win, opportunistic.
5. **Closeout** memory entry + RESEARCH_NOTES_17 closeout — ~1 h.

If time spillover: H (Fiedler ordering) or B (cluster-swap ALNS).
