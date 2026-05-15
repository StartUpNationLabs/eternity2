#!/bin/bash
# Vol-60 T4 — ALNS on each corner-sweep snapshot.
# For each perm's best snapshot, run ALNS with multiple seeds.

set -uo pipefail

ALNS_MS="${1:-300000}"   # 5 min ALNS
N_SEEDS="${2:-4}"
PARALLEL="${3:-8}"

cd "$(dirname "$0")/.."
SWEEP_DIR="output/vol-60/corner_sweep"
RES_DIR="output/vol-60/corner_sweep_alns"
mkdir -p "$RES_DIR"

# Find the BEST snapshot per perm (max depth).
JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"

for perm_dir in "$SWEEP_DIR"/snaps_p*; do
    [ -d "$perm_dir" ] || continue
    perm_id=$(basename "$perm_dir" | sed 's/snaps_//')

    # Find best snapshot in this dir by depth (from filename suffix)
    BEST=""
    BEST_DEPTH=0
    for snap in "$perm_dir"/*.json; do
        [ -f "$snap" ] || continue
        # Snapshot names like t0_s000_d150.json — extract depth from suffix
        DEPTH=$(basename "$snap" .json | grep -oE 'd[0-9]+' | tail -1 | sed 's/d//')
        if [ "${DEPTH:-0}" -gt "$BEST_DEPTH" ]; then
            BEST="$snap"
            BEST_DEPTH="$DEPTH"
        fi
    done

    if [ -z "$BEST" ]; then
        echo "skip $perm_id: no snapshots"
        continue
    fi

    # Also try the save-best file if it has higher depth
    SAVE_BEST="$SWEEP_DIR/${perm_id}_best.json"
    if [ -f "$SAVE_BEST" ]; then
        # save-best is a board JSON, doesn't necessarily have depth in filename
        # Just compare to snapshot best
        :
    fi

    for ((seed=1; seed<=N_SEEDS; seed++)); do
        OUT="$RES_DIR/result_${perm_id}_seed${seed}.json"
        if [ -f "$OUT" ] && [ -s "$OUT" ]; then continue; fi
        echo "$BEST $seed $OUT" >> "$JOBS_FILE"
    done
done

N=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "$(date +%H:%M:%S) Queued $N jobs (alns_ms=$ALNS_MS, parallel=$PARALLEL)"

cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    SNAP="$0"
    SEED="$1"
    OUT="$2"
    NAME=$(basename "$OUT" .json | sed "s/result_//")
    LOG="${OUT}.log"
    target/release/alns_only --cp-board "$SNAP" --alns-budget-ms '"$ALNS_MS"' \
        --seed "$SEED" --ops winning5 --t 1.0 > "$LOG" 2>&1
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
    SCORE=$(python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] $NAME → score=$SCORE  src=$(basename $SNAP)"
'

echo
echo "=== SUMMARY (per-perm) ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "perm,seed,score,best_snap" > "$SUMMARY"
for r in "$RES_DIR"/result_*.json; do
    [ -f "$r" ] || continue
    bn=$(basename "$r" .json | sed 's/result_//')
    perm=$(echo "$bn" | sed 's/_seed.*//')
    seed=$(echo "$bn" | grep -oE 'seed[0-9]+' | grep -oE '[0-9]+')
    SCORE=$(python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "$perm,$seed,$SCORE," >> "$SUMMARY"
done

echo "Best 10:"
sort -t',' -k3 -nr "$SUMMARY" | head -10

echo ""
echo "Best per perm:"
awk -F',' 'NR>1 {if ($3 > best[$1]) best[$1] = $3} END {for (p in best) print p, best[p]}' "$SUMMARY" | sort -k2 -nr
