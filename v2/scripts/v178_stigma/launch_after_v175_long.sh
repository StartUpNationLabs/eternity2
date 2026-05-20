#!/usr/bin/env bash
# Wait for V175-LONG-LIFT to finish (i.e. no alns_only matching the
# long_lift pattern), then launch V178 STIGMA sweep.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

LOG=/tmp/v178_chain.log
echo "[v178-chain] start $(date)" > "$LOG"

# Wait for V175-LONG-LIFT alns_only jobs (1800000ms budget) to finish.
echo "[v178-chain] waiting for V175-LONG-LIFT to finish..." | tee -a "$LOG"
while true; do
  n=$(ps aux | grep "[a]lns_only.*1800000" | wc -l | tr -d ' ')
  if [ "$n" -le 0 ]; then
    break
  fi
  sleep 60
done
echo "[v178-chain] V175-LONG-LIFT done at $(date), launching V178" | tee -a "$LOG"

# Launch V178 STIGMA sweep.
bash scripts/v178_stigma/run.sh >> "$LOG" 2>&1
echo "[v178-chain] V178 STIGMA done at $(date)" | tee -a "$LOG"
