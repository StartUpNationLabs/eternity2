#!/bin/bash
# E6 launcher: PT-on-ALNS with 4 different CP partials (one per chain).
# Run AFTER gen_cp_partials.sh has produced canonical_v17a_cp_seed{2,3,4}.json
set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2

CP_BOARDS="output/v17_exp/canonical_v17a_cp_362_seed1.json,output/v17_exp/canonical_v17a_cp_seed2.json,output/v17_exp/canonical_v17a_cp_seed3.json,output/v17_exp/canonical_v17a_cp_seed4.json"

echo "[$(date '+%H:%M:%S')] E6: PT-ALNS multi-CP-partial"
./target/bench-fast/alns_pt \
    --cp-boards "$CP_BOARDS" \
    --n-chains 4 \
    --t-min 0.5 --t-max 2.0 \
    --inner-iters 25 \
    --time-budget-ms 300000 \
    --ops winning5 \
    --seed 1
