#!/usr/bin/env bash
# Cascade specifically from the 453 board: cross 453 + each other parent.
# Tests whether the 453 basin has accessible neighbors at 454+.

set -uo pipefail
cd "$(dirname "$0")/.."

PT_S="${1:-120}"
LOG=/tmp/ga_cascade_453.log

echo "=== GA-CASCADE-453 start: $(date) ===" | tee "$LOG"

# Wait for GA-WIDE to finish.
echo "Waiting for ga_wide_run.sh to finish..." | tee -a "$LOG"
while pgrep -lf 'ga_wide_run' >/dev/null; do
    sleep 30
done
echo "ga_wide done: $(date)" | tee -a "$LOG"
sleep 5

A="output/HISTORIC_first_453_1778557672.json"
PARTNERS=(
    "output/HISTORIC_first_452_1778547973.json"
    "output/pt_e2_1778550597_451of480.json"
    "output/pt_e2_1778551437_451of480.json"
    "output/archive/frame_first_e2_1778532924_450of480.json"
    "output/ne1_stage1_new_450.json"
    "output/ne1_stage2_best_450of480.json"
    "output/pt_e2_1778535682_449of480.json"
    "output/archive/pt_e2_1778526208_449of480.json"
)

mkdir -p output/ga_cascade_453
BEST_SCORE=453
HITS_454=0

i=0
for B in "${PARTNERS[@]}"; do
    [[ ! -f "$B" ]] && continue
    i=$((i+1))
    # Try 3 random regions per partner.
    for r in 1 2 3; do
        KSIZE=4
        RX=$((1 + RANDOM % (16 - KSIZE - 1)))
        RY=$((1 + RANDOM % (16 - KSIZE - 1)))
        CHILD="output/ga_cascade_453/c_${i}_r${r}_at${RX}-${RY}.json"
        echo | tee -a "$LOG"
        echo "===== cascade-453 #$i.$r: B=$(basename $B), region ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

        python3 scripts/ga_crossover.py "$A" "$B" \
            --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
            --out "$CHILD" --seed $((i * 100 + r * 13)) 2>&1 | tee -a "$LOG"

        ./target/release/pt_e2 \
            --pt-seconds "$PT_S" \
            --skip-sa-compare \
            --start-from "$CHILD" \
            --seed $((i * 200 + r * 7 + 91)) \
            2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done)" || true

        LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
        if [[ -n "$LATEST" ]]; then
            FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo "0")
            echo "polished: $FINAL/480" | tee -a "$LOG"
            if [[ "$FINAL" -ge 454 ]]; then
                HITS_454=$((HITS_454 + 1))
                cp "$LATEST" "output/HISTORIC_${FINAL}_cascade453_${i}.${r}_$(date +%s).json"
                echo "*** 454+ HIT: $FINAL/480 ***" | tee -a "$LOG"
            fi
            if [[ "$FINAL" -gt "$BEST_SCORE" ]]; then
                BEST_SCORE=$FINAL
                echo "*** NEW NIGHT RECORD: $BEST_SCORE/480 ***" | tee -a "$LOG"
            fi
        fi
    done
done

echo | tee -a "$LOG"
echo "=== GA-CASCADE-453 done: $(date) ===" | tee -a "$LOG"
echo "best: $BEST_SCORE/480, 454+ hits: $HITS_454" | tee -a "$LOG"
