#!/bin/bash
# Generate Blackwood CP partials for seeds 2, 3, 4 sequentially (~15 min).
# Each is a 5-min CP run with calibrated_v17a, no ALNS.
# Output: output/v17_exp/canonical_v17a_cp_seedN.json
set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2

for seed in 2 3 4; do
    log_file="output/v17_exp/cp_seed${seed}.stderr.log"
    out_file="output/v17_exp/canonical_v17a_cp_seed${seed}.json"
    echo "[$(date '+%H:%M:%S')] generating CP partial seed=${seed}..."
    ./target/bench-fast/run_e2_blackwood \
        --cp-budget-ms 300000 --alns-budget-ms 0 \
        --seed "$seed" --arms blackwood_raw --schedule calibrated_v17a \
        > "$log_file" 2>&1
    # Find the produced cp_board.json and copy to a stable name.
    latest_run_dir=$(ls -td output/v15_e2_blackwood/run_*/ | head -1)
    cp "${latest_run_dir}/blackwood_raw_cp_board.json" "$out_file"
    matched=$(grep "CP:" "$log_file" | grep -oE "matched=[0-9]+/480" | head -1)
    echo "[$(date '+%H:%M:%S')] seed=${seed} cp done: ${matched} → ${out_file}"
done
echo "[$(date '+%H:%M:%S')] All CP partials generated."
