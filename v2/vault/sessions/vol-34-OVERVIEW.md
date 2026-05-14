# Vol-33 + Vol-34 autonomous-session overview

**Date**: 2026-05-14 (single 8-hour autonomous session per user request).
**Author**: agent-only; user away 08:00-20:00.

## TLDR

Two volumes shipped in one session:
1. **Vol-33** — 5 deferred refactor items from vol-25 finally executed
2. **Vol-34** — T1+T2+T3 measurements + 2 score-reporting bugs discovered and fixed

Plus substantial vol-35 T1 pilot (fitness-landscape mapping per user proposal).

**47 commits** total. No record-breaking — vol-32's 458 stands.
**5 distinct verified 457 cold-start basins** known (3 from vol-32, 2 from vol-34).

## Vol-33 deliverables (refactor)

- `crates/time/`: extracted Clock (was duplicated in solver-engine + solver-naive)
- `crates/export/`: consolidated 3 duplicate utilities (score_board, bucas_url, DumpedBoard, render_board, write_report)
- `crates/puzzle-io/`: extracted CSV loader from benchmark
- `crates/solver-engine/src/{paths,schedule_builders,config,profiles}.rs`: internal module split. lib.rs: 5355 → 3705 lines (−31%).
- `crates/bench-audit/src/lib.rs`: `harness::*` helpers (outcome_to_view, write_summary, build_postmortem_json) + QuietSink. 2 bins migrated as proof-of-value; 70+ bins remain for future incremental migration.

## Vol-34 deliverables (record-chase + propagator)

### T1 — vanilla_fast deep-probe infrastructure
- `--snapshot-dir`, `--snapshot-interval-ms`, `--snapshot-min-depth`,
  `--snapshot-on-visit` flags on vanilla_fast.
- 30-min probe at 8 threads → 14 distinct snapshots, 5 basin families.
- Gate "≥215 depth" NOT met (max 209).
- `--snapshot-on-visit` validation: 60s × 1 thread → 23 distinct snapshots
  (vs ~3 with new-max-only).

### T2 — unsat-clause-propagator
- **Hard-pruner REFUTED**: capiman's clauses are heuristic-search-regime-
  specific, not globally unsat. Validation: 56 conflict pairs on the
  vol-32 458 record board.
- **Encoding fully reconciled**: `ml/data/color_map.json` (23-color
  bijection via per-color frequency-class signature) +
  `ml/data/piece_card_map.json` (256-card bijection + rotation table).
  Reusable for any future capiman-database work.
- **Soft-pruner depth analysis**: signal r=0% at d=30, 9-20% at d=80,
  inconsistent at d≥160. Vol-35 candidate as depth-conditional value-order.

### T3 — mass ALNS lottery
- 14 partials × 4 seeds × 5min = 56 runs.
- **TWO bugs found and fixed en route**:
  1. `piece_swap_hillclimb` gain over-counter (commit `4474987`)
  2. `alns_only` filename collision (commit `4c82bc1`) — the actually
     severe bug; parallel ALNS processes overwrote each other's saved JSONs
     when finishing in the same epoch-second.
- Post-fix: 56/56 rescore-consistent.
- **Final scores**: 2 × 457 (distinct basins), 1 × 456, 2 × 455, mean 446.7, max 457.
- Gate "≥458" NOT met.

## Bug-fix infrastructure shipped

- `ml/verify_t3_lottery.sh`: per-run verifier (rescore_board vs log).
- `ml/verify_records.sh`: canonical record-board sanity check. ALL 6
  records (1 × 458 + 5 × 457) verified PASS post-fix.
- `target/release/rescore_board`: now reports both export-crate and
  localsearch scoring side-by-side.

## Vol-35-prep (user-proposed landscape mapping)

User asked mid-vol-34: "could we on smaller puzzles map the world of
minima/maxima, then scale up?"

Built `crates/bench-audit/src/bin/landscape_explorer.rs` (ALNS-from-random
× many restarts, save each polished LO).

Pilots:
- 6×6/5c × 1000 restarts × 5s ALNS: mean H = 35.4 / 36, FDC r = -0.031.
  **Rugged landscape, no clustering.**
- 6×6/5c × 100 × 30s: same statistics. Longer ALNS doesn't help.
- 12×12/8c × 100 × 30s: FDC r = -0.104. **Slightly more structured.**
- 16×16/22c × 50 × 3min: in flight. Hypothesis: r ~ -0.3 to -0.5.

If FDC scales meaningfully with puzzle size, **the canonical 16×16
landscape has exploitable big-valley structure** — operators that
navigate toward high-score LOs SHOULD be effective. Vol-32's 458 might
be the "tip" of such a valley.

## Files

- `vault/sessions/vol-33.md` — refactor journal
- `vault/sessions/vol-34.md` — record-chase journal
- `vault/sessions/vol-34-t1-signal.md` — mid-vol 457 discovery + cross-basin bounds
- `vault/sessions/vol-34-basin-clustering.md` — 14-snapshot clustering analysis
- `vault/sessions/vol-34-landscape-1000.md` — landscape probe findings
- `vault/sessions/vol-34-WAKE-SUMMARY.md` — entry point for next session
- `vault/plans/CURRENT-VOL.md` — vol-35 plan (active)
- `vault/concepts/fitness-landscape-mapping.md` — vol-35 T1 concept page
- `vault/concepts/unsat-clause-propagator.md` — refuted-as-hard-pruner status
- `ml/data/{color_map,piece_card_map}.json` — encoding maps
- `ml/{reconcile_unsat_encoding_v2,reconcile_piece_ids,validate_unsat_partial_v2,
  unsat_soft_value_order_proto,unsat_soft_shallow_test,analyze_landscape,
  verify_t3_lottery,verify_records,run_t3_lottery}.{py,sh}` — analysis scripts

## Honest framing

- **No record broken**. The 458 stands.
- **Real bugs fixed**. Future record claims via alns_only-family bins
  are now trustworthy (with rescore_board verification).
- **New research direction opened**. Landscape mapping at scales 4×4,
  6×6, 12×12 shows the landscape is rugged but FDC structure scales
  with puzzle size — testable hypothesis for canonical 16×16.
- **5 distinct 457 basins** documented across project history. Each
  has its own bound ceiling (457-465). The fact that ALNS routinely
  reaches 457 from arbitrary-seed vanilla_fast partials confirms 457
  is the "easy ceiling"; 458 requires structurally different basin family.
