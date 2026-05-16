#!/usr/bin/env bash
# Vol-118 T3 — corner perm sweep through bound-ascent + Hungarian + ALNS
#
# For each of 24 corner perm partials in output/vol-60/corner_partials/,
# run the full pipeline and record the final ALNS score.
#
# Output: output/vol-118/corner_sweep/${perm_name}.json (final board)
# Summary: output/vol-118/corner_sweep/_summary.csv

set -e

OUT_DIR="output/vol-118/corner_sweep_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
SUMMARY="$OUT_DIR/_summary.csv"
echo "perm,bound_ascent,hungarian,alns_60s,alns_path" > "$SUMMARY"

for perm in output/vol-60/corner_partials/*.json; do
  name=$(basename "$perm" .json)
  echo "=== $name ===" | tee -a "$OUT_DIR/_log.txt"

  ba_out="$OUT_DIR/${name}_bound.json"
  ./target/release/edge_bound_ascent --board "$perm" --iters 500 --seed 42 \
    --acceptance accept >> "$OUT_DIR/_log.txt" 2>&1 || true
  # bound_ascent writes to output/v21_bound_ascent_b*.json — find latest
  ba_latest=$(ls -t output/v21_bound_ascent_b*.json 2>/dev/null | head -1)
  if [ -z "$ba_latest" ]; then echo "  bound_ascent failed"; continue; fi
  cp "$ba_latest" "$ba_out"

  tm_out="$OUT_DIR/${name}_hungarian.json"
  ./target/release/edge_target_match --board "$ba_out" >> "$OUT_DIR/_log.txt" 2>&1 || true
  tm_latest=$(ls -t output/v21_target_match_*.json 2>/dev/null | head -1)
  if [ -z "$tm_latest" ]; then echo "  hungarian failed"; continue; fi
  cp "$tm_latest" "$tm_out"

  hungarian_score=$(./target/release/rescore_board "$tm_out" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  alns_out="$OUT_DIR/${name}_alns.json"
  ./target/release/alns_only --cp-board "$tm_out" --alns-budget-ms 60000 \
    --seed 42 --ops basic >> "$OUT_DIR/_log.txt" 2>&1 || true
  # alns saves to output/v17_alns_only/... — find latest
  alns_latest=$(ls -t output/v17_alns_only/*.json 2>/dev/null | head -1)
  if [ -z "$alns_latest" ]; then echo "  alns failed"; continue; fi
  cp "$alns_latest" "$alns_out"
  alns_score=$(./target/release/rescore_board "$alns_out" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  ba_bound=$(./target/release/rescore_board "$ba_out" 2>&1 | tail -1 | awk -F'\t' '{print $4}')

  echo "$name,$ba_bound,$hungarian_score,$alns_score,$alns_out" >> "$SUMMARY"
  echo "  bound=$ba_bound  hungarian=$hungarian_score  alns=$alns_score"
done

echo ""
echo "=== Summary ==="
cat "$SUMMARY"
