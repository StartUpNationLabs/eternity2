#!/usr/bin/env bash
# GA-LARGE: scaled-up GA crossover with full parent pool including 452+451 boards.
#
# Population: ALL 451+ boards + all 449/450 boards.
# 60 crossovers, varied region sizes (3-5), varied positions.
# Each child polished 90s. Total ~100 min.
#
# Predicted: ~6-9 hits at 451+. Some may be in DIFFERENT basin
# from current 452-basin. Statistical chance of 453+.

set -uo pipefail
cd "$(dirname "$0")/.."

N_CROSS="${1:-60}"
PT_S="${2:-90}"
LOG=/tmp/ga_large.log

echo "=== GA-LARGE start: $(date) ===" | tee "$LOG"
echo "N crossovers: $N_CROSS, PT seconds per child: $PT_S" | tee -a "$LOG"

PARENTS=(
    "output/HISTORIC_first_452_1778547973.json"
    "output/pt_e2_1778550597_451of480.json"
    "output/pt_e2_1778551437_451of480.json"
    "output/archive/frame_first_e2_1778532924_450of480.json"
    "output/ne1_stage1_new_450.json"
    "output/ne1_stage2_best_450of480.json"
    "output/pt_e2_1778535682_449of480.json"
    "output/archive/pt_e2_1778526208_449of480.json"
)
PARENTS_AVAIL=()
for p in "${PARENTS[@]}"; do
    if [[ -f "$p" ]]; then
        PARENTS_AVAIL+=("$p")
        score=$(jq '.score.matched_edges' "$p" 2>/dev/null || echo "?")
        echo "  $p  ($score/480)" | tee -a "$LOG"
    fi
done
NP=${#PARENTS_AVAIL[@]}
echo "$NP parents available" | tee -a "$LOG"

mkdir -p output/ga_large
BEST_SCORE=452
BEST_BOARD="output/HISTORIC_first_452_1778547973.json"
HITS_451PLUS=0

for i in $(seq 1 "$N_CROSS"); do
    A_IDX=$((RANDOM % NP))
    B_IDX=$((RANDOM % NP))
    while [[ "$B_IDX" -eq "$A_IDX" ]]; do
        B_IDX=$((RANDOM % NP))
    done
    A="${PARENTS_AVAIL[$A_IDX]}"
    B="${PARENTS_AVAIL[$B_IDX]}"

    KSIZES=(3 4 4 4 4 5)
    KSIZE=${KSIZES[$((RANDOM % 6))]}
    RX=$((1 + RANDOM % (16 - KSIZE - 1)))
    RY=$((1 + RANDOM % (16 - KSIZE - 1)))

    CHILD="output/ga_large/child_${i}_k${KSIZE}_at${RX}-${RY}.json"
    echo | tee -a "$LOG"
    echo "===== large #$i: A=$(basename $A), B=$(basename $B), region ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

    python3 scripts/ga_crossover.py "$A" "$B" \
        --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
        --out "$CHILD" --seed $((i * 7919)) 2>&1 | tee -a "$LOG"

    ./target/release/pt_e2 \
        --pt-seconds "$PT_S" \
        --skip-sa-compare \
        --start-from "$CHILD" \
        --seed $((i * 31 + 13)) \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|Report:)" || true

    LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo "0")
        echo "polished: $FINAL/480 ($LATEST)" | tee -a "$LOG"
        if [[ "$FINAL" -ge 451 ]]; then
            HITS_451PLUS=$((HITS_451PLUS + 1))
            cp "$LATEST" "output/HISTORIC_${FINAL}_galarge_${i}_$(date +%s).json"
            echo "*** 451+ HIT #$HITS_451PLUS: $FINAL/480 ***" | tee -a "$LOG"
        fi
        if [[ "$FINAL" -gt "$BEST_SCORE" ]]; then
            BEST_SCORE=$FINAL
            BEST_BOARD=$LATEST
            echo "*** NEW NIGHT RECORD: $BEST_SCORE/480 ***" | tee -a "$LOG"
        fi
    fi
done

echo | tee -a "$LOG"
echo "=== GA-LARGE done: $(date) ===" | tee -a "$LOG"
echo "best: $BEST_SCORE/480 at $BEST_BOARD" | tee -a "$LOG"
echo "451+ hits: $HITS_451PLUS / $N_CROSS" | tee -a "$LOG"
