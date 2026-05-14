#!/usr/bin/env bash
# Vol-36 T1 — ALNS lottery from vanilla_path --path-mode border-first partial.
# Mirrors vol-32's deep_458_basin recipe but on the new border-first partial.

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIAL="${PARTIAL:-output/vol-36/border_first_5min_best.json}"
SEEDS_PER="${SEEDS_PER:-12}"
BUDGET_MS="${BUDGET_MS:-300000}"
PARALLEL="${PARALLEL:-4}"
OPS_LIST="${OPS_LIST:-winning5 mega_mix full diverse}"

ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
OUT_DIR="output/vol-36/border_first_lottery"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

# Verify input
if [ ! -f "$PARTIAL" ]; then
    echo "Missing partial: $PARTIAL" >&2
    exit 1
fi
python3 -c "
import json
d = json.load(open('$PARTIAL'))
placed = sum(1 for p in d['placement'] if p is not None)
pids = [p['piece_id'] for p in d['placement'] if p is not None]
assert len(set(pids)) == len(pids), f'duplicate pieces in input!'
print(f'[lottery] input: {placed} placed, {len(set(pids))} unique')
"

run_one() {
    local seed="$1"
    local ops="$2"
    local log="$OUT_DIR/logs/seed${seed}_${ops}.log"
    "$ALNS_BIN" --cp-board "$PARTIAL" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops "$ops" --repair-kind sa > "$log" 2>&1 || true
    local saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=0
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        local r=$(./target/release/rescore_board "$saved" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}' | cut -d/ -f1)
        local uniq=$(python3 -c "
import json
d = json.load(open('$saved'))
pieces = [x['piece_id'] for x in d['placement'] if x is not None]
print('valid' if len(set(pieces)) == len(pieces) else 'DUP')
" 2>/dev/null)
        if [ "$uniq" = "valid" ]; then
            rescore=$r
        else
            rescore="INVALID"
        fi
    fi
    local logged=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | cut -d= -f2 | cut -d/ -f1)
    echo "{\"seed\":$seed,\"ops\":\"$ops\",\"logged\":${logged:-0},\"rescore\":\"${rescore:-0}\",\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[border-first] seed=$seed ops=$ops → logged=$logged rescore=$rescore"
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
echo "[lottery] $N runs at $BUDGET_MS ms each, parallelism=$PARALLEL"

cat "$RUN_FILE" | xargs -n2 -P"$PARALLEL" bash -c 'run_one "$0" "$1"'

echo ""
echo "=== Top results ==="
jq -s 'map(select(.rescore != "INVALID" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:15] | .[] | "\(.rescore)  seed=\(.seed) ops=\(.ops) (logged=\(.logged))"' -r "$SUMMARY"
