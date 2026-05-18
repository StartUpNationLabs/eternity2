#!/bin/bash
# Full transformer → ALNS pipeline.
#
# Workflow:
# 1. Use trained transformer to generate a starting board (hint-only or warm-start).
# 2. Run alns_only basic on it, 30min budget.
# 3. Save best result.
#
# Usage:
#   ./transformer_alns_pipeline.sh [checkpoint.pt] [n_iterations]
set -uo pipefail

CHECKPOINT="${1:-runs/v2_edges_long/best.pt}"
N_ITERATIONS="${2:-10}"
REPO="/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2"
cd "$REPO"

OUT_DIR="output/vol-125/transformer_alns_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT_DIR"
echo "OUT_DIR=$OUT_DIR"

if [ ! -f "ml/transformer_v1/$CHECKPOINT" ]; then
    echo "Checkpoint not found: ml/transformer_v1/$CHECKPOINT"
    echo "Train first via: ml/.venv/bin/python3 ml/transformer_v1/train_v2.py ..."
    exit 1
fi

# Phase 1: Generate N starting boards via transformer.
for i in $(seq 1 $N_ITERATIONS); do
    echo "[$i/$N_ITERATIONS] transformer inference..."
    init_board="$OUT_DIR/initial_$i.json"
    cd ml/transformer_v1
    if [ $((i % 2)) -eq 0 ]; then
        # Half iterations: hint-only warm start, iterative inference.
        ml/.venv/bin/python3 transformer_to_alns.py \
            --checkpoint "$CHECKPOINT" \
            --iterative \
            --strict-hints \
            --out "$REPO/$init_board" 2>&1 | tail -5
    else
        # Half: single-shot inference.
        ml/.venv/bin/python3 transformer_to_alns.py \
            --checkpoint "$CHECKPOINT" \
            --strict-hints \
            --out "$REPO/$init_board" 2>&1 | tail -5
    fi
    cd "$REPO"

    if [ -f "$init_board" ]; then
        # Phase 2: ALNS basic 30min on this seed.
        echo "[$i/$N_ITERATIONS] ALNS basic 30min..."
        ./target/bench-fast/alns_only \
            --cp-board "$init_board" \
            --ops basic \
            --alns-budget-ms 1800000 \
            --seed $i \
            > "$OUT_DIR/alns_$i.log" 2>&1
        # Quick result.
        matched=$(grep -oE "matched=[0-9]+" "$OUT_DIR/alns_$i.log" | sed 's/matched=//' | tail -1)
        echo "[$i/$N_ITERATIONS] result: matched=$matched"
    fi
done

echo "Done. Results in $OUT_DIR"
echo "Best score:"
grep -hoE "matched=[0-9]+" "$OUT_DIR"/alns_*.log 2>/dev/null | sed 's/matched=//' | sort -n | tail -1
