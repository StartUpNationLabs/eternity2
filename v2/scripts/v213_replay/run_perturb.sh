#!/bin/zsh
# vol-213 deviate-then-replay (461 hunt): per epoch, one forced deviation
# at a sampled depth in [LO,HI), full witness-guided continuation
# (priors + replay + mcb2 + et14 @ 100M cap). Base = exact 460 replay.
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
BUDGET=${1:-900000}
SEEDS=${2:-8}
LO=${3:-140}
HI=${4:-182}

$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460a.json \
  --hints --exact-tail 14 --et-cap 100000000 \
  --prior-boards output/vol-213/prior_witness \
  --schedule-from-board output/vol-213/prior_witness/groups_219671623_460.json \
  --prior-over-cost --max-cell-breaks 2 --replay-perturb $LO:$HI \
  --seeds $SEEDS --budget-ms $BUDGET --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460b.json \
  --hints --exact-tail 14 --et-cap 100000000 \
  --prior-boards output/vol-213/prior_witness_b \
  --schedule-from-board output/vol-213/prior_witness_b/groups_219328931_460.json \
  --prior-over-cost --max-cell-breaks 2 --replay-perturb $LO:$HI \
  --seeds $SEEDS --budget-ms $BUDGET --restart-ms 5000 --threads 8 \
  --out-root output/vol-213
