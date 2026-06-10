#!/bin/zsh
# vol-213 REPLAY mode (prior-over-cost) — witness A then B, sequential
# (8 cores max total). Control = same config poc=false (vol-213 day 1:
# A 455/456/457 @60s saturated; B 456x8 @600s).
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
BUDGET=${1:-300000}
SEEDS=${2:-8}

$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460a.json \
  --hints --exact-tail 14 \
  --prior-boards output/vol-213/prior_witness \
  --schedule-from-board output/vol-213/prior_witness/groups_219671623_460.json \
  --prior-over-cost \
  --seeds $SEEDS --budget-ms $BUDGET --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460b.json \
  --hints --exact-tail 14 \
  --prior-boards output/vol-213/prior_witness_b \
  --schedule-from-board output/vol-213/prior_witness_b/groups_219328931_460.json \
  --prior-over-cost \
  --seeds $SEEDS --budget-ms $BUDGET --restart-ms 5000 --threads 8 \
  --out-root output/vol-213
