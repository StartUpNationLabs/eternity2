#!/usr/bin/env bash
# Verify all claimed record boards by score AND piece uniqueness.
# Catches: (1) score-reporting bugs (vol-34 found 2 of these);
# (2) piece-uniqueness violations in CP partials / ALNS outputs
#     (vol-35 discovery: vanilla_fast pin_hints snapshot writer
#     produces duplicate pieces when hint position unreached but
#     hint piece placed elsewhere — bug fix shipped vol-35).

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x target/release/rescore_board ]; then
    echo "[build] target/release/rescore_board missing"
    source $HOME/.cargo/env
    cargo build --release --bin rescore_board
fi

declare -a TARGETS=(
    "458:output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"
    "458:output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json"
)

PASS=0
FAIL=0
echo "label              path                                                          expected  rescore  uniq  status"
for entry in "${TARGETS[@]}"; do
    expected="${entry%%:*}"
    path="${entry#*:}"
    if [ ! -f "$path" ]; then
        printf "%-18s %-60s %4s     MISSING\n" "claimed=$expected" "$path" "?"
        FAIL=$((FAIL+1))
        continue
    fi
    rescore=$(./target/release/rescore_board "$path" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    # Piece-uniqueness check via python
    uniq_check=$(python3 -c "
import json, sys
d = json.load(open('$path'))
pieces = [x['piece_id'] for x in d['placement'] if x is not None]
if len(set(pieces)) == len(pieces):
    print('valid')
else:
    counter = {}
    for p in pieces:
        counter[p] = counter.get(p, 0) + 1
    dupes = [p for p, c in counter.items() if c > 1]
    print(f'DUP{dupes}')
")
    if [ "$rescore" = "$expected" ] && [ "$uniq_check" = "valid" ]; then
        printf "%-18s %-60s %4s     %4s  %5s  PASS\n" "claimed=$expected" "$path" "$expected" "$rescore" "$uniq_check"
        PASS=$((PASS+1))
    else
        printf "%-18s %-60s %4s     %4s  %5s  *** FAIL ***\n" "claimed=$expected" "$path" "$expected" "$rescore" "$uniq_check"
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "PASS=$PASS  FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
