#!/usr/bin/env bash
# After ga_light finishes, run NE-RAND (random-start PT).
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/post_ga_run_ne_rand.log
echo "===== POST-GA-RUN-NE-RAND start: $(date) =====" | tee "$LOG"
echo "Waiting for ga_light_run.sh to finish..." | tee -a "$LOG"
while pgrep -lf 'ga_light_run' >/dev/null; do sleep 30; done
echo "ga_light done: $(date)" | tee -a "$LOG"
sleep 5

# NE-RAND: PT from random fill (CP basin diagnostic).
python3 scripts/random_fill_board.py --out /tmp/ne_rand_fill.json --seed 31 2>&1 | tee -a "$LOG"
./target/release/pt_e2 --pt-seconds 600 --skip-sa-compare --start-from /tmp/ne_rand_fill.json --seed 999 2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|^PT:|PT done|loaded board|new best)" || true
echo "===== POST-GA-RUN-NE-RAND end: $(date) =====" | tee -a "$LOG"
