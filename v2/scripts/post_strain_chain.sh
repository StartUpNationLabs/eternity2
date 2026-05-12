#!/usr/bin/env bash
# After post_night_chain finishes, run random-PT-start diagnostic.
# Tests whether CP basin bias is what pins PT at 449.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG=/tmp/post_strain_chain.log
echo "===== POST-STRAIN-CHAIN start: $(date) =====" | tee "$LOG"

# Wait for post_night_chain to finish.
echo "Waiting for post_night_chain to finish..." | tee -a "$LOG"
while pgrep -lf 'post_night_chain' >/dev/null; do
    sleep 30
done
echo "post_night_chain done: $(date)" | tee -a "$LOG"
sleep 5

# Generate a fresh random board (different seed than first one).
python3 scripts/random_fill_board.py --out /tmp/random_fill_for_pt.json --seed 23 2>&1 | tee -a "$LOG"

# Run PT from this random board for 600s.
echo "Running PT from random fill..." | tee -a "$LOG"
./target/release/pt_e2 \
    --pt-seconds 600 \
    --skip-sa-compare \
    --start-from /tmp/random_fill_for_pt.json \
    --seed 3806637746 \
    2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|^PT:|PT done|^loaded board|new best)" || true

cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
git add -A output/pt_e2_*.json 2>/dev/null || true

echo "===== POST-STRAIN-CHAIN end: $(date) =====" | tee -a "$LOG"
