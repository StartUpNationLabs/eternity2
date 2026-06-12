#!/bin/zsh
# One MIRROR race leg. Env: OUT_DIR, BUDGET_MS, BIN, PUZZLE. Arg: top json.
set -u
top=$1
arm=$(basename $(dirname $top))
name=$(basename $top .json)
log="$OUT_DIR/logs/${arm}_${name}.log"
if [[ -s "$log" ]] && grep -q "best-partial" "$log"; then exit 0; fi
$BIN --puzzle "$PUZZLE" --pin-hints --init-board "$top" --init-rows 5 \
     --threads 1 --budget-ms "$BUDGET_MS" >"$log" 2>&1
