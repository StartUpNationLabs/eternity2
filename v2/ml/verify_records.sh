#!/usr/bin/env bash
# Verify all claimed record boards by rescore_board.
# Catches any silent score-reporting bugs (vol-34 found 2 of these).

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x target/release/rescore_board ]; then
    echo "[build] target/release/rescore_board missing"
    source $HOME/.cargo/env
    cargo build --release --bin rescore_board
fi

declare -a TARGETS=(
    "458:output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json"
    "457:output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json"
)

PASS=0
FAIL=0
echo "label              path                                                          expected  rescore  status"
for entry in "${TARGETS[@]}"; do
    expected="${entry%%:*}"
    path="${entry#*:}"
    if [ ! -f "$path" ]; then
        printf "%-18s %-60s %4s     MISSING\n" "claimed=$expected" "$path" "?"
        FAIL=$((FAIL+1))
        continue
    fi
    rescore=$(./target/release/rescore_board "$path" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    if [ "$rescore" = "$expected" ]; then
        printf "%-18s %-60s %4s     %4s  PASS\n" "claimed=$expected" "$path" "$expected" "$rescore"
        PASS=$((PASS+1))
    else
        printf "%-18s %-60s %4s     %4s  *** MISMATCH ***\n" "claimed=$expected" "$path" "$expected" "$rescore"
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "PASS=$PASS  FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
