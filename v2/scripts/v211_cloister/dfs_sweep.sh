#!/bin/bash
# vol-211 CLOISTER DFS config sweep: schedule x breaks x exact-tail.
# 4 configs x 8 seeds x 300s = ~20 min total (configs sequential, seeds parallel).
set -u
cd "$(dirname "$0")/../.." || exit 1
TS=$(date +%Y%m%dT%H%M%S)
LOG=output/vol-211/dfs_sweep_${TS}.log
{
echo "=== CLOISTER DFS sweep $TS ==="
echo "--- A: breaks 5, default sched, et8, restart 3s"
./target/release/cloister --mode dfs --seeds 8 --budget-ms 300000 \
  --breaks 5 --exact-tail 8 --restart-ms 3000
echo "--- B: breaks 5, LATE sched, et8, restart 3s"
./target/release/cloister --mode dfs --seeds 8 --budget-ms 300000 \
  --break-schedule "165,172,178,184,189" --exact-tail 8 --restart-ms 3000
echo "--- C: breaks 8, spread sched, et8, restart 3s"
./target/release/cloister --mode dfs --seeds 8 --budget-ms 300000 \
  --break-schedule "150,156,162,168,174,180,185,189" --exact-tail 8 --restart-ms 3000
echo "--- D: breaks 5, default sched, et11, restart 5s"
./target/release/cloister --mode dfs --seeds 8 --budget-ms 300000 \
  --breaks 5 --exact-tail 11 --restart-ms 5000
echo "=== sweep done ==="
} > "$LOG" 2>&1
echo "$LOG"
