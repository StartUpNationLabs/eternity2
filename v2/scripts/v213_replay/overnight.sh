#!/bin/zsh
# vol-213 evening batch (sequential, 8 cores max):
#  1. perturb wide window [60:140) both witnesses (900 s x 8)
#  2. unguided mcb2 A/B on strict460a (300 s x 8, hinted, et14+et-cap)
#  3. framegen: 300 chains + 300 no-chains; 6 s hinted probe of both
#     (chain-constraint precision); 30 s x 8 census on compatible frames
#  4. choke-map A/B: hand-gates probe -> choke TSV -> auto-gates run
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FG=./target/release/framegen
TS=$(date -u +%Y%m%dT%H%M%S)

echo "=== 1. perturb wide [60:140) ==="
scripts/v213_replay/run_perturb.sh 900000 8 60 140

echo "=== 2. unguided mcb2 A/B (control then mcb2) ==="
for MCB in 1 2; do
  $BIN --mode dfs \
    --frame output/vol-212/frames_best/strict460a.json \
    --hints --exact-tail 14 --et-cap 100000000 \
    --breaks 14 --max-cell-breaks $MCB \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done

echo "=== 3. framegen + probe + census ==="
$FG --count 300 --seed0 1 --out-root output/vol-213
$FG --count 300 --seed0 100001 --no-chains --out-root output/vol-213
CH=$(ls -td output/vol-213/framegen_chains_* | head -1)
NC=$(ls -td output/vol-213/framegen_nochains_* | head -1)
# 6 s hinted probe: hint-compat = completes or reaches depth >= 20
for DIR in $CH $NC; do
  $BIN --mode dfs --frame $DIR \
    --hints --exact-tail 14 --et-cap 100000000 --breaks 14 \
    --seeds 1 --budget-ms 6000 --restart-ms 3000 --threads 8 \
    --out-root output/vol-213
done

echo "=== 4. choke A/B (unguided hinted, hand vs auto gates) ==="
$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460a.json \
  --hints --exact-tail 14 --et-cap 100000000 --breaks 14 \
  --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213
PROBE=$(ls -td output/vol-213/cloister2_dfs_* | head -1)
$BIN --mode dfs \
  --frame output/vol-212/frames_best/strict460a.json \
  --hints --exact-tail 14 --et-cap 100000000 \
  --schedule-from-choke $PROBE/choke_strict460a.tsv,14,100 \
  --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

echo "=== batch done ==="
