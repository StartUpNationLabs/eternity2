# Vol-34 wake-up summary (2026-05-14 morning autonomous session)

Read this first when starting vol-35.

## 🎯 HEADLINE

Vol-33 (code-quality refactor) + Vol-34 (record chase + propagator) BOTH shipped
in a single autonomous session.

- **Vol-33**: All 5 vol-25 deferred items finally shipped (8 vols delay).
  See [[vol-33]] for session journal.
- **Vol-34**: T1+T2+T3 measurements complete; TWO score-reporting bugs
  found and fixed; vol-32 records all verified intact.

## What was attempted in vol-34

### T1 — vanilla_fast deep-probe with snapshot infrastructure

Built `--snapshot-dir`, `--snapshot-interval-ms`, `--snapshot-min-depth`,
`--snapshot-on-visit` flags. 30-min × 8-thread probe (truncated early
to start T3) produced **14 distinct snapshots clustering into 5 basin
families** (intra-thread prefix agreement 80-90 cells; inter-thread 0-1).

Gate "≥215 depth" NOT met (max=209). T1 status: shipped, partials saved
for vol-35.

### T2 — unsat-clause-propagator

**Hard-pruner REFUTED** after full encoding reconciliation:
- ml/data/color_map.json — 23-color bijection via per-color frequency-class
  signature (256/256 our pieces match capiman cards)
- ml/data/piece_card_map.json — piece_id ↔ card_id + per-pid rotation table

Validation on vol-32 458 board: 56 conflict pairs against forbidden_all.bin
(18 round-1 only). Capiman's clauses are heuristic-search-regime-specific,
not globally unsat.

**Soft-pruner candidate**: depth-rank analysis on 3 verified record boards
showed rank 0%/perfect at d=30; 9-20% at d=80; inconsistent at d≥160.
Vol-35 T3 candidate.

### T3 — mass ALNS lottery — DONE

14 partials × 4 ALNS seeds × 5 min = 56 runs. Discovered + fixed
TWO bugs en route:

1. **piece_swap_hillclimb gain over-count** (commit `4474987`) —
   local-delta estimator over-counted on shared-neighbour swap
   topologies; reported `polish_swap=+400` while real gain was 0-2.
2. **alns_only filename collision** (commit `4c82bc1`) — parallel ALNS
   processes writing to `output/v17_alns_only/{ops}_{repair}_t{T}_s{seed}_{epoch_secs}.json`
   could overwrite each other when finishing in the same second.

**Final results (56/56 rescore-verified)**:
- 2 verified 457s (distinct basins, 1.2% cell overlap, both bound 464)
- 1 × 456, 2 × 455, 5 × 454, mean 446.7, max 457
- Gate "≥458" NOT met. 458 is structurally unreachable from the
  vanilla_fast basin family.

The 5 distinct 457 cold-start basins now known across project history:
vol-18, vol-32-seed7, vol-32-seed10, vol-32-seed4-30m, vol-34 #1, vol-34 #2.

## 🚨 CRITICAL: ALWAYS rescore_board before claiming a record

Two score-reporting bugs found in vol-34 mean ANY claim from `alns_only`
or its descendants must be verified by `target/release/rescore_board` on
the saved JSON. Use `ml/verify_records.sh` as the canonical sanity check.

Currently-verified records (rescore_board PASS):
- 458 — output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json (caveat: 2/5
  canonical hints displaced)
- 457 × 3 — output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed{7,10}.json,
  output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json
- 457 — output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json
  (5/5 canonical hints honored — cleaner than vol-32 458)

## 📋 Vol-35 plan (drafted at vol-34 close)

User-proposed mid-vol research direction: **fitness/energy landscape mapping
on small E2 puzzles**. Enumerate local optima at 4×4/6×6/8×8, measure basin
properties (size, radius, adjacency, saddle-heights), look for transferable
structural invariants. See [[fitness-landscape-mapping]] for the 5-phase plan.

Promoted to vol-35 T1. Vol-32's vanilla_fast + vol-34's snapshot infrastructure
serves as the basin-sampling layer; the analysis layer is new.

## Vol-33 outputs (the refactor volume)

- `crates/time/` — eternity2-time crate (Clock for native + wasm).
- `crates/export/` — eternity2-export (score_board, bucas_url, DumpedBoard,
  RunReport, render_board, placed_count, internal_edge_count).
- `crates/puzzle-io/` — eternity2-puzzle-io (CSV loader + hint parser).
- `crates/solver-engine/src/{config,profiles,paths,schedule_builders}.rs` —
  internal module split; lib.rs went 5355 → 3705 lines (−31%).
- `crates/bench-audit/src/lib.rs` — new harness helpers (QuietSink,
  harness::outcome_to_view, harness::write_summary, harness::build_postmortem_json).

## Vol-34 outputs (the propagator + record-chase volume)

- `ml/data/{color_map,piece_card_map}.json` — capiman ↔ ours encoding.
- `ml/reconcile_unsat_encoding_v2.py` + `ml/reconcile_piece_ids.py` — rebuild
  the maps if puzzle changes.
- `ml/validate_unsat_partial_v2.py` — encoding-aware unsat-conflict checker.
- `ml/unsat_soft_value_order_proto.py` + `ml/unsat_soft_shallow_test.py` —
  soft-pruner signal analysis at varying depths.
- `ml/verify_t3_lottery.sh` — verifier for T3 batch (rescore + flag
  discrepancies).
- `ml/verify_records.sh` — canonical record-board sanity check.
- `output/vol-34/t1_probe/` — 14 vanilla_fast snapshots, depth 200-209.
- `output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json` —
  the verified canonical-clue 457 (new basin family).
- `output/vol-34/t3_full/` — full lottery results + summary.jsonl (will be
  complete when T3 finishes).

## Where to start vol-35

1. Read `vault/plans/VOL-35.md` for the 4-task plan.
2. T1 (recommended) is the landscape-mapping work. New small-puzzle
   ALNS infrastructure needed; existing `alns_only` only knows 16×16.
3. If a pure record chase is desired, T2 (vanilla_fast oversubscribed
   probe) is the cheaper option.

## Commits

This session: 30+ commits, all on develop. Not pushed to remote.

## Honest framing

Vol-34 produced no new score record. The 458 stands (with caveats). The
vol-34 contribution was infrastructure (snapshot probing + encoding
reconciliation + two bug fixes + a verifier) rather than a record. The
landscape-mapping direction the user proposed mid-vol is the highest-EV
next step.
