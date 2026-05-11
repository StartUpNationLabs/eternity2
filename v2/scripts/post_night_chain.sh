#!/usr/bin/env bash
# After night_chain completes, run strain diagnostic.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/post_night_chain.log
echo "===== POST-NIGHT-CHAIN start: $(date) =====" | tee "$LOG"
echo "Waiting for night_chain.sh to finish..." | tee -a "$LOG"
while pgrep -lf 'night_chain' >/dev/null; do
    sleep 30
done
echo "night_chain done: $(date)" | tee -a "$LOG"
sleep 5

# Strain diagnostic.
echo "Running strain_diagnostic.sh..." | tee -a "$LOG"
bash scripts/strain_diagnostic.sh 2>&1 | tee -a "$LOG"

cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
git add -A output/pt_e2_*.json 2>/dev/null || true

echo "===== POST-NIGHT-CHAIN end: $(date) =====" | tee -a "$LOG"
