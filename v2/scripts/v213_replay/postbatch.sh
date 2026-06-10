#!/bin/zsh
# vol-213 post-batch (sequential, 8 cores):
#  1. census: 50 generated hint-compatible frames, vol-212 reliable
#     hinted recipe (tail2 trigger 168, breaks 8) x 8 seeds x 30 s
#     -> does ANY frame escape the 444-450 band?
#  2. mcb A/B rerun, properly configured: unhinted et14 lane
#     (breaks 12, gates 130-190 — the vol-212 450-453 plateau lane)
#  3. hinted tail2 lane A/B (the reliable 445-446 lane)
#  4. choke auto-gates with budget 18 (cross the 182 trigger?)
#  5. vol-214 opener: perfect-prefix miner wall A/B
#     {off, ledger, cairn, ledger+cairn} hinted budget-0, 8 x 60 s
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
UNH_SCHED="130,135,141,146,152,157,163,168,174,179,185,190"

echo "=== census 50 generated frames ==="
$BIN --mode dfs --frame output/vol-213/frames_census50 \
  --hints --tail2 --tail2-cap 30000 --breaks 8 \
  --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

echo "=== mcb A/B unhinted et14 lane ==="
for MCB in 1 2; do
  $BIN --mode dfs --frame $FRAME \
    --exact-tail 14 --et-cap 100000000 --break-schedule "$UNH_SCHED" \
    --max-cell-breaks $MCB \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done

echo "=== mcb A/B hinted tail2 lane ==="
for MCB in 1 2; do
  $BIN --mode dfs --frame $FRAME \
    --hints --tail2 --tail2-cap 30000 --breaks 8 \
    --max-cell-breaks $MCB \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done

echo "=== choke auto-gates budget 18, hinted et14 ==="
$BIN --mode dfs --frame $FRAME \
  --hints --exact-tail 14 --et-cap 100000000 \
  --schedule-from-choke output/vol-213/cloister2_dfs_20260610T185057/choke_strict460a.tsv,18,100 \
  --seeds 8 --budget-ms 60000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

echo "=== vol-214 opener: miner wall A/B ==="
for FLAGS in "" "--ledger" "--cairn" "--ledger --cairn"; do
  $BIN --mode dfs --frame $FRAME \
    --hints --exact-tail 0 ${=FLAGS} \
    --seeds 8 --budget-ms 60000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done
echo "=== postbatch done ==="
