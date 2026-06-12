#!/bin/zsh
# Vol-218: full 10×10 measurement grid across 8 instances.
# Phase A: m2ladder (M2 exactness gate, controlled b*-graded family)
# Phase B: m23 (blind entries: saw bracket + bb + gap@b*)
# Phase C: m4  (instruments on the full bank)
# One process per instance (8 cores). Usage: full_grid.sh RUN_DIR
set -u
RUN=$1
BIN=./target/release/mini_lab
SEEDS=(101 102 103 104 105 106 107 108)

echo "[grid] phase A: m2ladder" >&2
for s in $SEEDS; do
  $BIN --mode m2ladder --seed $s --bb-budget-ms 600000 \
    > $RUN/m2ladder_$s.tsv 2> $RUN/m2ladder_$s.err &
done
wait
echo "[grid] phase A done $(date -u +%H:%M:%S)" >&2

echo "[grid] phase B: m23 (grid-n 20)" >&2
for s in $SEEDS; do
  $BIN --mode m23 --seed $s --entries $RUN/inst_$s/entries.jsonl \
    --grid-n 20 --bb-budget-ms 120000 \
    > $RUN/m23_$s.tsv 2> $RUN/m23_$s.err &
done
wait
echo "[grid] phase B done $(date -u +%H:%M:%S)" >&2

echo "[grid] phase C: m4 (full bank)" >&2
for s in $SEEDS; do
  $BIN --mode m4 --seed $s --entries $RUN/inst_$s/entries.jsonl \
    --node-cap 300000000 \
    > $RUN/m4_$s.tsv 2> $RUN/m4_$s.err &
done
wait
echo "[grid] ALL DONE $(date -u +%H:%M:%S)" >&2
