#!/usr/bin/env bash
# Vol-118 T10 — bf → Hungarian DIRECT (skip bound-ascent).
#
# Hypothesis: the bound-ascent step shuffles pieces toward color-balance
# which homogenizes basins. All paths through bound-ascent land in
# UB=458 basins (vol-118 T6 measurement). Skipping bound-ascent might
# preserve color-profile diversity → different UB basins → potentially
# higher ALNS ceiling.
#
# Pipeline (per seed-offset):
#   par-8 bf 60s → Hungarian directly → bound-ascent UB measure → ALNS 8 trials

set -e

OUT_DIR="output/vol-118/T10_bf_to_hungarian_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
SUMMARY="$OUT_DIR/_summary.csv"
echo "seed_off,bf_score,hungarian_score,UB_post_hungarian,alns_max" > "$SUMMARY"

SEEDS="${SEEDS:-0 100 500 1000 2000}"
BF_BUDGET_MS="${BF_BUDGET_MS:-60000}"

for SOFF in $SEEDS; do
  echo "=== seed-offset $SOFF ===" | tee -a "$OUT_DIR/_log.txt"

  PARTIAL="$OUT_DIR/par_bf_seed${SOFF}.json"
  ./target/release/bf_bw_schedule_hinted --threads 8 --seed-offset $SOFF \
    --budget-ms $BF_BUDGET_MS --schedule v17a --dump-partial "$PARTIAL" \
    >> "$OUT_DIR/_log.txt" 2>&1
  BF_SCORE=$(./target/release/rescore_board "$PARTIAL" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  # Direct Hungarian on the bf partial.
  ./target/release/edge_target_match --board "$PARTIAL" >> "$OUT_DIR/_log.txt" 2>&1 || true
  HG=$(ls -t output/v21_target_match_*.json 2>/dev/null | head -1)
  HG_OUT="$OUT_DIR/hg_seed${SOFF}.json"
  cp "$HG" "$HG_OUT"
  HG_SCORE=$(./target/release/rescore_board "$HG_OUT" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  # Measure UB of the Hungarian board (run bound-ascent for diagnostic only).
  ./target/release/edge_bound_ascent --board "$HG_OUT" --iters 500 --seed 42 \
    --acceptance accept >> "$OUT_DIR/_log.txt" 2>&1 || true
  BA=$(ls -t output/v21_bound_ascent_b*.json 2>/dev/null | head -1)
  UB=$(basename "$BA" | sed -E 's/.*_b([0-9]+)_.*/\1/')

  # ALNS on the DIRECTLY-Hungarian'd board (NOT the bound-ascent-polished one).
  best=0
  for ASEED in 1 7 42 100; do
    for OPS in basic winning5; do
      R=$(./target/release/alns_only --cp-board "$HG_OUT" --alns-budget-ms 60000 \
        --seed $ASEED --ops $OPS 2>&1 | grep "new_best" | tail -1 | awk '{print $NF}' | sed 's/new_best=//')
      if [ -n "$R" ] && [ "$R" -gt "$best" ] 2>/dev/null; then best=$R; fi
      echo "    alns seed=$ASEED ops=$OPS $R" | tee -a "$OUT_DIR/_log.txt"
    done
  done

  echo "$SOFF,$BF_SCORE,$HG_SCORE,$UB,$best" >> "$SUMMARY"
  echo "  bf=$BF_SCORE  hungarian=$HG_SCORE  ub=$UB  alns_max=$best"
done

echo ""
echo "=== Summary ==="
cat "$SUMMARY"
