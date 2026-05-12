#!/usr/bin/env bash
# GA-WIDE: large-region crossover designed to ESCAPE the 452 basin.
#
# Hypothesis: 4×4 crossovers polish back to 452 (basin-reproductive).
# Larger regions (6-8) inject more diversity → lower 451+ rate but
# any hits that DO land in 451+ may be in NEW basins.
#
# Population: same as GA-LARGE (8 parents).
# 30 crossovers, region sizes ∈ {6, 7, 8}, longer PT (180s) to give
# the disrupted child time to settle.
# Total ~120 min.
#
# Predicted: 1-3 hits at 451+, possibly in DIFFERENT basins than the
# current 452.

set -uo pipefail
cd "$(dirname "$0")/.."

N_CROSS="${1:-30}"
PT_S="${2:-180}"
LOG=/tmp/ga_wide.log

echo "=== GA-WIDE start: $(date) ===" | tee "$LOG"
echo "N crossovers: $N_CROSS, PT seconds per child: $PT_S" | tee -a "$LOG"

PARENTS=(
    "output/HISTORIC_first_453_1778557672.json"               # 453 (NEW BEST)
    "output/HISTORIC_first_452_1778547973.json"               # 452
    "output/pt_e2_1778550597_451of480.json"                   # 451 (cascade #1)
    "output/pt_e2_1778551437_451of480.json"                   # 451 (cascade #8)
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

mkdir -p output/ga_wide
BEST_SCORE=453
HITS_451PLUS=0
NEW_BASIN_HITS=0

for i in $(seq 1 "$N_CROSS"); do
    A_IDX=$((RANDOM % NP))
    B_IDX=$((RANDOM % NP))
    while [[ "$B_IDX" -eq "$A_IDX" ]]; do
        B_IDX=$((RANDOM % NP))
    done
    A="${PARENTS_AVAIL[$A_IDX]}"
    B="${PARENTS_AVAIL[$B_IDX]}"

    KSIZES=(6 6 7 7 8)  # all wide
    KSIZE=${KSIZES[$((RANDOM % 5))]}
    RX=$((1 + RANDOM % (16 - KSIZE - 1)))
    RY=$((1 + RANDOM % (16 - KSIZE - 1)))

    CHILD="output/ga_wide/child_${i}_k${KSIZE}_at${RX}-${RY}.json"
    echo | tee -a "$LOG"
    echo "===== wide #$i: A=$(basename $A), B=$(basename $B), region ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

    python3 scripts/ga_crossover.py "$A" "$B" \
        --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
        --out "$CHILD" --seed $((i * 6571 + 1)) 2>&1 | tee -a "$LOG"

    ./target/release/pt_e2 \
        --pt-seconds "$PT_S" \
        --skip-sa-compare \
        --start-from "$CHILD" \
        --seed $((i * 41 + 23)) \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|Report:)" || true

    LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo "0")
        echo "polished: $FINAL/480" | tee -a "$LOG"
        if [[ "$FINAL" -ge 451 ]]; then
            HITS_451PLUS=$((HITS_451PLUS + 1))
            cp "$LATEST" "output/HISTORIC_${FINAL}_gawide_${i}_$(date +%s).json"
            echo "*** WIDE 451+ HIT #$HITS_451PLUS: $FINAL/480 ***" | tee -a "$LOG"

            # Compute overlap with current best (452 board) — % SAME positions.
            OVERLAP=$(python3 -c "
import json, re
W = 16
url1 = json.load(open('output/HISTORIC_first_453_1778557672.json'))['bucas_url']
url2 = json.load(open('$LATEST'))['bucas_url']
b1 = re.search(r'board_edges=([a-z]+)', url1).group(1)
b2 = re.search(r'board_edges=([a-z]+)', url2).group(1)
ov = sum(1 for i in range(len(b1)) if b1[i] == b2[i])
print(f'{100*ov/len(b1):.1f}')
" 2>/dev/null)
            echo "  basin overlap with 452: ${OVERLAP}%" | tee -a "$LOG"

            # Heuristic: if overlap < 50%, declare new basin.
            if (( $(echo "$OVERLAP < 50" | bc -l 2>/dev/null) )); then
                NEW_BASIN_HITS=$((NEW_BASIN_HITS + 1))
                echo "  *** NEW BASIN #$NEW_BASIN_HITS ***" | tee -a "$LOG"
            fi
        fi
        if [[ "$FINAL" -gt "$BEST_SCORE" ]]; then
            BEST_SCORE=$FINAL
            echo "*** NEW NIGHT RECORD: $BEST_SCORE/480 ***" | tee -a "$LOG"
        fi
    fi
done

echo | tee -a "$LOG"
echo "=== GA-WIDE done: $(date) ===" | tee -a "$LOG"
echo "best: $BEST_SCORE/480" | tee -a "$LOG"
echo "451+ hits: $HITS_451PLUS / $N_CROSS" | tee -a "$LOG"
echo "new-basin hits: $NEW_BASIN_HITS" | tee -a "$LOG"
