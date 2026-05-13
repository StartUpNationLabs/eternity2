#!/usr/bin/env bash
# T3 — Multi-seed PT lottery from canonical depth-174 LearnedOnTies partial.
#
# Vol-32 finding: the depth-174 partial is a structural attractor — v3, v3b,
# v4 with any (eps, max_k) all converge to the EXACT same board (md5 match).
# So the only variability axis is the pt_e2 PT seed.
#
# Plan: 30 seeds × 4 replicas × 15 min, 2 in parallel (each uses 4 cores).
# Gives ~30/2 * 15 = 225 min ≈ 3.75 hr. Or 30 seeds × 2 replicas × 15 min
# with 4 parallel = 30/4 * 15 = 112 min ≈ 1.9 hr.

set -euo pipefail
cd "$(dirname "$0")/.."

PARTIAL="${PARTIAL:-output/vol-32/t3_partials/canonical_174.pt_e2.json}"
SEEDS_LIST="${SEEDS_LIST:-1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30}"
PT_SECONDS="${PT_SECONDS:-900}"   # 15 min per seed
N_REPLICAS="${N_REPLICAS:-2}"
PARALLEL="${PARALLEL:-4}"
OUT_DIR="${OUT_DIR:-output/vol-32/t3_pt}"
SUMMARY="$OUT_DIR/summary.jsonl"

OUT_DIR_ABS="$(pwd)/$OUT_DIR"
LOGS_DIR="$OUT_DIR_ABS/logs"
RUNS_DIR="$OUT_DIR_ABS/runs"
SUMMARY_ABS="$OUT_DIR_ABS/summary.jsonl"
PT_BIN="$(pwd)/target/release/pt_e2"
PUZZLE_ABS="$(cd ../data/puzzles && pwd)/size_16_official_eternity.csv"
mkdir -p "$OUT_DIR_ABS" "$LOGS_DIR" "$RUNS_DIR"
: > "$SUMMARY_ABS"

PARTIAL_ABS="$(pwd)/$PARTIAL"
[ -f "$PARTIAL_ABS" ] || { echo "FATAL: $PARTIAL not found"; exit 1; }
echo "T3 starting: partial=$PARTIAL_ABS pt_bin=$PT_BIN out_dir=$OUT_DIR"

run_one() {
    local seed="$1"
    local log_abs="$LOGS_DIR/seed${seed}.log"
    local cwd_abs="$RUNS_DIR/seed${seed}"
    mkdir -p "$cwd_abs"
    local t0=$SECONDS
    (cd "$cwd_abs" && "$PT_BIN" \
        --puzzle "$PUZZLE_ABS" \
        --start-from "$PARTIAL_ABS" \
        --pin-hints \
        --houdayer-every 10 \
        --kick-every 20 \
        --seed "$seed" \
        --n-replicas "$N_REPLICAS" \
        --pt-seconds "$PT_SECONDS" \
        --skip-sa-compare \
        > "$log_abs" 2>&1)
    local elapsed=$((SECONDS - t0))
    local best=$(grep -oE 'global_best=[0-9]+' "$log_abs" | tail -1 | sed 's/global_best=//')
    best="${best:-0}"
    echo "{\"seed\":$seed,\"replicas\":$N_REPLICAS,\"pt_seconds\":$PT_SECONDS,\"best\":$best,\"elapsed\":$elapsed}" >> "$SUMMARY_ABS"
    echo "[t3] seed=$seed best=$best elapsed=${elapsed}s"
}

export -f run_one
export N_REPLICAS PT_SECONDS PARTIAL_ABS SUMMARY_ABS LOGS_DIR RUNS_DIR PT_BIN PUZZLE_ABS

echo "$SEEDS_LIST" | tr ' ' '\n' | xargs -I {} -P "$PARALLEL" bash -c 'run_one "$1"' _ {}

echo
echo "=== T3 SUMMARY ==="
python3 -c "
import json
import statistics
rows = [json.loads(l) for l in open('$SUMMARY_ABS')]
rows.sort(key=lambda r: -r['best'])
print(f\"{'seed':>4}  {'best':>5}  {'elapsed_s':>9}\")
for r in rows:
    print(f\"{r['seed']:>4}  {r['best']:>5}  {r['elapsed']:>9}\")
scores = [r['best'] for r in rows]
if scores:
    print(f'\nN={len(scores)} mean={statistics.mean(scores):.1f} median={statistics.median(scores)} max={max(scores)} min={min(scores)} stdev={statistics.stdev(scores) if len(scores)>1 else 0:.2f}')
"
