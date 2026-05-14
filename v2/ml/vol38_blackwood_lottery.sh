#!/usr/bin/env bash
# Vol-38 — scaled blackwood_raw lottery (32 seeds × 5min from same partial).
# Per vol-32 BACKLOG: "32-seed × 5min lottery would likely produce a 458 outlier."

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIAL="${PARTIAL:-output/vol-38/blackwood_partial/cp5min.json}"
SEEDS_PER="${SEEDS_PER:-32}"
BUDGET_MS="${BUDGET_MS:-300000}"
PARALLEL="${PARALLEL:-4}"
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
OPS_LIST="${OPS_LIST:-winning5 mega_mix full diverse}"

OUT_DIR="output/vol-38/blackwood_lottery"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

if [ ! -f "$PARTIAL" ]; then
    echo "[vol-38] partial missing: $PARTIAL" >&2
    exit 1
fi

INIT=$(python3 -c "
import json
d=json.load(open('$PARTIAL'))
pl=d['placement']
print(sum(1 for p in pl if p is not None))
")
echo "[vol-38] partial: $PARTIAL, $INIT cells placed"

run_one() {
    local seed="$1"
    local ops="$2"
    local log="$OUT_DIR/logs/seed${seed}_${ops}.log"
    "$ALNS_BIN" --cp-board "$PARTIAL" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops "$ops" --repair-kind sa > "$log" 2>&1 || true
    local saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=0 uniq=0 hints_ok=0
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
    echo "{\"seed\":$seed,\"ops\":\"$ops\",\"logged\":${logged:-0},\"rescore\":\"${rescore:-0}\",\"uniq\":\"${uniq}\",\"hints_ok\":\"${hints_ok}\",\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[vol-38] s=$seed ops=$ops → logged=$logged rescore=$rescore uniq=$uniq hints=$hints_ok"
}
export -f run_one
export ALNS_BIN BUDGET_MS PARTIAL OUT_DIR SUMMARY

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for s in $(seq 1 "$SEEDS_PER"); do
    for op in $OPS_LIST; do
        echo "$s $op" >> "$RUN_FILE"
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[vol-38] $N runs total at $BUDGET_MS ms each, parallelism=$PARALLEL"

cat "$RUN_FILE" | xargs -n2 -P"$PARALLEL" bash -c 'run_one "$0" "$1"'

echo "=== Top valid canonical results (hints=5/5) ==="
jq -s 'map(select(.hints_ok == "5/5" and .rescore != "0" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:20] | .[] | "\(.rescore) seed=\(.seed) ops=\(.ops)"' -r "$SUMMARY"
echo "=== Top all ==="
jq -s 'map(select(.rescore != "0" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:20] | .[] | "\(.rescore) [hints=\(.hints_ok)] seed=\(.seed) ops=\(.ops)"' -r "$SUMMARY"
