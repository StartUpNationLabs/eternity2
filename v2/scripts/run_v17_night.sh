#!/bin/bash
# Vol-17 overnight experiment queue.
# Run sequentially; each waits for previous to finish (no overlap).
# Designed for ~7-hour total budget. Each block is ~10-60 min.

set -e
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
mkdir -p output/v17_runs

log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

# Block 1: 11-ops single-seed (seed 1, calibrated_v17a + WorstBand+ComponentDestroy+HingeDestroy)
log "Block 1: 11-ops single-seed seed=1 (~10min)"
./target/bench-fast/run_e2_blackwood \
    --cp-budget-ms 300000 --alns-budget-ms 300000 \
    --seed 1 --arms blackwood_raw --schedule calibrated_v17a \
    > output/v17_runs/block1_seed1_11ops.stderr.log 2>&1

# Block 2: 4-seed cold portfolio with calibrated arm only
log "Block 2: 4-seed cold portfolio calibrated (~40min)"
./target/bench-fast/cold_portfolio \
    --seeds 1,2,3,4 --cp-ms 300000 --alns-ms 300000 --arms calibrated \
    > output/v17_runs/block2_portfolio_4seeds.stderr.log 2>&1

# Block 3: K-pipeline test on seed 1
log "Block 3: K-pipeline test seed=1 (~11min)"
./target/bench-fast/run_e2_blackwood_then_csp \
    --cp-bw-ms 180000 --cp-csp-ms 180000 --alns-ms 300000 \
    --seed 1 --schedule calibrated_v17a \
    > output/v17_runs/block3_k_seed1.stderr.log 2>&1

# Block 4: extended single seed - 10 min CP + 10 min ALNS on seed 1
log "Block 4: extended seed=1 10+10min (~20min)"
./target/bench-fast/run_e2_blackwood \
    --cp-budget-ms 600000 --alns-budget-ms 600000 \
    --seed 1 --arms blackwood_raw --schedule calibrated_v17a \
    > output/v17_runs/block4_seed1_extended.stderr.log 2>&1

# Block 5: 4 more seeds with calibrated arm (seeds 5-8)
log "Block 5: portfolio seeds 5-8 calibrated (~40min)"
./target/bench-fast/cold_portfolio \
    --seeds 5,6,7,8 --cp-ms 300000 --alns-ms 300000 --arms calibrated \
    > output/v17_runs/block5_portfolio_seeds5to8.stderr.log 2>&1

# Block 6: K-pipeline with v17b schedule on seed 1
log "Block 6: K-pipeline v17b seed=1 (~11min)"
./target/bench-fast/run_e2_blackwood_then_csp \
    --cp-bw-ms 180000 --cp-csp-ms 180000 --alns-ms 300000 \
    --seed 1 --schedule calibrated_v17b \
    > output/v17_runs/block6_k_v17b_seed1.stderr.log 2>&1

# Block 7: very-long single seed - 15 min ALNS on best CP partial
log "Block 7: very-long ALNS seed=1 5+15min (~20min)"
./target/bench-fast/run_e2_blackwood \
    --cp-budget-ms 300000 --alns-budget-ms 900000 \
    --seed 1 --arms blackwood_raw --schedule calibrated_v17a \
    > output/v17_runs/block7_seed1_longalns.stderr.log 2>&1

# Block 8: baseline portfolio comparison (4 seeds at baseline arm)
log "Block 8: baseline portfolio 4 seeds (~40min)"
./target/bench-fast/cold_portfolio \
    --seeds 1,2,3,4 --cp-ms 300000 --alns-ms 300000 --arms baseline \
    > output/v17_runs/block8_baseline_portfolio.stderr.log 2>&1

# Block 9: K-pipeline on seeds 2 and 3 (parallel-quality verification)
log "Block 9: K-pipeline seed=2 (~11min)"
./target/bench-fast/run_e2_blackwood_then_csp \
    --cp-bw-ms 180000 --cp-csp-ms 180000 --alns-ms 300000 \
    --seed 2 --schedule calibrated_v17a \
    > output/v17_runs/block9_k_seed2.stderr.log 2>&1

log "Block 10: K-pipeline seed=3 (~11min)"
./target/bench-fast/run_e2_blackwood_then_csp \
    --cp-bw-ms 180000 --cp-csp-ms 180000 --alns-ms 300000 \
    --seed 3 --schedule calibrated_v17a \
    > output/v17_runs/block10_k_seed3.stderr.log 2>&1

# Block 11: schedule v17b on seed 1 with all 11 ops (compare to v17a all-ops)
log "Block 11: v17b + all 11 ops seed=1 (~10min)"
./target/bench-fast/run_e2_blackwood \
    --cp-budget-ms 300000 --alns-budget-ms 300000 \
    --seed 1 --arms blackwood_raw --schedule calibrated_v17b \
    > output/v17_runs/block11_v17b_allops_seed1.stderr.log 2>&1

# Block 12: extended ALNS on seed 1 to test diminishing returns
log "Block 12: very-very-long ALNS seed=1 (~30min)"
./target/bench-fast/run_e2_blackwood \
    --cp-budget-ms 300000 --alns-budget-ms 1500000 \
    --seed 1 --arms blackwood_raw --schedule calibrated_v17a \
    > output/v17_runs/block12_seed1_30min_alns.stderr.log 2>&1

log "All blocks done."
