#!/bin/bash
# Vol-62 — A/B test: winning5 vs winning5_smallcomp on the local 459 board.
#
# Tests the hypothesis that lowering ComponentDestroy's min_size from 6 to
# 2 (so the operator FIRES at the 459 regime instead of falling back to
# ConflictDriven) escapes the 459 basin.
#
# Source board: local 459 record (p06_corner_1_0_2_3_seed2).
# Setup: same seed across the two ops presets so the ONLY difference is
# the operator set.
#
# Output: timestamped dir under output/vol-62/

set -uo pipefail
cd "$(dirname "$0")/.."

TS="$(date +%Y%m%dT%H%M%S)"
RES="output/vol-62/cqd_smallcomp_ab_${TS}"
mkdir -p "$RES"
echo "Run: $RES"

SRC="output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"
SEEDS=(1 2 3 4 5)
BUDGET_MS=300000  # 5 min per run

# Build job list — parallel across the 3×5 = 15 runs
JOBS="$RES/jobs.txt"
: > "$JOBS"
for ops in winning5 winning5_smallcomp winning5_cluster; do
  for seed in "${SEEDS[@]}"; do
    out="$RES/result_${ops}_seed${seed}.json"
    echo "$ops $seed $out" >> "$JOBS"
  done
done

# Launch with 4-way parallelism (10 jobs × 5min, 4 at a time → ~15min wall)
cat "$JOBS" | xargs -L 1 -P 4 bash -c '
  OPS="$0"; SEED="$1"; OUT="$2"
  LOG="${OUT}.log"
  target/release/alns_only \
    --cp-board "'"$SRC"'" \
    --alns-budget-ms '"$BUDGET_MS"' \
    --seed "$SEED" --ops "$OPS" --t 1.0 \
    > "$LOG" 2>&1
  SAVED=$(grep "^saved:" "$LOG" | tail -1 | awk "{print \$2}")
  if [ -n "$SAVED" ] && [ -f "$SAVED" ]; then
    cp "$SAVED" "$OUT"
    SCORE=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open(\"$OUT\")).get(\"matched\", 0))" 2>/dev/null || echo "?")
    echo "[$(date +%H:%M:%S)] ops=$OPS seed=$SEED → $SCORE"
  else
    echo "[$(date +%H:%M:%S)] ops=$OPS seed=$SEED FAILED"
  fi
'

echo ""
echo "=== SUMMARY ==="
echo "Source: 459 (local p06)"
echo ""
for ops in winning5 winning5_smallcomp winning5_cluster; do
  echo "--- $ops ---"
  scores=()
  for seed in "${SEEDS[@]}"; do
    r="$RES/result_${ops}_seed${seed}.json"
    [ -f "$r" ] || continue
    s=$(/tmp/vol53_venv/bin/python3 -c "import json; print(json.load(open('$r')).get('matched', 0))" 2>/dev/null || echo 0)
    echo "  seed=$seed → $s"
    scores+=("$s")
  done
  echo "  scores: ${scores[*]}"
done

echo ""
echo "Records (≥460):"
./scripts/verify_records.sh "$RES"/result_*.json 2>&1 | grep -E "460|461|462|463|464|465|466|467|468|469|470" || echo "  (no records ≥ 460 found)"
echo ""
echo "Run dir: $RES"
