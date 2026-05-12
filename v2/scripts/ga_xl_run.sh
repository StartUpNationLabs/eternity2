#!/usr/bin/env bash
# GA-XL: long-running GA crossover with 453 in parent pool.
# 200 crossovers, 4×4 sweet-spot bias, 90s PT. ~5h total.

set -uo pipefail
cd "$(dirname "$0")/.."

N_CROSS="${1:-200}"
PT_S="${2:-90}"
LOG=/tmp/ga_xl.log

echo "=== GA-XL start: $(date) ===" | tee "$LOG"
echo "N=$N_CROSS, PT=$PT_S sec" | tee -a "$LOG"

PARENTS=(
    "output/HISTORIC_first_453_1778557672.json"               # 453 (best)
    "output/HISTORIC_first_452_1778547973.json"               # 452
    "output/pt_e2_1778550597_451of480.json"                   # 451
    "output/pt_e2_1778551437_451of480.json"                   # 451
    "output/archive/frame_first_e2_1778532924_450of480.json"
    "output/ne1_stage1_new_450.json"
    "output/ne1_stage2_best_450of480.json"
    "output/pt_e2_1778535682_449of480.json"
    "output/archive/pt_e2_1778526208_449of480.json"
)
PARENTS_AVAIL=()
for p in "${PARENTS[@]}"; do
    [[ -f "$p" ]] && PARENTS_AVAIL+=("$p")
done
NP=${#PARENTS_AVAIL[@]}
echo "$NP parents available" | tee -a "$LOG"

mkdir -p output/ga_xl
BEST_SCORE=453
HITS=0

for i in $(seq 1 "$N_CROSS"); do
    A_IDX=$((RANDOM % NP))
    B_IDX=$((RANDOM % NP))
    while [[ "$B_IDX" -eq "$A_IDX" ]]; do
        B_IDX=$((RANDOM % NP))
    done
    A="${PARENTS_AVAIL[$A_IDX]}"
    B="${PARENTS_AVAIL[$B_IDX]}"

    KSIZES=(3 4 4 4 4 4 5)
    KSIZE=${KSIZES[$((RANDOM % 7))]}
    RX=$((1 + RANDOM % (16 - KSIZE - 1)))
    RY=$((1 + RANDOM % (16 - KSIZE - 1)))

    CHILD="output/ga_xl/c_${i}_k${KSIZE}_at${RX}-${RY}.json"
    echo | tee -a "$LOG"
    echo "===== xl #$i: A=$(basename $A) B=$(basename $B) ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

    python3 scripts/ga_crossover.py "$A" "$B" \
        --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
        --out "$CHILD" --seed $((i * 9001)) 2>&1 | tee -a "$LOG"

    ./target/release/pt_e2 \
        --pt-seconds "$PT_S" \
        --skip-sa-compare \
        --start-from "$CHILD" \
        --seed $((i * 53 + 17)) \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done)" || true

    LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo "0")
        echo "polished: $FINAL/480" | tee -a "$LOG"
        if [[ "$FINAL" -ge 451 ]]; then
            HITS=$((HITS + 1))
            cp "$LATEST" "output/HISTORIC_${FINAL}_xl_${i}_$(date +%s).json"
        fi
        if [[ "$FINAL" -gt "$BEST_SCORE" ]]; then
            BEST_SCORE=$FINAL
            echo "*** NEW NIGHT RECORD: $BEST_SCORE/480 ***" | tee -a "$LOG"
        fi
    fi
done

echo | tee -a "$LOG"
echo "=== GA-XL done: $(date) ===" | tee -a "$LOG"
echo "best: $BEST_SCORE/480, 451+ hits: $HITS / $N_CROSS" | tee -a "$LOG"
