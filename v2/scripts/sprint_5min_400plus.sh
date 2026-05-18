#!/bin/bash
# 5-minute sprint: generate as many boards >= 400 as possible.
#
# Strategy: bf_bw is our fastest record-producer (84M nps single-thread).
# A 30-second bf_bw run typically reaches score 400-450 on canonical E2.
# Run 7 parallel workers, each cycling through random seed-offsets,
# saving any partial with score >= 400.

set -uo pipefail

cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2

OUT_DIR="output/vol-125/sprint_5min_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
echo "OUT_DIR=$OUT_DIR"

WORKERS=7
TOTAL_BUDGET_SEC=300  # 5 min total
PER_JOB_BF=30000      # 30 sec bf_bw budget (ms)

# Worker: keep running bf_bw with new random offsets until time runs out.
worker() {
    local worker_id=$1
    local end_time=$2
    local count=0
    while [ "$(date +%s)" -lt "$end_time" ]; do
        local off=$((RANDOM % 10000))
        local partial="$OUT_DIR/w${worker_id}_off${off}_p.json"

        # Run bf_bw with random seed offset; dump-partial saves placement.
        timeout 35 ./target/bench-fast/bf_bw \
            --threads 1 \
            --seed-offset "$off" \
            --budget-ms "$PER_JOB_BF" \
            --dump-partial "$partial" >/dev/null 2>&1 || continue

        [ -f "$partial" ] || continue

        # Check score — bf_bw dump-partial includes "score" field.
        local score
        score=$(python3 -c "
import json, sys
try:
    with open('$partial') as f: d = json.load(f)
    print(d.get('score', 0))
except: print(0)
" 2>/dev/null)

        if [ "$score" -ge 400 ] 2>/dev/null; then
            local final="$OUT_DIR/sprint_w${worker_id}_off${off}_score${score}.json"
            mv "$partial" "$final"
            count=$((count + 1))
            echo "[worker $worker_id] off=$off score=$score → saved ($count saves)"
        else
            rm -f "$partial"
        fi
    done
    echo "[worker $worker_id] done, saved $count boards"
}

export -f worker
export OUT_DIR PER_JOB_BF

START_TIME=$(date +%s)
END_TIME=$((START_TIME + TOTAL_BUDGET_SEC))

# Launch 7 workers.
declare -a PIDS=()
for i in $(seq 1 $WORKERS); do
    worker "$i" "$END_TIME" &
    PIDS+=("$!")
done

# Wait.
for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
done

# Final tally.
echo ""
echo "=== SPRINT COMPLETE ==="
SAVED=$(ls "$OUT_DIR"/sprint_*.json 2>/dev/null | wc -l | tr -d ' ')
echo "Total saved boards >= 400: $SAVED"
echo "Output: $OUT_DIR"

echo ""
echo "Score distribution:"
for f in "$OUT_DIR"/sprint_*.json; do
    [ -f "$f" ] || continue
    python3 -c "
import json, sys
with open(sys.argv[1]) as fh: d = json.load(fh)
print(d.get('score', d.get('matched', 0)))
" "$f" 2>/dev/null
done | sort -n | uniq -c | sort -rn
