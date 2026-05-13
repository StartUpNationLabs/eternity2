#!/usr/bin/env bash
# Vol-32 follow-up — PT mini A/B across 3 partials.
# Uses the saturation finding: 30s PT × 8 seeds per partial.
# Compare TRUE LOT (lot_fixed_v4) vs BUGGY-LOT-was-Insertion (insertion_174) vs baseline (edge_bp_165).

set -euo pipefail
cd "$(dirname "$0")/.."

PT_SECONDS=30
N_REPLICAS=2
PARALLEL=4

OUT_DIR="output/vol-32/t6_mini_pt"
LOGS_DIR="$(pwd)/$OUT_DIR/logs"
RUNS_DIR="$(pwd)/$OUT_DIR/runs"
SUMMARY_ABS="$(pwd)/$OUT_DIR/summary.jsonl"
PARTIALS_DIR="$(pwd)/output/vol-32/t4"
PUZZLE_ABS="$(cd ../data/puzzles && pwd)/size_16_official_eternity.csv"
PT_BIN="$(pwd)/target/release/pt_e2"

mkdir -p "$LOGS_DIR" "$RUNS_DIR"
: > "$SUMMARY_ABS"

run_one() {
    local partial="$1"
    local seed="$2"
    local log_abs="$LOGS_DIR/${partial}_seed${seed}.log"
    local cwd_abs="$RUNS_DIR/${partial}_seed${seed}"
    mkdir -p "$cwd_abs"
    local partial_path="$PARTIALS_DIR/${partial}.pt_e2.json"
    local t0=$SECONDS
    (cd "$cwd_abs" && "$PT_BIN" \
        --puzzle "$PUZZLE_ABS" \
        --start-from "$partial_path" \
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
    echo "{\"partial\":\"$partial\",\"seed\":$seed,\"best\":$best,\"elapsed\":$elapsed}" >> "$SUMMARY_ABS"
    echo "[t6-mini] partial=$partial seed=$seed best=$best elapsed=${elapsed}s"
}

export -f run_one
export LOGS_DIR RUNS_DIR PT_BIN PUZZLE_ABS N_REPLICAS PT_SECONDS PARTIALS_DIR SUMMARY_ABS

PARTIALS="edge_bp_165 insertion_174 lot_fixed_v4"
SEEDS="1 2 3 4 5 6 7 8"

(for p in $PARTIALS; do for s in $SEEDS; do echo "$p $s"; done; done) \
    | xargs -n 2 -P "$PARALLEL" bash -c 'run_one "$@"' _

echo
echo "=== T6 mini-PT A/B summary ==="
python3 -c "
import json, statistics
from collections import defaultdict
rows = [json.loads(l) for l in open('$SUMMARY_ABS')]
by_partial = defaultdict(list)
for r in rows:
    by_partial[r['partial']].append(r['best'])
print(f\"{'partial':>20}  {'N':>3}  {'mean':>6}  {'median':>6}  {'max':>4}  {'min':>4}  {'stdev':>6}\")
for p in sorted(by_partial):
    s = by_partial[p]
    sd = statistics.stdev(s) if len(s) > 1 else 0
    print(f\"{p:>20}  {len(s):>3}  {statistics.mean(s):>6.1f}  {statistics.median(s):>6}  {max(s):>4}  {min(s):>4}  {sd:>6.2f}\")
"
