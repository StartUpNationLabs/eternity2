#!/usr/bin/env bash
# Vol-37 — ALNS lottery on canonical partials from all 7 valid records.
# Goal: find a verified canonical-compliant ≥459 board.
#
# Strategy: 5 seeds × 4 ops × 7 starts × 5min ALNS = 140 runs.
# At -P4 parallel, ~280 minutes wall clock.

set -euo pipefail
cd "$(dirname "$0")/.."

PARALLEL="${PARALLEL:-4}"
BUDGET_MS="${BUDGET_MS:-300000}"
SEEDS="${SEEDS:-1 2 3 4 5}"
OPS_LIST="${OPS_LIST:-winning5 mega_mix full diverse}"

ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
OUT_DIR="output/vol-37/canonical_lottery"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

# List of canonical partials (already-made-canonical)
PARTIALS=(
    "output/vol-37/canonical_partials/RECORD_BREAK_458_vanilla_fast_alns.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_457_blackwood_mrv_30min_seed4.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_457_blackwood_mrv_5min_seed10.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_457_blackwood_mrv_5min_seed7.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_458_vol35_deep458_winning5_seed5.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_457_vol35_deep458_full_seed5_3hints.canonical.json"
    "output/vol-37/canonical_partials/RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints.canonical.json"
)

# Pre-fill the 254-cell partials via prune_restart MaxScore so ALNS starts complete
echo "[vol-37] pre-filling 254-cell partials via prune_restart MaxScore..."
for P in "${PARTIALS[@]}"; do
    BASE=$(basename "$P" .json)
    N_PLACED=$(python3 -c "
import json
d = json.load(open('$P'))
print(sum(1 for p in d['placement'] if p is not None))
")
    if [ "$N_PLACED" = "256" ]; then
        # Already complete (canonical 457 or 458 from blackwood_mrv)
        cp "$P" "$OUT_DIR/${BASE}.filled.json"
        echo "  $BASE: already 256, copied"
    else
        # Run prune_restart pin-all MaxScore 60s to fill
        OUT="$OUT_DIR/${BASE}.filled.json"
        if [ ! -f "$OUT" ]; then
            echo "  $BASE: pre-filling..."
            target/release/prune_restart \
                --start "$P" \
                --cp-budget-ms 60000 \
                --rounds 1 \
                --seed 1 \
                --pin-all-from-start \
                --max-score \
                --out-dir "$OUT_DIR/prune_${BASE}" > /dev/null 2>&1
            if [ -f "$OUT_DIR/prune_${BASE}/round_1_board.json" ]; then
                cp "$OUT_DIR/prune_${BASE}/round_1_board.json" "$OUT"
                FSCORE=$(./target/release/rescore_board "$OUT" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
                echo "    filled to $FSCORE"
            fi
        fi
    fi
done

run_one() {
    local partial="$1"
    local seed="$2"
    local ops="$3"
    local base=$(basename "$partial" .filled.json)
    local log="$OUT_DIR/logs/${base}_s${seed}_${ops}.log"
    "$ALNS_BIN" --cp-board "$partial" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops "$ops" --repair-kind sa > "$log" 2>&1 || true
    local saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=0
    local uniq=0
    local hints_ok=0
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        local r=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
        local check=$(python3 -c "
import json
d = json.load(open('$saved'))
pl = d['placement']
pids = [x['piece_id'] for x in pl if x is not None]
canonical = {34: 207, 45: 254, 135: 138, 210: 180, 221: 248}
hints_ok = sum(1 for pos, pid in canonical.items() if any(p for p in pl if p is not None and p.get('pos') == pos and p['piece_id'] == pid))
print(f'{len(set(pids))}/{len(pids)} {hints_ok}/5')
" 2>/dev/null)
        uniq=$(echo "$check" | cut -d' ' -f1)
        hints_ok=$(echo "$check" | cut -d' ' -f2)
        rescore=$r
    fi
    local logged=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    echo "{\"start\":\"$base\",\"seed\":$seed,\"ops\":\"$ops\",\"logged\":${logged:-0},\"rescore\":\"${rescore:-0}\",\"uniq\":\"${uniq}\",\"hints_ok\":\"${hints_ok}\",\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[vol-37] $base s=$seed ops=$ops → logged=$logged rescore=$rescore uniq=$uniq hints=$hints_ok"
}

export -f run_one
export ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

# Build run file
RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for P in "$OUT_DIR"/*.filled.json; do
    for s in $SEEDS; do
        for op in $OPS_LIST; do
            echo "$P $s $op" >> "$RUN_FILE"
        done
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[vol-37] $N runs total at $BUDGET_MS ms each, parallelism=$PARALLEL"

cat "$RUN_FILE" | xargs -n3 -P"$PARALLEL" bash -c 'run_one "$0" "$1" "$2"'

echo ""
echo "=== Top valid canonical results (hints=5/5) ==="
jq -s 'map(select(.hints_ok == "5/5" and .rescore != "0" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:20] | .[] | "\(.rescore) \(.start) seed=\(.seed) ops=\(.ops) uniq=\(.uniq)"' -r "$SUMMARY"

echo ""
echo "=== Top all results regardless of hint compliance ==="
jq -s 'map(select(.rescore != "0" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:20] | .[] | "\(.rescore) [hints=\(.hints_ok)] \(.start) seed=\(.seed) ops=\(.ops)"' -r "$SUMMARY"
