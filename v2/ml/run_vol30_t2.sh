#!/usr/bin/env bash
# Vol-30 T2 — long-imitation overnight experiment.
# Assumes canonical_traj_long.jsonl is already captured (100 seeds × 60s).
# Trains two models for comparison:
#   v3b: same hidden=64 as v3, but on 5x the data (100 trajectories).
#   v4:  bigger model (hidden=128, color_emb=24) on the same data.
# Then evaluates both under canonical-eval with mode=learned and
# mode=learned_on_ties.

set -euo pipefail

# 1) Preprocess
echo "=== preprocess long trajectories ==="
uv run python preprocess_canonical.py \
    --traj data/canonical_traj_long.jsonl \
    --puzzle ../../data/puzzles/size_16_official_eternity.csv \
    --out data/canonical_traj_long.v2.pt \
    --candidates 12

# 2a) Train v3b (same config as v3, more data)
echo
echo "=== train v3b (hidden=64) ==="
mkdir -p runs/v3b
E2_ML_DEVICE=cpu E2_ML_THREADS=8 PYTHONUNBUFFERED=1 uv run python train_v2_cached.py \
    --data data/canonical_traj_long.v2.pt \
    --out runs/v3b/model.pt \
    --epochs 30 --batch-size 512 --lr 1e-3 --hidden 64

# 2b) Train v4 (bigger model)
echo
echo "=== train v4 (hidden=128) ==="
mkdir -p runs/v4
E2_ML_DEVICE=cpu E2_ML_THREADS=8 PYTHONUNBUFFERED=1 uv run python train_v2_cached.py \
    --data data/canonical_traj_long.v2.pt \
    --out runs/v4/model.pt \
    --epochs 50 --batch-size 512 --lr 1e-3 --hidden 128 --color-emb 24

# 3) Export ONNX
echo
echo "=== ONNX export ==="
uv run python export_v2.py --ckpt runs/v3b/model.pt --out runs/v3b/model.onnx
uv run python export_v2.py --ckpt runs/v4/model.pt --out runs/v4/model.onnx

# 4) Gate measurements
PUZZLE=$(cd ../../data/puzzles && pwd)/size_16_official_eternity.csv
BP=$(cd ../output/v12_bp && pwd)/edge_bp_60i.json
BENCH=$(cd ../target/release && pwd)/canonical-eval

echo
echo "=== baseline (sanity) ==="
$BENCH --profile joe_depth150_bp --mode default --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"

echo
echo "=== v3 (vol-29 model, 20 traj, hidden=64) - learned_on_ties ==="
E2_LEARNED_MODEL="$PWD/runs/v3/model.onnx" $BENCH --profile joe_depth150_bp --mode learned_on_ties --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"

echo
echo "=== v3b (100 traj, hidden=64) - learned ==="
E2_LEARNED_MODEL="$PWD/runs/v3b/model.onnx" $BENCH --profile joe_depth150_bp --mode learned --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"

echo "=== v3b (100 traj, hidden=64) - learned_on_ties ==="
E2_LEARNED_MODEL="$PWD/runs/v3b/model.onnx" $BENCH --profile joe_depth150_bp --mode learned_on_ties --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"

echo
echo "=== v4 (100 traj, hidden=128) - learned ==="
E2_LEARNED_MODEL="$PWD/runs/v4/model.onnx" $BENCH --profile joe_depth150_bp --mode learned --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"

echo "=== v4 (100 traj, hidden=128) - learned_on_ties ==="
E2_LEARNED_MODEL="$PWD/runs/v4/model.onnx" $BENCH --profile joe_depth150_bp --mode learned_on_ties --budget-ms 60000 --puzzle "$PUZZLE" --bp-path "$BP"
