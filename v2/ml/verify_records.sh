#!/usr/bin/env bash
# Verify all claimed record boards by:
#   1. score (rescore_board output)
#   2. piece uniqueness
#   3. canonical hint compliance (5/5 means all canonical hints honored)
#
# Catches:
#   - score-reporting bugs (vol-34 found 2)
#   - piece-uniqueness violations (vol-35 pin_hints bug)
#   - canonical-vs-displaced-hint distinction (vol-37 finding)

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x target/release/rescore_board ]; then
    echo "[build] target/release/rescore_board missing"
    source $HOME/.cargo/env
    cargo build --release --bin rescore_board
fi

# Format: expected_score:path
declare -a TARGETS=(
    # 458 boards (non-canonical caveat: 3/5 hints honored)
    "458:output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"
    "458:output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json"

    # 457 canonical (5/5 hints, blackwood_mrv family)
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json"
    "457:output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json"

    # 456 canonical (5/5 hints, blackwood_raw)
    "456:output/vol-32/blackwood_raw_alns_seed2_456.json"
    "456:output/vol-32/blackwood_raw_alns_seed4_456.json"

    # 455 canonical (NEW vol-39, 5/5 hints, ALNS-diverse from canonical 454)
    "455:output/vol-39/records/RECORD_CANONICAL_455_vol39_diverse_seed1.json"
    "455:output/vol-39/records/RECORD_CANONICAL_455_vol39_diverse_seed5.json"

    # 454 canonical (NEW vol-36, 5/5 hints, make-canonical pathway)
    "454:output/vol-36/records/RECORD_CANONICAL_454_vol36_seed5.json"
)

PASS=0
FAIL=0
echo "expected  rescore  uniq      hints  status  path"
echo "--------------------------------------------------------------------------------"
for entry in "${TARGETS[@]}"; do
    expected="${entry%%:*}"
    path="${entry#*:}"
    if [ ! -f "$path" ]; then
        printf "%4s      ----     ----      ---    MISSING  %s\n" "$expected" "$path"
        FAIL=$((FAIL+1))
        continue
    fi
    rescore=$(./target/release/rescore_board "$path" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
    # Piece-uniqueness + canonical hint check
    check=$(python3 -c "
import json
d = json.load(open('$path'))
pl = d['placement']
pids = [x['piece_id'] for x in pl if x is not None]
uniq = 'OK' if len(set(pids)) == len(pids) else 'DUP'
canonical = {34: 207, 45: 254, 135: 138, 210: 180, 221: 248}
hints_ok = sum(1 for pos, pid in canonical.items()
               if any(p for p in pl if p is not None and p.get('pos') == pos and p['piece_id'] == pid))
print(f'{uniq} {hints_ok}/5')
")
    uniq_check=$(echo "$check" | cut -d' ' -f1)
    hints_check=$(echo "$check" | cut -d' ' -f2)

    if [ "$rescore" = "$expected" ] && [ "$uniq_check" = "OK" ]; then
        status="PASS"
        PASS=$((PASS+1))
    else
        status="FAIL"
        FAIL=$((FAIL+1))
    fi
    printf "%4s      %4s     %-8s  %3s    %s    %s\n" \
        "$expected" "$rescore" "$uniq_check" "$hints_check" "$status" "$path"
done

echo "--------------------------------------------------------------------------------"
echo "PASS=$PASS  FAIL=$FAIL"
echo ""
echo "Note: 'hints' column shows 5/5 = canonical-respecting board"
echo "      x/5 (x<5) = canonical hint(s) displaced (non-canonical record class)"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
