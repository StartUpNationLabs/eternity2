#!/bin/bash
# Full summary of v17 overnight queue results.
# Run after the night script completes (or anytime to see partial progress).
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2

print_block() {
    local n=$1; local desc=$2; local logname=$3
    local log="output/v17_runs/${logname}.stderr.log"
    if [[ ! -f "$log" ]]; then
        printf "Block %-3s %-60s  NOT_RUN\n" "$n:" "$desc"
        return
    fi
    # Extract per-arm matched scores
    local alns_line
    alns_line=$(grep "ALNS:" "$log" 2>/dev/null | tail -1 || true)
    local cp_line
    cp_line=$(grep -E "CP:" "$log" 2>/dev/null | tail -1 || true)
    if [[ -n "$alns_line" ]]; then
        local m
        m=$(echo "$alns_line" | grep -oE "matched=[0-9]+/480" | head -1)
        printf "Block %-3s %-60s  %s\n" "$n:" "$desc" "$m"
    elif [[ -n "$cp_line" ]]; then
        local m
        m=$(echo "$cp_line" | grep -oE "matched=[0-9]+/480" | head -1)
        printf "Block %-3s %-60s  (CP only) %s\n" "$n:" "$desc" "$m"
    else
        printf "Block %-3s %-60s  PENDING\n" "$n:" "$desc"
    fi
}

echo "=== vol-17 overnight queue results ==="
echo
print_block 1  "11-ops seed=1 (HingeDestroy + CP-repair primary)" "block1_seed1_11ops"
print_block 2  "4-seed cold portfolio calibrated arm"             "block2_portfolio_4seeds"
print_block 3  "K-pipeline seed=1 v17a"                           "block3_k_seed1"
print_block 4  "Extended seed=1 10+10min"                          "block4_seed1_extended"
print_block 5  "Cold portfolio seeds 5-8"                          "block5_portfolio_seeds5to8"
print_block 6  "K-pipeline v17b seed=1"                            "block6_k_v17b_seed1"
print_block 7  "Long ALNS seed=1 5+15min"                          "block7_seed1_longalns"
print_block 8  "Baseline portfolio 4 seeds"                        "block8_baseline_portfolio"
print_block 9  "K-pipeline seed=2"                                 "block9_k_seed2"
print_block 10 "K-pipeline seed=3"                                 "block10_k_seed3"
print_block 11 "v17b + all 11 ops seed=1"                          "block11_v17b_allops_seed1"
print_block 12 "Very-long ALNS seed=1 30min"                       "block12_seed1_30min_alns"

echo
echo "=== Best scores across all v17 runs ==="
grep -h "ALNS:" output/v17_runs/*.stderr.log 2>/dev/null \
    | grep -oE "matched=[0-9]+/480" \
    | sort -t= -k2 -nr \
    | uniq -c \
    | head -10
echo
echo "Master log:"
tail -5 output/v17_runs/_night_master.log 2>/dev/null
