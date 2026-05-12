#!/usr/bin/env bash
# After GA-light finishes, cascade from the new 452/480 board:
# - Long PT polish on the 452 itself (try to push to 453+).
# - Multiple crossovers using the 452 as one parent.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG=/tmp/post_ga_cascade.log
echo "===== POST-GA-CASCADE start: $(date) =====" | tee "$LOG"

# Wait for ga_light_run to finish.
echo "Waiting for ga_light_run.sh to finish..." | tee -a "$LOG"
while pgrep -lf 'ga_light_run' >/dev/null; do
    sleep 30
done
echo "ga_light done: $(date)" | tee -a "$LOG"
sleep 5

# Find the BEST 452+ board produced.
BEST_BOARD=""
BEST_SCORE=0
for f in output/HISTORIC_first_452_*.json output/pt_e2_*45[2-9]of480.json output/pt_e2_*4[6-9]?of480.json; do
    if [[ -f "$f" ]]; then
        s=$(jq '.score.matched_edges' "$f" 2>/dev/null)
        if [[ -n "$s" && "$s" -gt "$BEST_SCORE" ]]; then
            BEST_SCORE=$s
            BEST_BOARD=$f
        fi
    fi
done
echo "Best ≥452 board: $BEST_BOARD (score=$BEST_SCORE)" | tee -a "$LOG"

if [[ -z "$BEST_BOARD" ]]; then
    echo "ERROR: no ≥452 board found" | tee -a "$LOG"
    exit 1
fi

# Phase A: long PT polish from the best board (try to push to 453+).
echo | tee -a "$LOG"
echo "===== Phase A: 30-min PT polish from $BEST_BOARD =====" | tee -a "$LOG"
./target/release/pt_e2 --pt-seconds 1800 --skip-sa-compare --start-from "$BEST_BOARD" --seed 12345 \
    2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|^PT:|PT done|new best)" || true

# Phase B: 8 crossovers using the 452 board × random other parents, 120s PT each.
echo | tee -a "$LOG"
echo "===== Phase B: 8 cascade crossovers using 452 as parent =====" | tee -a "$LOG"
PARENTS=(
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

mkdir -p output/ga_cascade
BEST_CASCADE_SCORE=$BEST_SCORE
BEST_CASCADE_BOARD=$BEST_BOARD
for i in $(seq 1 8); do
    OTHER=${PARENTS_AVAIL[$((RANDOM % ${#PARENTS_AVAIL[@]}))]}
    KSIZES=(3 4 5)
    KSIZE=${KSIZES[$((RANDOM % 3))]}
    RX=$((1 + RANDOM % (16 - KSIZE - 1)))
    RY=$((1 + RANDOM % (16 - KSIZE - 1)))

    CHILD="output/ga_cascade/cas_${i}_k${KSIZE}_at${RX}-${RY}.json"
    echo | tee -a "$LOG"
    echo "===== cascade #$i: A=$BEST_CASCADE_BOARD, B=$(basename $OTHER), region ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

    python3 scripts/ga_crossover.py "$BEST_CASCADE_BOARD" "$OTHER" \
        --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
        --out "$CHILD" --seed $((i * 1009)) 2>&1 | tee -a "$LOG"

    ./target/release/pt_e2 --pt-seconds 120 --skip-sa-compare --start-from "$CHILD" --seed $((i * 23 + 5)) \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|Report:)" || true

    LATEST=$(ls -t output/pt_e2_*.json | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST")
        echo "polished: $FINAL/480" | tee -a "$LOG"
        if [[ "$FINAL" -gt "$BEST_CASCADE_SCORE" ]]; then
            BEST_CASCADE_SCORE=$FINAL
            BEST_CASCADE_BOARD=$LATEST
            cp "$LATEST" "output/HISTORIC_${FINAL}_$(date +%s).json"
            echo "*** NEW CASCADE BEST: $FINAL ***" | tee -a "$LOG"
        fi
    fi
done

echo | tee -a "$LOG"
echo "===== POST-GA-CASCADE done: $(date) =====" | tee -a "$LOG"
echo "best score: $BEST_CASCADE_SCORE/480, board: $BEST_CASCADE_BOARD" | tee -a "$LOG"

cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
git add -A output/HISTORIC_*.json 2>/dev/null || true
