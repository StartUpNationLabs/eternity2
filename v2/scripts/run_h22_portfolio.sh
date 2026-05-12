#!/bin/bash
# Vol-17 — H22 (shuffle_within_blackwood_ties) portfolio.
# 8 seeds × 5min CP + 5min ALNS each = ~80 min sequential.
# Tests schedule-invariant CP-partial diversity via tie-shuffle.
set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
mkdir -p output/v17_exp

SEEDS="1 2 3 4 5 6 7 8"
CP_MS=300000
ALNS_MS=300000

START=$(date '+%s')
for seed in $SEEDS; do
    log="output/v17_exp/h22_seed${seed}.stderr.log"
    echo "[$(date '+%H:%M:%S')] H22 seed=${seed} (5+5 min) shuffle_within_blackwood_ties=true"
    ./target/bench-fast/run_e2_blackwood \
        --cp-budget-ms $CP_MS --alns-budget-ms $ALNS_MS \
        --seed "$seed" --arms blackwood_raw \
        --schedule calibrated_v17a \
        --shuffle-blackwood-ties \
        > "$log" 2>&1
    result=$(grep "ALNS:" "$log" | tail -1 | grep -oE "matched=[0-9]+/480" | head -1)
    echo "[$(date '+%H:%M:%S')] seed=${seed}: $result"
done
END=$(date '+%s')
echo "H22 portfolio done in $((END - START))s"

echo ""
echo "H22 portfolio summary:"
for seed in $SEEDS; do
    log="output/v17_exp/h22_seed${seed}.stderr.log"
    m=$(grep "ALNS:" "$log" | tail -1 | grep -oE "matched=[0-9]+/480")
    echo "  seed=${seed}: $m"
done | tee output/v17_exp/h22_summary.txt
