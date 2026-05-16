#!/bin/bash
# Vol-106 T11 — break-index threshold sweep.
#
# Measures (max_depth, best_score, nps) across break-first ∈ {150, 160,
# 170, 180, 192} with break-count=15 each. 10s budget single-thread,
# 1 seed per config (multi-seed via thread shuffle if needed).
#
# Total wall-time: ~5 min.

set -e

OUT="output/vol-106/break-sweep_$(date +%Y%m%dT%H%M%S)"
mkdir -p "$OUT"

BIN=./target/release/bf_bw
PUZZLE=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv

echo "break_first,break_count,max_depth,best_score,nodes,nps" > "$OUT/results.csv"

for FIRST in 150 160 170 180 192; do
    echo "=== break-first=$FIRST count=15, single-thread, 10s ==="
    OUT_J=$("$BIN" --puzzle "$PUZZLE" --schedule v17a --threads 1 \
                   --break-first "$FIRST" --break-count 15 --budget-ms 10000 2>/dev/null \
                   | tail -1)
    echo "$OUT_J" | tee -a "$OUT/raw.jsonl"
    # parse using a simple grep + extract
    MD=$(echo "$OUT_J" | grep -oE '"max_depth":[0-9]+' | grep -oE '[0-9]+')
    BS=$(echo "$OUT_J" | grep -oE '"best_score":[0-9]+' | grep -oE '[0-9]+')
    NODES=$(echo "$OUT_J" | grep -oE '"nodes":[0-9]+' | grep -oE '[0-9]+')
    NPS=$(echo "$OUT_J" | grep -oE '"nps":[0-9]+' | grep -oE '[0-9]+')
    echo "$FIRST,15,$MD,$BS,$NODES,$NPS" >> "$OUT/results.csv"
done

echo
echo "=== summary ($OUT/results.csv) ==="
cat "$OUT/results.csv"
