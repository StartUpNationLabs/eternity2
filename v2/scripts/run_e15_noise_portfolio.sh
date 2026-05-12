#!/bin/bash
# Vol-17 — noise-injected schedule portfolio (v17e × 4 seeds, sequential).
# Each run is 3min CP + 3min ALNS = 6min. Total ~24min.
set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2

for sched_seed in 1 2 3 4; do
    log="output/v17_exp/E15_v17e_noise015_sched${sched_seed}.stderr.log"
    echo "[$(date '+%H:%M:%S')] E15 sched_seed=${sched_seed} noise=0.15"
    ./target/bench-fast/run_e2_blackwood \
        --cp-budget-ms 180000 --alns-budget-ms 180000 \
        --seed 1 --arms blackwood_raw \
        --schedule calibrated_v17e \
        --noise-amplitude 0.15 --schedule-seed "$sched_seed" \
        > "$log" 2>&1
    grep "ALNS:" "$log" | tail -1
done
echo "[$(date '+%H:%M:%S')] noise portfolio done."
