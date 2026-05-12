#!/usr/bin/env bash
# GA-light: simple multi-pair crossover + short PT polish.
#
# Take all 450/449 boards available, do N random crossovers
# (different region offsets), polish each child for SHORT_PT seconds,
# keep the best result. If any reach 451+, we have a real
# breakthrough.
#
# Usage:
#   scripts/ga_light_run.sh [N_CROSSOVERS] [SHORT_PT_SECONDS]
# Default: 12 crossovers × 90s PT each = ~18 min total.

set -uo pipefail
cd "$(dirname "$0")/.."

N_CROSS="${1:-12}"
PT_S="${2:-90}"
LOG=/tmp/ga_light.log

echo "=== GA-LIGHT start: $(date) ===" | tee "$LOG"
echo "N crossovers: $N_CROSS, PT seconds per child: $PT_S" | tee -a "$LOG"

# Inventory of 449/450 parent boards.
PARENTS=(
    "output/archive/frame_first_e2_1778532924_450of480.json"      # vol-4 450
    "output/ne1_stage1_new_450.json"                              # NE1 stage-1 450
    "output/ne1_stage2_best_450of480.json"                        # NE1 stage-2 450/6/6
    "output/pt_e2_1778535682_449of480.json"                       # NE2 K=10 449/fmm=0
    "output/archive/pt_e2_1778526208_449of480.json"               # canonical 449 basin B
)

# Filter to existing files.
PARENTS_AVAIL=()
for p in "${PARENTS[@]}"; do
    if [[ -f "$p" ]]; then
        PARENTS_AVAIL+=("$p")
    fi
done
echo "Available parents: ${#PARENTS_AVAIL[@]}" | tee -a "$LOG"
for p in "${PARENTS_AVAIL[@]}"; do
    score=$(jq '.score.matched_edges' "$p" 2>/dev/null || echo "?")
    echo "  $p  score=$score" | tee -a "$LOG"
done

if [[ ${#PARENTS_AVAIL[@]} -lt 2 ]]; then
    echo "ERROR: need at least 2 parents" | tee -a "$LOG"
    exit 1
fi

mkdir -p output/ga_light
BEST_SCORE=0
BEST_CHILD=""

for i in $(seq 1 "$N_CROSS"); do
    # Pick two distinct random parents.
    A_IDX=$((RANDOM % ${#PARENTS_AVAIL[@]}))
    B_IDX=$((RANDOM % ${#PARENTS_AVAIL[@]}))
    while [[ "$B_IDX" -eq "$A_IDX" ]]; do
        B_IDX=$((RANDOM % ${#PARENTS_AVAIL[@]}))
    done
    A="${PARENTS_AVAIL[$A_IDX]}"
    B="${PARENTS_AVAIL[$B_IDX]}"

    # Random region.
    KSIZES=(4 5 6)
    KSIZE=${KSIZES[$((RANDOM % 3))]}
    RX=$((1 + RANDOM % (16 - KSIZE - 1)))
    RY=$((1 + RANDOM % (16 - KSIZE - 1)))

    CHILD="output/ga_light/child_${i}_k${KSIZE}_at${RX}-${RY}.json"
    POLISHED="output/ga_light/child_${i}_polished.json"

    echo | tee -a "$LOG"
    echo "===== crossover #$i: A=$(basename $A), B=$(basename $B), region ($RX,$RY)+${KSIZE} =====" | tee -a "$LOG"

    # Crossover.
    python3 scripts/ga_crossover.py "$A" "$B" \
        --region-x "$RX" --region-y "$RY" --region-k "$KSIZE" \
        --out "$CHILD" --seed $((i * 997)) 2>&1 | tee -a "$LOG"

    CHILD_SCORE=$(jq '.score.matched_edges' "$CHILD" 2>/dev/null || echo "?")
    echo "child raw score: $CHILD_SCORE/480" | tee -a "$LOG"

    # Short PT polish.
    ./target/release/pt_e2 \
        --pt-seconds "$PT_S" \
        --skip-sa-compare \
        --start-from "$CHILD" \
        --seed $((i * 17 + 7)) \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|Report:)" || true

    # Read latest output.
    LATEST=$(ls -t output/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST" ]]; then
        FINAL=$(jq '.score.matched_edges' "$LATEST" 2>/dev/null || echo "0")
        echo "polished: $FINAL/480 ($LATEST)" | tee -a "$LOG"
        if [[ "$FINAL" -gt "$BEST_SCORE" ]]; then
            BEST_SCORE=$FINAL
            BEST_CHILD=$LATEST
            echo "*** NEW BEST: $BEST_SCORE/480 ($BEST_CHILD) ***" | tee -a "$LOG"
        fi
    fi
done

echo | tee -a "$LOG"
echo "=== GA-LIGHT done: $(date) ===" | tee -a "$LOG"
echo "best child: $BEST_SCORE/480 at $BEST_CHILD" | tee -a "$LOG"
