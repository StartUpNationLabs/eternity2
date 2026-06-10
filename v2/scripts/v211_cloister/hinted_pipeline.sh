#!/bin/bash
# vol-211 hinted record pipeline: DFS-long + hybrid(rim) + control.
set -u
cd "$(dirname "$0")/../.." || exit 1
TS=$(date +%Y%m%dT%H%M%S)
LOG=output/vol-211/hinted_pipeline_${TS}.log
{
echo "=== CLOISTER hinted pipeline $TS ==="
echo "--- H1: hinted DFS 300s x 8, breaks 7, et14"
./target/release/cloister --mode dfs --seeds 8 --budget-ms 300000 \
  --breaks 7 --exact-tail 14 --restart-ms 3000 --hints
echo "--- H2: hinted hybrid lambda=1.0, 300s x 8 (dfs 60s), breaks 7, et14"
./target/release/cloister --mode hybrid --seeds 8 --budget-ms 300000 --dfs-ms 60000 \
  --breaks 7 --exact-tail 14 --restart-ms 3000 --hints --rim-lambda 1.0
echo "--- H3: hinted hybrid lambda=0 (control), 300s x 8"
./target/release/cloister --mode hybrid --seeds 8 --budget-ms 300000 --dfs-ms 60000 \
  --breaks 7 --exact-tail 14 --restart-ms 3000 --hints
echo "=== hinted pipeline done ==="
} > "$LOG" 2>&1
echo "$LOG"
