#!/usr/bin/env bash
# T1 — LearnedOnTies hyperparameter sweep
# EPS × MAX_K grid at 60s each, parallel via xargs.
# Output: one JSON line per config to $OUT.

set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-ml/runs/v4/model.onnx}"
BUDGET_MS="${BUDGET_MS:-60000}"
OUT="${OUT:-output/vol32/t1_sweep.jsonl}"
PARALLEL="${PARALLEL:-4}"

EPS_LIST=(0.005 0.01 0.02 0.05 0.10 0.20 0.40)
MAXK_LIST=(2 4 8 12 16 24 32)

mkdir -p "$(dirname "$OUT")"
: > "$OUT"

run_one() {
    local eps="$1"
    local maxk="$2"
    local json
    json=$(E2_LEARNED_MODEL="$MODEL" \
           E2_ML_DEVICE=cpu \
           E2_ML_THREADS=2 \
           E2_LOT_EPS="$eps" \
           E2_LOT_MAX_K="$maxk" \
           target/release/canonical-eval \
               --profile joe_depth150_bp \
               --mode learned_on_ties \
               --budget-ms "$BUDGET_MS" \
           2>/dev/null | tail -1)
    # inject eps/max_k into the json
    json=$(echo "$json" | sed "s/^{/{\"eps\":$eps,\"max_k\":$maxk,/")
    echo "$json" >> "$OUT"
    echo "done eps=$eps max_k=$maxk -> $(echo "$json" | python3 -c 'import json,sys;d=json.loads(sys.stdin.read());print("depth",d["max_depth"])')"
}

export -f run_one
export MODEL BUDGET_MS OUT

# Build the (eps, maxk) cartesian
TASKS=""
for eps in "${EPS_LIST[@]}"; do
    for maxk in "${MAXK_LIST[@]}"; do
        TASKS+="$eps $maxk
"
    done
done

echo "$TASKS" | xargs -n 2 -P "$PARALLEL" bash -c 'run_one "$@"' _

echo "=== sweep complete -> $OUT ==="
echo "summary (depth, sorted desc):"
python3 -c "
import json
rows = [json.loads(l) for l in open('$OUT')]
rows.sort(key=lambda r: -r['max_depth'])
print(f\"{'eps':>8}  {'max_k':>5}  {'depth':>5}  {'nodes':>10}  {'backtracks':>10}\")
for r in rows:
    print(f\"{r['eps']:>8}  {r['max_k']:>5}  {r['max_depth']:>5}  {r['nodes']:>10}  {r['backtracks']:>10}\")
"
