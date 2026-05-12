#!/usr/bin/env bash
# After cascade finishes, run NE-RAND.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG=/tmp/post_cascade_ne_rand.log
echo "===== POST-CASCADE-NE-RAND start: $(date) =====" | tee "$LOG"
while pgrep -lf 'post_ga_cascade' >/dev/null; do sleep 30; done
echo "cascade done: $(date)" | tee -a "$LOG"
sleep 5
python3 scripts/random_fill_board.py --out /tmp/ne_rand_fill.json --seed 31 2>&1 | tee -a "$LOG"
./target/release/pt_e2 --pt-seconds 600 --skip-sa-compare --start-from /tmp/ne_rand_fill.json --seed 999 2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|^PT:|PT done|loaded board|new best)" || true
echo "===== POST-CASCADE-NE-RAND end: $(date) =====" | tee -a "$LOG"
