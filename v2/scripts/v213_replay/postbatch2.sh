#!/bin/zsh
# vol-213 corrected reruns (the hinted lane uses gates 120-168, NOT the
# default 154-186 spread — config error in postbatch.sh round 1):
#  1. census-1b: 50 generated frames, hinted tail2 gates 120-168
#  2. hinted tail2 mcb A/B with correct gates
#  3. miner A/B redesigned: budget-19 sentinel gates (deficit-bounded
#     prefix mining), {off, ledger} x {off, cairn}, hinted, 60 s x 8
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
HSCHED="120,127,134,141,148,155,162,168"

echo "=== census-1b: 50 frames, correct hinted gates ==="
$BIN --mode dfs --frame output/vol-213/frames_census50 \
  --hints --tail2 --tail2-cap 30000 --break-schedule "$HSCHED" \
  --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213

echo "=== hinted tail2 mcb A/B, correct gates ==="
for MCB in 1 2; do
  $BIN --mode dfs --frame $FRAME \
    --hints --tail2 --tail2-cap 30000 --break-schedule "$HSCHED" \
    --max-cell-breaks $MCB \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done

echo "=== miner A/B v2: budget-19 deficit-bounded prefix mining ==="
SENT="195,195,195,195,195,195,195,195,195,195,195,195,195,195,195,195,195,195,195"
for FLAGS in "" "--ledger" "--cairn" "--ledger --cairn"; do
  $BIN --mode dfs --frame $FRAME \
    --hints --exact-tail 0 --break-schedule "$SENT" ${=FLAGS} \
    --seeds 8 --budget-ms 60000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213
done
echo "=== postbatch2 done ==="
