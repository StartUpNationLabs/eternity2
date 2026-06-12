#!/bin/zsh
# Vol-217 stage-3 penetration experiment (pre-registered:
# output/vol-217/stage2_gen_*/PREREG_stage3_penetration.txt).
# For each stratified stage-2 state: pin rows 0-7, DFS 60 s x 8
# threads, snapshots on-visit at depth>=192 (perfect rows 0-11).
set -e
cd "$(dirname "$0")/../.."
LIST=$1
ROOT=$2
mkdir -p $ROOT
BIN=./target/release/vanilla_fast
PUZ=../data/puzzles/size_16_official_eternity.csv

tail -n +2 $LIST | while IFS=$'\t' read F STRATUM FLOOR SOFT; do
  TAG=$(basename $F .json)
  OD=$ROOT/pen_${STRATUM}_$TAG
  mkdir -p $OD
  $BIN --puzzle $PUZ --pin-hints --init-board $F --init-rows 8 \
    --snapshot-dir $OD --snapshot-on-visit --snapshot-min-depth 192 \
    --snapshot-interval-ms 200 --threads 8 --budget-ms 60000 \
    > $OD/run.log 2>&1
  MD=$(grep -o '"max_depth":[0-9]*' $OD/run.log | cut -d: -f2)
  ND=$(ls $OD/*.json 2>/dev/null | wc -l | tr -d ' ')
  echo -e "$TAG\t$STRATUM\t$FLOOR\t$SOFT\t$MD\t$ND" | tee -a $ROOT/results.tsv
done
echo "=== penetration done: $ROOT ==="
