#!/usr/bin/env bash
# Vol-35 — re-lottery v2: one representative per BASIN FAMILY (19 reps × 4 seeds = 76 runs).
# Uses cluster_basins.py output to pick reps. Less concurrent OOM risk.

set -euo pipefail
cd "$(dirname "$0")/.."

SEEDS_PER="${1:-4}"
BUDGET_MS="${2:-300000}"
PARALLEL="${PARALLEL:-4}"  # reduced from -P8 to avoid OOM
ALNS_BIN="${ALNS_BIN:-target/release/alns_only}"
SWEEP_ROOT="output/vol-35/sweep_v3"
OUT_DIR="output/vol-35/family_lottery_v3_b"
SUMMARY="$OUT_DIR/summary.jsonl"

mkdir -p "$OUT_DIR/logs"
: > "$SUMMARY"

# Productive thread_ids from cluster_basins.py (19 distinct basin families)
TIDS=(0 1 4 5 7 100 102 103 104 105 107 110 165 220 275 330 385 440 495)

# For each tid, find its DEEPEST snapshot in sweep_v3
declare -a PICKS=()
for tid in "${TIDS[@]}"; do
    # Determine which offset this tid belongs to (offset = tid - (tid % 50)
    # but the buckets are at 0, 50, 100, 150, etc., so:
    offset=$(( (tid / 50) * 50 ))
    dir="$SWEEP_ROOT/offset_$(printf '%04d' $offset)"
    # In-offset thread index (filenames use 2-digit prefix)
    in_off=$((tid - offset))
    # Find snapshots with this in_offset index
    # Filename format: t<XX>_s<NNN>_d<DDD>.json where XX = in_off if 0-9 needs zero-pad to 2 chars
    pattern=$(printf 't%02d_s*_d*.json' $in_off)
    deepest=$(ls "$dir"/$pattern 2>/dev/null | sort -t_ -k3 -nr | head -1)
    if [ -n "$deepest" ]; then
        PICKS+=("$tid:$deepest")
    fi
done
echo "[lottery_v3_b] picked ${#PICKS[@]} family representatives"

run_one() {
    local entry="$1"
    local seed="$2"
    local tid=$(echo "$entry" | cut -d: -f1)
    local partial=$(echo "$entry" | cut -d: -f2)
    local log="$OUT_DIR/logs/tid${tid}_seed${seed}.log"
    "$ALNS_BIN" --cp-board "$partial" --alns-budget-ms "$BUDGET_MS" \
        --seed "$seed" --ops winning5 --repair-kind sa > "$log" 2>&1 || true
    local saved=$(grep -h 'saved: ' "$log" | awk '{print $2}' | tail -1)
    local rescore=0
    if [ -n "$saved" ] && [ -f "$saved" ]; then
        # Both rescore AND piece-uniqueness check
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
    echo "{\"tid\":$tid,\"seed\":$seed,\"logged\":${logged:-0},\"rescore\":\"${rescore:-0}\",\"saved\":\"${saved:-}\"}" >> "$SUMMARY"
    echo "[lottery_v3_b] tid=$tid seed=$seed → logged=$logged rescore=$rescore"
}

export -f run_one
export ALNS_BIN BUDGET_MS OUT_DIR SUMMARY

RUN_FILE="$OUT_DIR/runs.txt"
: > "$RUN_FILE"
for pick in "${PICKS[@]}"; do
    for s in $(seq 1 "$SEEDS_PER"); do
        echo "$pick $s" >> "$RUN_FILE"
    done
done
N=$(wc -l < "$RUN_FILE")
echo "[lottery_v3_b] $N runs in $RUN_FILE, parallelism=$PARALLEL"

cat "$RUN_FILE" | xargs -n2 -P"$PARALLEL" bash -c 'run_one "$0" "$1"'

echo ""
echo "=== Top results ==="
jq -s 'map(select(.rescore != "INVALID" and (.rescore | tonumber) > 0)) | sort_by(-(.rescore | tonumber))[:15] | .[] | "\(.rescore)  tid=\(.tid) seed=\(.seed) (logged=\(.logged))"' -r "$SUMMARY"
