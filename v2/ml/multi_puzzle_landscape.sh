#!/usr/bin/env bash
# Vol-35 — multi-puzzle landscape probe.
#
# For each of N puzzle seeds at 16×16/22c, generate the puzzle, dump
# to CSV, run vanilla_fast for SHORT_BUDGET, capture snapshots,
# aggregate. Lets us study basin landscape ACROSS different
# canonical-class puzzles (vs vol-34 T1 which used only seed=1
# = canonical Eternity II).
#
# Usage: ml/multi_puzzle_landscape.sh [N_PUZZLES] [BUDGET_MS] [SIZE] [COLORS]

set -euo pipefail
cd "$(dirname "$0")/.."

N="${1:-10}"
BUDGET_MS="${2:-30000}"
SIZE="${3:-16}"
COLORS="${4:-22}"
ROOT="output/vol-35/multi_puzzle"

mkdir -p "$ROOT/csvs" "$ROOT/snaps"

echo "[multi] generating + probing $N puzzles at ${SIZE}x${SIZE}/${COLORS}c, ${BUDGET_MS}ms each"

for seed in $(seq 1 "$N"); do
    csv="$ROOT/csvs/p_s${seed}.csv"
    snap_dir="$ROOT/snaps/p_s${seed}"
    mkdir -p "$snap_dir"
    if [ ! -f "$csv" ]; then
        ./target/release/dump_puzzle_csv \
            --size "$SIZE" --colors "$COLORS" --seed "$seed" --out "$csv" 2>&1 | tail -1
    fi
    if [ "$(ls $snap_dir/*.json 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
        echo "[multi] seed=$seed: already probed, skip"
        continue
    fi
    echo "[multi] seed=$seed: vanilla_fast probe..."
    ./target/release/vanilla_fast \
        --threads 8 \
        --budget-ms "$BUDGET_MS" \
        --puzzle "$csv" \
        --snapshot-dir "$snap_dir" \
        --snapshot-interval-ms 5000 \
        --snapshot-min-depth 150 \
        --snapshot-on-visit \
        > "$snap_dir/probe.log" 2>&1 || true
    nsnap=$(ls "$snap_dir"/*.json 2>/dev/null | wc -l | tr -d ' ')
    max_d=$(ls "$snap_dir"/*.json 2>/dev/null | awk -F'_d' '{print $NF}' | sed 's/\.json//' | sort -nr | head -1)
    echo "[multi] seed=$seed done: nsnap=$nsnap max_depth=${max_d:-?}"
done

# Aggregate
echo ""
echo "=== Multi-puzzle landscape summary ==="
for d in "$ROOT/snaps"/p_s*; do
    seed=$(basename "$d" | sed 's/p_s//')
    nsnap=$(ls "$d"/*.json 2>/dev/null | wc -l | tr -d ' ')
    max_d=$(ls "$d"/*.json 2>/dev/null | awk -F'_d' '{print $NF}' | sed 's/\.json//' | sort -nr | head -1)
    tids=$(ls "$d"/*.json 2>/dev/null | awk -F'/' '{print $NF}' | cut -c2-3 | sort -u | tr '\n' ',')
    echo "  seed=$seed: nsnap=$nsnap max_d=${max_d:-?} tids=$tids"
done
