#!/bin/zsh
# Round-2 probes after the 300s curves: recipe variants on strict460a.
# Each: 30s x 8 seeds, hinted. Run sequentially (8 threads each).
set -e
BIN=./target/release/cloister2
F=output/vol-212/frames_control/strict460a.json
G="120,127,134,141,148,155,162"     # gates < trigger 168 (8th gate at 168 was unusable)
run() { echo "=== $1 ==="; shift; $BIN --mode dfs --frame $F --seeds 8 --budget-ms 30000 --hints --threads 8 --out-root output/vol-212 "$@" 2>&1 | tail -2 }
run "tail2 cap100k"  --break-schedule $G --tail2 --tail2-cap 100000
run "tail2 cap300k"  --break-schedule $G --tail2 --tail2-cap 300000
run "tail2 boustro"  --break-schedule $G --tail2 --scan boustro
run "tail2 lds3"     --break-schedule $G --tail2 --max-disc 3
run "tail2 lds8"     --break-schedule $G --tail2 --max-disc 8
run "tail2 breaks10" --break-schedule "115,121,127,133,139,145,151,157,162,167" --tail2
run "tail2 breaks6"  --break-schedule "125,133,141,149,157,165" --tail2
