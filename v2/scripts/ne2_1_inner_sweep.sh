#!/usr/bin/env bash
# NE2.1: inner-loop forbidden-mismatch penalty sweep.
#
# Differs from ne2_k_sweep.sh: uses the rebuilt pt_e2 binary which now
# applies the soft penalty inside SA Metropolis (NOT JUST at PT swap
# time). Honest comparison to vanilla NE2's K-sweep requires keeping
# the same K-grid and same total budget.
#
# After NE2 K-sweep, we observed:
#   K=0   → 448 (baseline)
#   K=10  → 449 with fmm=0 (cold chain reached the constrained-449
#           basin but did not break 449)
#   K=50+ → over-constrained, raw scores fell back to ~448 with fmm>0
#
# Hypothesis for NE2.1: inner-loop penalty makes the cold chain
# actively avoid forbidden mismatches during search (not just at swap
# time), so the chain at the constrained-449 basin can search MORE of
# the surrounding state space without being penalized for transient
# fmm>0 visits during exploration.
#
# Sweep: K ∈ {10, 50, 100} (skip K=0 — same as NE2 K=0). K=200 omitted
# (over-constrained in NE2). 600s each = 30 min total.
#
# Usage:
#   scripts/ne2_1_inner_sweep.sh [PT_SECONDS] [SEED]
# Defaults: PT_SECONDS=600 SEED=3806637746 (0xE2E2E2E2).

set -euo pipefail

PT_SECONDS="${1:-600}"
SEED="${2:-3806637746}"
FORBIDDEN_PATH="data/forbidden_top6.json"
OUT_DIR="output"
BIN="./target/release/pt_e2"

mkdir -p "$OUT_DIR"

if [[ ! -x "$BIN" ]]; then
    echo "ERROR: $BIN not built."
    exit 1
fi
if [[ ! -f "$FORBIDDEN_PATH" ]]; then
    echo "ERROR: $FORBIDDEN_PATH missing."
    exit 1
fi

# Combined inner-loop + swap-level penalty is ~5-10x stronger than
# swap-only at the same K. Empirical: K=10 combined produced 445 vs
# swap-only K=10 produced 449. Need much smaller K for combined.
KS=(1 2 5)
SUMMARY_PATH="$OUT_DIR/ne2_1_inner_sweep_$(date +%s).json"

echo "[" > "$SUMMARY_PATH.tmp"
FIRST=1

for K in "${KS[@]}"; do
    LOG="/tmp/ne2_1_k${K}_seed${SEED}.log"
    echo "=== NE2.1 inner-loop K=$K seed=$SEED pt_seconds=$PT_SECONDS ===" | tee -a "$LOG"
    date | tee -a "$LOG"

    $BIN \
        --cp-seconds 30 \
        --pt-seconds "$PT_SECONDS" \
        --skip-sa-compare \
        --seed "$SEED" \
        --forbidden-edges "$FORBIDDEN_PATH" \
        --forbidden-k "$K" \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|best_board fmm|Report:)" || true

    LAST_JSON=$(ls -t "$OUT_DIR"/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -z "$LAST_JSON" ]]; then continue; fi

    if [[ "$FIRST" -eq 0 ]]; then echo "," >> "$SUMMARY_PATH.tmp"; fi
    FIRST=0
    cat >> "$SUMMARY_PATH.tmp" <<EOF
  {"K": $K, "seed": "$SEED", "pt_seconds": $PT_SECONDS, "json_path": "$LAST_JSON"}
EOF
done

echo "]" >> "$SUMMARY_PATH.tmp"
mv "$SUMMARY_PATH.tmp" "$SUMMARY_PATH"
echo "===== NE2.1 sweep complete ====="
echo "summary index: $SUMMARY_PATH"
echo "compare to NE2 swap-only sweep using:"
echo "  python3 scripts/ne2_analyze.py $SUMMARY_PATH"
