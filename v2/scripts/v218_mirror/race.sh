#!/bin/zsh
# Vol-218 MIRROR race: per-top vanilla_fast perfect descent (rows 5-15)
# at matched compute. Usage: race.sh TOPS_DIR OUT_DIR [BUDGET_MS] [WORKERS]
# Output: OUT_DIR/results.tsv (arm, top, max_depth, matched_total)
# Throttle via xargs -P (zsh $(jobs) is subshell-blind — the 20260612
# pilot ran 280-way oversubscribed because of it).
set -u
TOPS_DIR=$1
OUT_DIR=$2
BUDGET_MS=${3:-60000}
WORKERS=${4:-7}
export OUT_DIR BUDGET_MS
export BIN=./target/release/vanilla_fast
export PUZZLE=../data/puzzles/size_16_official_eternity.csv
mkdir -p "$OUT_DIR/logs"

ls "$TOPS_DIR"/*/top_*.json | xargs -P "$WORKERS" -n 1 zsh scripts/v218_mirror/race_one.sh

echo "arm\ttop\tmax_depth\tmatched_total" > "$OUT_DIR/results.tsv"
for log in "$OUT_DIR"/logs/*.log; do
  base=$(basename "$log" .log)
  arm=${base%%_top_*}
  top=top_${base#*_top_}
  line=$(grep "best-partial" "$log" | tail -1)
  depth=$(echo "$line" | sed -n 's/.*depth=\([0-9]*\).*/\1/p')
  total=$(echo "$line" | sed -n 's/.*matched_total=\([0-9]*\)\/480.*/\1/p')
  echo "$arm\t$top\t${depth:--1}\t${total:--1}" >> "$OUT_DIR/results.tsv"
done
echo "[race] done: $(wc -l < "$OUT_DIR/results.tsv") rows" >&2
