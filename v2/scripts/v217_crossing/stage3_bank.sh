#!/bin/zsh
# Vol-217 stage-3 banking at scale: for each floor-0 stage-2 state
# (ranked by soft), pin rows 0-7 and DFS 30 s on 1 thread, banking
# perfect rows-0-11 states (d>=192 snapshots). 8 states run in
# parallel (8 x 1 thread = 8 cores).
# Usage: stage3_bank.sh LIST OUT_ROOT [BUDGET_MS]
set -e
cd "$(dirname "$0")/../.."
LIST=$1
ROOT=$2
BUDGET=${3:-30000}
mkdir -p $ROOT
BIN=./target/release/vanilla_fast
PUZ=../data/puzzles/size_16_official_eternity.csv

run_one() {
  local F=$1
  local TAG=$(basename $F .json)
  local OD=$ROOT/s3_$TAG
  [ -d $OD ] && return 0
  mkdir -p $OD
  $BIN --puzzle $PUZ --pin-hints --init-board $F --init-rows 8 \
    --snapshot-dir $OD --snapshot-on-visit --snapshot-min-depth 192 \
    --snapshot-interval-ms 300 --threads 1 --budget-ms $BUDGET \
    > $OD/run.log 2>&1
  local MD=$(grep -o '"max_depth":[0-9]*' $OD/run.log | cut -d: -f2)
  local ND=$(ls $OD/t*.json 2>/dev/null | wc -l | tr -d ' ')
  echo -e "$TAG\t$MD\t$ND" >> $ROOT/bank_summary.tsv
}

N_PAR=8
i=0
while read F; do
  run_one $F &
  i=$((i+1))
  if (( i % N_PAR == 0 )); then wait; fi
done < $LIST
wait
echo "=== stage3 banking done: $ROOT ==="
awk -F'\t' '{md[$1]=$2; tot+=$3} END {print "total d192+ states:", tot}' \
  $ROOT/bank_summary.tsv
