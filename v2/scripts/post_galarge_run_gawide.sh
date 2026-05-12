#!/usr/bin/env bash
# After GA-LARGE finishes, run GA-WIDE.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG=/tmp/post_galarge_run_gawide.log
echo "===== POST-GALARGE-RUN-GAWIDE start: $(date) =====" | tee "$LOG"

while pgrep -lf 'ga_large_run' >/dev/null; do
    sleep 30
done
echo "ga_large done: $(date)" | tee -a "$LOG"
sleep 5

bash scripts/ga_wide_run.sh 30 180 2>&1 | tee -a "$LOG"

echo "===== POST-GALARGE-RUN-GAWIDE end: $(date) =====" | tee -a "$LOG"
