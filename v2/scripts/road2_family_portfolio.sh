#!/usr/bin/env bash
# Vol-18 Road 2 — trajectory family portfolio.
#
# Test 4 schedule variants × 3 seeds = 12 trajectory families.
# Each: 240s CP + 240s ALNS = 8 min/run. Total ~96 min.
#
# For each finished run, extract final matched score + ALNS best.
# Append to a master SCOREBOARD.txt with timestamps.
#
# After the portfolio completes, the highest-scoring family's CP
# board is the seed for the next phase (OracleSwap probes + hot-PT).

set -uo pipefail
cd "$(dirname "$0")/.."

OUT=output/v18_road2
mkdir -p "$OUT"
SCOREBOARD="$OUT/SCOREBOARD.txt"
START=$(date +%s)
echo "# Road 2 family portfolio started at $(date)" > "$SCOREBOARD"
echo "# schedule | seed | sched_seed | shuffle_ties | cp_match | alns_match | wall_s" >> "$SCOREBOARD"

run_one() {
    local schedule=$1
    local seed=$2
    local sched_seed=$3
    local shuffle=$4
    local label="${schedule}_s${seed}_ss${sched_seed}_${shuffle}"
    local logfile="$OUT/${label}.log"
    local t0=$(date +%s)
    local args="--schedule $schedule --seed $seed --schedule-seed $sched_seed \
                --cp-budget-ms 240000 --alns-budget-ms 240000 \
                --ops winning5 --arms blackwood"
    if [ "$shuffle" = "shuffle" ]; then
        args="$args --shuffle-blackwood-ties"
    fi
    echo "=== $label ==="
    ./target/bench-fast/run_e2_blackwood $args 2>&1 | tee "$logfile" | grep -E "CP:|ALNS:|matched=|^\[" | head -10
    local t1=$(date +%s)
    local wall=$((t1 - t0))
    # run_e2_blackwood prints "[label] CP: ... matched=N/480 ..." and similar for ALNS.
    local cp_match=$(grep -oE "CP:.*matched=[0-9]+" "$logfile" | head -1 | grep -oE "[0-9]+$")
    local alns_match=$(grep -oE "matched=[0-9]+/480" "$logfile" | tail -1 | grep -oE "[0-9]+/480" | cut -d/ -f1)
    echo "${schedule} | ${seed} | ${sched_seed} | ${shuffle} | ${cp_match:-?} | ${alns_match:-?} | ${wall}" >> "$SCOREBOARD"
    echo "  done: cp=$cp_match alns=$alns_match wall=${wall}s"
}

for schedule in calibrated_v17b calibrated_v17c calibrated_v17e; do
    for seed in 1 2 3; do
        run_one $schedule $seed 1 noshuffle
    done
done

# Also a v17b variant with shuffle_blackwood_ties (per vol-17 F3 directional signal)
run_one calibrated_v17b 1 1 shuffle
run_one calibrated_v17b 2 1 shuffle
run_one calibrated_v17b 3 1 shuffle

# v17e with different schedule seeds (noise diversity)
run_one calibrated_v17e 1 2 noshuffle
run_one calibrated_v17e 1 3 noshuffle
run_one calibrated_v17e 1 4 noshuffle

END=$(date +%s)
TOTAL=$((END - START))
echo "" >> "$SCOREBOARD"
echo "# Portfolio complete at $(date). Total wall: ${TOTAL}s" >> "$SCOREBOARD"

echo ""
echo "=== Final SCOREBOARD ==="
cat "$SCOREBOARD"
