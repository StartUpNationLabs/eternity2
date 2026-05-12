#!/usr/bin/env bash
# After post_strain_chain finishes, run GA-light experiment.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG=/tmp/post_ga_chain.log
echo "===== POST-GA-CHAIN start: $(date) =====" | tee "$LOG"

echo "Waiting for post_strain_chain to finish..." | tee -a "$LOG"
while pgrep -lf 'post_strain_chain' >/dev/null; do
    sleep 30
done
echo "post_strain_chain done: $(date)" | tee -a "$LOG"
sleep 5

echo "Running ga_light_run.sh..." | tee -a "$LOG"
bash scripts/ga_light_run.sh 12 90 2>&1 | tee -a "$LOG"

cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
git add -A output/pt_e2_*.json 2>/dev/null || true

echo "===== POST-GA-CHAIN end: $(date) =====" | tee -a "$LOG"
