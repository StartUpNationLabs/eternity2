#!/usr/bin/env bash
# Vol-29 end-to-end driver: preprocess -> train -> export -> gate.
# Assumes data/canonical_traj.jsonl is already captured by
# `target/release/canonical-capture`.

set -euo pipefail

PREFIX=runs/v3
mkdir -p $PREFIX

echo "=== preprocess canonical trajectories ==="
uv run python preprocess_canonical.py \
    --traj data/canonical_traj.jsonl \
    --puzzle ../../data/puzzles/size_16_official_eternity.csv \
    --out data/canonical_traj.v2.pt \
    --candidates 12

echo
echo "=== train v2 on canonical .pt ==="
E2_ML_DEVICE=cpu E2_ML_THREADS=8 PYTHONUNBUFFERED=1 uv run python train_v2_cached.py \
    --data data/canonical_traj.v2.pt \
    --out $PREFIX/model.pt \
    --epochs 30 --batch-size 256 --lr 1e-3

echo
echo "=== ONNX export ==="
uv run python export_v2.py --ckpt $PREFIX/model.pt --out $PREFIX/model.onnx

echo
echo "=== gate at canonical 16x16 ==="
uv run python canonical_gate.py \
    --model $PREFIX/model.onnx \
    --budget-ms 60000 \
    --out $PREFIX/canonical_gate.json
