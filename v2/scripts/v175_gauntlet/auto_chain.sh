#!/usr/bin/env bash
# Wait for V175 to fully finish, then chain V175-LONG-LIFT.
#
# V172 CHIASMUS may take a long time (112 hybrids × 5 min / 8-way = 70 min).
# V175-LONG-LIFT is 8 × 30min = 30 min wallclock.
#
# Strategy: launch V175-LONG-LIFT first (30 min), then V172.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

LOG=/tmp/v175_chain.log
echo "[chain] start $(date)" > "$LOG"

# Wait for V175 sweep to drop to 0 alns_only processes.
echo "[chain] waiting for V175 stage 2 to finish..." | tee -a "$LOG"
while true; do
  n=$(ps aux | grep "[a]lns_only" | grep -v "long_lift\|v172" | wc -l | tr -d ' ')
  if [ "$n" -le 0 ]; then
    break
  fi
  sleep 30
done
echo "[chain] V175 stage 2 done at $(date)" | tee -a "$LOG"

# Launch V175-LONG-LIFT (30min × top-8).
echo "[chain] launching V175-LONG-LIFT at $(date)" | tee -a "$LOG"
bash scripts/v175_gauntlet/run_long_lift.sh >> "$LOG" 2>&1
echo "[chain] V175-LONG-LIFT done at $(date)" | tee -a "$LOG"

# V178 STIGMA sweep (higher EV than V172 — fresh pheromone-biased
# basins vs remixing existing ones).
echo "[chain] launching V178 STIGMA at $(date)" | tee -a "$LOG"
bash scripts/v178_stigma/run.sh >> "$LOG" 2>&1
echo "[chain] V178 STIGMA done at $(date)" | tee -a "$LOG"

# Then V172 CHIASMUS on combined V175 + V178 outputs.
echo "[chain] launching V172 CHIASMUS at $(date)" | tee -a "$LOG"
bash scripts/v172_chiasmus/run_clean.sh >> "$LOG" 2>&1
echo "[chain] V172 done at $(date)" | tee -a "$LOG"

echo "[chain] all done $(date)" | tee -a "$LOG"
