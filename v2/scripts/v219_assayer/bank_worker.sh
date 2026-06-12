#!/bin/zsh
# Vol-219 stage-3 banking worker: one (stage-2 state, offset) per
# invocation. Pins rows 0-7, DFS BUDGET ms on 1 thread with
# --thread-id-offset OFF (different bucket shuffle = different walk;
# offset 0 reproduces the vol-217 deterministic walk), banks d>=192
# snapshots (rows 0-11 perfect).
# Usage: bank_worker.sh ROOT BUDGET_MS OFF STATE_JSON
set -e
ROOT=$1
BUDGET=$2
OFF=$3
F=$4
TAG=$(basename $F .json)
OD=$ROOT/s3_${TAG}_o${OFF}
[ -d $OD ] && exit 0
mkdir -p $OD
./target/release/vanilla_fast \
  --puzzle ../data/puzzles/size_16_official_eternity.csv \
  --pin-hints --init-board $F --init-rows 8 \
  --thread-id-offset $OFF \
  --snapshot-dir $OD --snapshot-on-visit --snapshot-min-depth 192 \
  --snapshot-interval-ms 300 --threads 1 --budget-ms $BUDGET \
  > $OD/run.log 2>&1 || echo "FAIL $TAG o$OFF" >> $ROOT/failures.log
MD=$(grep -o '"max_depth":[0-9]*' $OD/run.log | cut -d: -f2 | head -1)
ND=$(ls $OD/t*.json 2>/dev/null | wc -l | tr -d ' ')
echo "$TAG\t$OFF\t${MD:-NA}\t$ND" >> $ROOT/bank_summary.tsv
