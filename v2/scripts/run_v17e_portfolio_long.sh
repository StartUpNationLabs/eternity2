#!/bin/bash
# Vol-17 — long-form noise-injected schedule portfolio.
# 8 schedule seeds × 5min CP + 5min ALNS each = ~80 min sequential.
# Tests if any of the v17e schedule perturbations produces a better
# basin than v17a (455 ceiling).
set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
mkdir -p output/v17_exp

NOISE=0.15
SEEDS="1 2 3 4 5 6 7 8"
CP_MS=300000
ALNS_MS=300000

START=$(date '+%s')
for sched_seed in $SEEDS; do
    log="output/v17_exp/v17e_long_sched${sched_seed}.stderr.log"
    echo "[$(date '+%H:%M:%S')] v17e long sched_seed=${sched_seed} (5+5 min)"
    ./target/bench-fast/run_e2_blackwood \
        --cp-budget-ms $CP_MS --alns-budget-ms $ALNS_MS \
        --seed 1 --arms blackwood_raw \
        --schedule calibrated_v17e \
        --noise-amplitude $NOISE --schedule-seed "$sched_seed" \
        > "$log" 2>&1
    result=$(grep "ALNS:" "$log" | tail -1 | grep -oE "matched=[0-9]+/480" | head -1)
    echo "[$(date '+%H:%M:%S')] sched_seed=${sched_seed}: $result"
done
END=$(date '+%s')
echo "Portfolio done in $((END - START))s"
echo ""
echo "Summary across all v17e long runs:"
for sched_seed in $SEEDS; do
    log="output/v17_exp/v17e_long_sched${sched_seed}.stderr.log"
    m=$(grep "ALNS:" "$log" | tail -1 | grep -oE "matched=[0-9]+/480")
    echo "  sched_seed=${sched_seed}: $m"
done | tee output/v17_exp/v17e_long_summary.txt
