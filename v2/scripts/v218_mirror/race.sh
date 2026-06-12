#!/bin/zsh
# Vol-218 MIRROR race: per-top vanilla_fast perfect descent (rows 5-15)
# at matched compute. Usage: race.sh TOPS_DIR OUT_DIR [BUDGET_MS] [WORKERS]
# Output: OUT_DIR/results.tsv (arm, top, max_depth, matched_total)
set -u
TOPS_DIR=$1
OUT_DIR=$2
BUDGET_MS=${3:-60000}
WORKERS=${4:-7}
BIN=./target/release/vanilla_fast
PUZZLE=../data/puzzles/size_16_official_eternity.csv
mkdir -p "$OUT_DIR/logs"

run_one() {
  local top=$1
  local arm=$(basename $(dirname $top))
  local name=$(basename $top .json)
  local log="$OUT_DIR/logs/${arm}_${name}.log"
  if [[ -s "$log" ]] && grep -q "best-partial" "$log"; then return; fi
  $BIN --puzzle "$PUZZLE" --pin-hints --init-board "$top" --init-rows 5 \
       --threads 1 --budget-ms "$BUDGET_MS" >"$log" 2>&1
}

export -f run_one 2>/dev/null || true
export OUT_DIR BUDGET_MS BIN PUZZLE

# zsh-compatible job pool
typeset -a pids
pids=()
for top in "$TOPS_DIR"/*/top_*.json; do
  run_one "$top" &
  pids+=($!)
  while (( $(jobs -r | wc -l) >= WORKERS )); do sleep 1; done
done
wait

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
