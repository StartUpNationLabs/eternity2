#!/usr/bin/env bash
# Saturate the 454 board: same border pinned, 5 seeds × 300s each.
# If the same border supports 455+, we'll see it here.

set -uo pipefail
cd "$(dirname "$0")/.."

START="output/HISTORIC_first_454_1778567792.json"
LOG=/tmp/saturate_454.log
echo "=== saturate_454 start: $(date) ===" | tee "$LOG"

BEST=454
for i in 1 2 3 4 5; do
    SEED=$((i * 9001 + 17))
    echo "" | tee -a "$LOG"
    echo "===== seed $SEED (run $i/5) =====" | tee -a "$LOG"
    ./target/release/pt_e2 \
        --pt-seconds 300 \
        --skip-sa-compare \
        --start-from "$START" \
        --pin-perimeter \
        --seed "$SEED" \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|round.*global_best=45[5-9])" || true
    LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo 0)
        echo "run $i seed $SEED: best=$FINAL/480" | tee -a "$LOG"
        if [[ "$FINAL" -gt "$BEST" ]]; then
            BEST=$FINAL
            cp "$LATEST" "output/HISTORIC_${FINAL}_sat454_run${i}_$(date +%s).json"
            echo "*** NEW RECORD: $FINAL/480 ***" | tee -a "$LOG"
        fi
    fi
done
echo "" | tee -a "$LOG"
echo "=== saturate_454 done: $(date) best=$BEST ===" | tee -a "$LOG"
