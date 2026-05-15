#!/bin/bash
# Vol-60 T4 — ALNS with corner-pinning, on each perm's best CP snapshot.
# Uses alns_only's new --extra-hint flag (vol-60 fix) to keep corners pinned.

set -uo pipefail

ALNS_MS="${1:-300000}"   # 5 min per seed
N_SEEDS="${2:-4}"
PARALLEL="${3:-8}"
SWEEP_DIR="${4:?usage: vol60_corner_alns_pinned.sh ALNS_MS N_SEEDS PARALLEL SWEEP_DIR}"

cd "$(dirname "$0")/.."
TS="${VOL60_RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
RES_DIR="output/vol-60/corner_alns_pinned_${TS}"
mkdir -p "$RES_DIR"
echo "Sweep input: $SWEEP_DIR"
echo "Output dir: $RES_DIR"

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"

# Read each perm's best snapshot + the corner pin pieces from the snapshot itself.
for partial in "$SWEEP_DIR"/p*_best.json; do
    [ -f "$partial" ] || continue
    pid=$(basename "$partial" _best.json)
    # Extract corner piece IDs from the partial (which has the corners placed at pos 0/15/240/255)
    TL_P=$(/tmp/vol53_venv/bin/python3 -c "import json; d=json.load(open('$partial')); print(d['placement'][0]['piece_id'])" 2>/dev/null || echo "")
    TR_P=$(/tmp/vol53_venv/bin/python3 -c "import json; d=json.load(open('$partial')); print(d['placement'][15]['piece_id'])" 2>/dev/null || echo "")
    BL_P=$(/tmp/vol53_venv/bin/python3 -c "import json; d=json.load(open('$partial')); e=d['placement'][240]; print(e['piece_id'] if e else 'null')" 2>/dev/null || echo "")
    BR_P=$(/tmp/vol53_venv/bin/python3 -c "import json; d=json.load(open('$partial')); e=d['placement'][255]; print(e['piece_id'] if e else 'null')" 2>/dev/null || echo "")
    if [ -z "$TL_P" ] || [ -z "$TR_P" ]; then continue; fi
    echo "perm $pid: corners TL=$TL_P TR=$TR_P BL=$BL_P BR=$BR_P"

    for ((seed=1; seed<=N_SEEDS; seed++)); do
        OUT="$RES_DIR/result_${pid}_seed${seed}.json"
        if [ -f "$OUT" ] && [ -s "$OUT" ]; then continue; fi
        echo "$partial $seed $OUT" >> "$JOBS_FILE"
    done
done

N=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "$(date +%H:%M:%S) Queued $N jobs (parallel=$PARALLEL, alns_ms=$ALNS_MS)"

# We pin all 4 corners by position; alns_only --extra-hint POS uses the
# partial's placement at POS as the pinned value.
export RES_DIR
cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    SNAP="$0"
    SEED="$1"
    OUT="$2"
    NAME=$(basename "$OUT" .json | sed "s/result_//")
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SNAP" --alns-budget-ms '"$ALNS_MS"' \
        --seed "$SEED" --ops winning5 --t 1.0 \
        --extra-hint 0 --extra-hint 15 --extra-hint 240 --extra-hint 255 \
        > "$LOG" 2>&1
    EXIT=$?
    if [ $EXIT -ne 0 ]; then
        echo "[$(date +%H:%M:%S)] $NAME FAILED exit=$EXIT"
        exit 0
    fi
    SAVED=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
    if [ -z "$SAVED" ] || [ ! -f "$SAVED" ]; then
        echo "[$(date +%H:%M:%S)] $NAME NO SAVED"
        exit 0
    fi
    cp "$SAVED" "$OUT"
    SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] $NAME → score=$SCORE"
'

echo
echo "=== SUMMARY ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "perm,seed,score" > "$SUMMARY"
for r in "$RES_DIR"/result_*.json; do
    [ -f "$r" ] || continue
    bn=$(basename "$r" .json | sed 's/result_//')
    perm=$(echo "$bn" | sed 's/_seed.*//')
    seed=$(echo "$bn" | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "$perm,$seed,$SCORE" >> "$SUMMARY"
done

echo "Top 10:"
sort -t',' -k3 -nr "$SUMMARY" | head -10

echo ""
echo "Max per perm:"
awk -F',' 'NR>1 {if ($3 > best[$1]) best[$1] = $3} END {for (p in best) print p, best[p]}' "$SUMMARY" | sort -k2 -nr
