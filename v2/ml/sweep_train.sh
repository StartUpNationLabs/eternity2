#!/usr/bin/env bash
# T2 — Model size / LR / data ablation
#
# Vol-32 sharpening: vol-30 T2 already showed +9 invariant across
# v3 (h=64, 20tr), v3b (h=64, 100tr), v4 (h=128, 100tr). So a pure
# size/data sweep on the 165-ceiling data is unlikely to lift past 174.
#
# Therefore T2 here focuses on the NOVEL territory:
#  A) Larger models (h=256, h=192) on existing 100-traj data.
#     Tests whether vol-30 size sweep was just too small.
#  B) Bootstrap data: trajectories captured under LearnedOnTies
#     (depth 174 each) rather than the EdgeBp baseline (depth 165).
#     This is the most likely lift — training on the stronger
#     composite teacher's behaviour.
#  C) BP-blend ratio: train a variant that explicitly fuses BP-score
#     with NN-score (env-var-tunable) — distinct from T1's pure-NN
#     reranking within ties.
#
# Each model evaluated at:
#  - default LearnedOnTies (EPS=0.05, MAX_K=8) — for comparability.
#  - best EPS/MAX_K from T1 (passed via BEST_EPS, BEST_MAXK env).

set -euo pipefail
cd "$(dirname "$0")"

DATA_100="data/canonical_traj_long.v2.pt"
DATA_BOOT="${DATA_BOOT:-data/canonical_traj_lot.v2.pt}"   # built by bootstrap_capture+preprocess

BUDGET_MS="${BUDGET_MS:-60000}"
OUT_LOG="${OUT_LOG:-../output/vol-32/t2_eval.jsonl}"

PUZZLE="$(cd ../../data/puzzles && pwd)/size_16_official_eternity.csv"
BP="$(cd ../output/v12_bp && pwd)/edge_bp_60i.json"
BENCH="$(cd ../target/release && pwd)/canonical-eval"

mkdir -p "$(dirname "$OUT_LOG")"
mkdir -p runs/vol32
: > "$OUT_LOG"

BEST_EPS="${BEST_EPS:-0.05}"
BEST_MAXK="${BEST_MAXK:-8}"

train_one() {
    local name="$1"; local data="$2"; local hidden="$3"
    local color_emb="$4"; local lr="$5"; local epochs="$6"
    local out="runs/vol32/${name}"
    mkdir -p "$out"
    if [ ! -f "$out/model.onnx" ]; then
        echo
        echo "=== TRAIN $name (data=$data h=$hidden emb=$color_emb lr=$lr ep=$epochs) ==="
        E2_ML_DEVICE=cpu E2_ML_THREADS=8 PYTHONUNBUFFERED=1 \
            uv run python train_v2_cached.py \
                --data "$data" --out "$out/model.pt" \
                --epochs "$epochs" --batch-size 512 \
                --lr "$lr" --hidden "$hidden" --color-emb "$color_emb"
        uv run python export_v2.py --ckpt "$out/model.pt" --out "$out/model.onnx"
    fi
}

eval_one() {
    local name="$1"; local eps="$2"; local maxk="$3"; local label="$4"
    local model="$PWD/runs/vol32/${name}/model.onnx"
    [ -f "$model" ] || { echo "skip eval $name (no model)"; return; }
    echo
    echo "=== EVAL $name | eps=$eps max_k=$maxk ($label) ==="
    local json
    json=$(E2_LEARNED_MODEL="$model" \
           E2_ML_DEVICE=cpu E2_ML_THREADS=8 \
           E2_LOT_EPS="$eps" E2_LOT_MAX_K="$maxk" \
           "$BENCH" --profile joe_depth150_bp --mode learned_on_ties \
                    --budget-ms "$BUDGET_MS" --puzzle "$PUZZLE" --bp-path "$BP" \
           2>/dev/null | tail -1)
    json=$(echo "$json" | sed "s/^{/{\"model\":\"$name\",\"eps\":$eps,\"max_k\":$maxk,\"variant\":\"$label\",/")
    echo "$json" >> "$OUT_LOG"
    echo "$json" | python3 -c "import json,sys;d=json.loads(sys.stdin.read());print('  ->','depth',d['max_depth'],'nodes',d['nodes'])"
}

# === Track A — size sweep at upper end on existing 100-traj data ===
train_one t2A_h192 "$DATA_100" 192 24 1e-3 40
train_one t2A_h256 "$DATA_100" 256 24 1e-3 40

# === Track B — bootstrap from LearnedOnTies trajectories ===
if [ -f "$DATA_BOOT" ]; then
    train_one t2B_boot_h128 "$DATA_BOOT" 128 24 1e-3 40
    train_one t2B_boot_h64  "$DATA_BOOT" 64  16 1e-3 40
    train_one t2B_boot_h256 "$DATA_BOOT" 256 24 1e-3 40
fi

# === Track C — LR sensitivity at the new size ===
train_one t2C_h128_lr5e4 "$DATA_100" 128 24 5e-4 60
train_one t2C_h128_lr3e3 "$DATA_100" 128 24 3e-3 30

# === Track D — long-train at best config from vol-30 (v4) for control ===
train_one t2D_h128_ep120 "$DATA_100" 128 24 1e-3 120

ALL_MODELS="t2A_h192 t2A_h256 t2B_boot_h128 t2B_boot_h64 t2B_boot_h256 t2C_h128_lr5e4 t2C_h128_lr3e3 t2D_h128_ep120"

# Eval each at default and best-T1
for m in $ALL_MODELS; do
    eval_one "$m" 0.05 8 "default"
    if [ "$BEST_EPS" != "0.05" ] || [ "$BEST_MAXK" != "8" ]; then
        eval_one "$m" "$BEST_EPS" "$BEST_MAXK" "t1_best"
    fi
done

# Also re-eval v4 with best-T1 EPS/MAX_K to verify baseline-of-baseline
if [ "$BEST_EPS" != "0.05" ] || [ "$BEST_MAXK" != "8" ]; then
    eval_one "../v4" "$BEST_EPS" "$BEST_MAXK" "t1_best_v4"
fi

echo
echo "=== T2 COMPLETE -> $OUT_LOG ==="
python3 -c "
import json
rows = [json.loads(l) for l in open('$OUT_LOG')]
rows.sort(key=lambda r: (-r['max_depth'], r['nodes']))
print(f\"{'model':>20}  {'variant':>10}  {'eps':>6}  {'max_k':>5}  {'depth':>5}  {'nodes':>10}\")
for r in rows:
    print(f\"{r['model']:>20}  {r['variant']:>10}  {r['eps']:>6}  {r['max_k']:>5}  {r['max_depth']:>5}  {r['nodes']:>10}\")
"
