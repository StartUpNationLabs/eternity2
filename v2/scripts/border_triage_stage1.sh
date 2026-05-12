#!/usr/bin/env bash
# Stage 1 of vol-7 border-triage funnel.
# Take top-K borders from vol-6's top_1000_by_corner_tightness.jsonl,
# generate synthetic seeds, run pt_e2 with pin-perimeter for a short
# budget per border. Output: a summary table of (border_idx, best_score).
#
# Usage: scripts/border_triage_stage1.sh <N_BORDERS> <PT_SECONDS> <N_REPLICAS> <PARALLEL>
# Example: scripts/border_triage_stage1.sh 24 60 4 4
set -euo pipefail

N_BORDERS=${1:-12}
PT_SECONDS=${2:-60}
N_REPLICAS=${3:-2}
PARALLEL=${4:-4}

BORDER_FILE=output/borders/top_1000_by_corner_tightness.jsonl
SEED_DIR=output/v7_synth_seeds
RESULTS=output/v7_triage_results
mkdir -p "$SEED_DIR" "$RESULTS"

echo "=== STAGE 1: $N_BORDERS borders × ${PT_SECONDS}s × $N_REPLICAS replicas, parallelism $PARALLEL ==="
echo "started at $(date)"
echo

# Generate synthetic seeds for borders 0..(N_BORDERS-1) of the top file.
for i in $(seq 0 $((N_BORDERS - 1))); do
  out="$SEED_DIR/border_top$((i+1)).json"
  if [[ ! -f "$out" ]]; then
    python3 scripts/synth_border_seed.py "$BORDER_FILE" "$i" "$out" >/dev/null 2>&1
  fi
done

# Run pt_e2 on each, $PARALLEL at a time.
function run_one() {
  local idx=$1
  local seed=$((100000 + idx))
  local out_log="$RESULTS/border_$(printf '%03d' $idx).log"
  ./target/release/pt_e2 \
    --start-from "$SEED_DIR/border_top$((idx+1)).json" \
    --pin-perimeter \
    --pt-seconds "$PT_SECONDS" \
    --skip-sa-compare \
    --seed "$seed" \
    --n-replicas "$N_REPLICAS" \
    > "$out_log" 2>&1
  local best=$(grep -oE "best=[0-9]+/480" "$out_log" | tail -1 | grep -oE "[0-9]+" | head -1)
  echo "border $idx: best=${best:-?}/480"
}

export -f run_one
export PT_SECONDS N_REPLICAS SEED_DIR RESULTS
# Use xargs for parallelism
seq 0 $((N_BORDERS - 1)) | xargs -n 1 -P "$PARALLEL" -I {} bash -c 'run_one "$@"' _ {}

echo
echo "=== STAGE 1 SUMMARY ==="
echo
echo "border_idx  best_score"
echo "----------  ----------"
for i in $(seq 0 $((N_BORDERS - 1))); do
  best=$(grep -oE "best=[0-9]+/480" "$RESULTS/border_$(printf '%03d' $i).log" 2>/dev/null | tail -1 | grep -oE "[0-9]+" | head -1)
  printf "%-10d  %s\n" "$i" "${best:-?}"
done | sort -k2 -n -r
echo
echo "finished at $(date)"
