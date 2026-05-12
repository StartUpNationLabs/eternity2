#!/usr/bin/env bash
# Wait for ga_large AND ga_cascade_453 to finish, then run ga_wide.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/post_all_run_gawide.log
echo "===== POST-ALL-RUN-GAWIDE start: $(date) =====" | tee "$LOG"
echo "Waiting for ga_large_run + ga_cascade_453..." | tee -a "$LOG"
while pgrep -lf 'ga_large_run\|ga_cascade_453' >/dev/null; do
    sleep 30
done
echo "both done: $(date)" | tee -a "$LOG"
sleep 5
bash scripts/ga_wide_run.sh 30 180 2>&1 | tee -a "$LOG"
echo "===== POST-ALL-RUN-GAWIDE end: $(date) =====" | tee -a "$LOG"
