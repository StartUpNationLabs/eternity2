#!/usr/bin/env bash
# Vol-118 T6 — par-bf seed-offset sweep with UB filter.
#
# For each seed-offset in a list, run par-8 hint-preserving bf for budget B,
# then bound-ascent + Hungarian, measure UB of the resulting board.
# Print: seed-offset, bf_depth, bf_score, Hungarian_score, UB.
#
# Goal: find a partial whose Hungarian-rebuilt board has UB ≥ 458 (the
# strict-canonical 457 record minimum survival threshold for ALNS to
# potentially reach it).

set -e

OUT_DIR="output/vol-118/ub_filter_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
SUMMARY="$OUT_DIR/_summary.csv"
echo "seed_off,bf_depth,bf_score,hungarian_score,bound_ascent_ub" > "$SUMMARY"

# Seed offsets to test. Start with diverse small set.
SEEDS="${SEEDS:-0 100 200 300 500 1000 2000 4000 8000}"
# Budget per bf run.
BF_BUDGET_MS="${BF_BUDGET_MS:-60000}"

for SOFF in $SEEDS; do
  echo "=== seed-offset $SOFF ===" | tee -a "$OUT_DIR/_log.txt"

  PARTIAL="$OUT_DIR/par_bf_seed${SOFF}.json"
  ./target/release/bf_bw_schedule_hinted --threads 8 --seed-offset $SOFF \
    --budget-ms $BF_BUDGET_MS --schedule v17a --dump-partial "$PARTIAL" \
    >> "$OUT_DIR/_log.txt" 2>&1
  if [ ! -f "$PARTIAL" ]; then echo "  bf failed"; continue; fi

  BF_INFO=$(./target/release/rescore_board "$PARTIAL" 2>&1 | tail -1)
  BF_PLACED=$(echo "$BF_INFO" | awk -F'\t' '{print $2}')
  BF_SCORE=$(echo "$BF_INFO" | awk -F'\t' '{print $4}')

  # Bound-ascent on partial.
  ./target/release/edge_bound_ascent --board "$PARTIAL" --iters 500 --seed 42 \
    --acceptance accept >> "$OUT_DIR/_log.txt" 2>&1 || true
  BA=$(ls -t output/v21_bound_ascent_b*.json 2>/dev/null | head -1)
  if [ -z "$BA" ]; then echo "  bound_ascent failed"; continue; fi
  BA_OUT="$OUT_DIR/ba_seed${SOFF}.json"
  cp "$BA" "$BA_OUT"

  # Extract UB from filename.
  BA_UB=$(basename "$BA" | sed -E 's/.*_b([0-9]+)_.*/\1/')

  # Hungarian.
  ./target/release/edge_target_match --board "$BA_OUT" >> "$OUT_DIR/_log.txt" 2>&1 || true
  HG=$(ls -t output/v21_target_match_*.json 2>/dev/null | head -1)
  HG_OUT="$OUT_DIR/hg_seed${SOFF}.json"
  cp "$HG" "$HG_OUT"
  HG_SCORE=$(./target/release/rescore_board "$HG_OUT" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  echo "$SOFF,$BF_PLACED,$BF_SCORE,$HG_SCORE,$BA_UB" >> "$SUMMARY"
  echo "  bf=$BF_PLACED/$BF_SCORE  hungarian=$HG_SCORE  ub=$BA_UB"

  # If UB >= 458, run ALNS (4 seeds × 2 ops) on this partial.
  if [ "$BA_UB" -ge "458" ] 2>/dev/null; then
    echo "  >> UB ≥ 458, running ALNS..."
    for ASEED in 1 7 42 100; do
      for OPS in basic winning5; do
        R=$(./target/release/alns_only --cp-board "$HG_OUT" --alns-budget-ms 60000 --seed $ASEED --ops $OPS 2>&1 | grep "new_best" | tail -1 | awk '{print $NF}' | sed 's/new_best=//')
        echo "    alns seed=$ASEED ops=$OPS $R"
      done
    done
  fi
done

echo ""
echo "=== Summary ==="
cat "$SUMMARY"
