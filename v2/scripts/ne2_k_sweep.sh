#!/usr/bin/env bash
# NE2 K-sweep: forbidden-mismatch constrained PT vs unconstrained baseline.
#
# Sweeps K ∈ {0, 10, 50, 100, 200} at fixed seed and fixed PT budget.
# K=0 is the unconstrained baseline. Writes a sweep summary to
# output/ne2_k_sweep_summary.json.
#
# Reads top-6 forbidden edges from data/forbidden_top6.json.
#
# Usage:
#   scripts/ne2_k_sweep.sh [PT_SECONDS] [SEED]
# Defaults: PT_SECONDS=600 SEED=0xE2E2E2E2
#
# Honest experimental design:
#   - Same CP seed → same PT starting basin across K (controls for
#     basin variability).
#   - Same wall-clock budget per K (controls for compute).
#   - K=0 baseline answers "did the penalty help at all".
#   - K-sweep at non-zero values answers "what penalty weight is best".

set -euo pipefail

PT_SECONDS="${1:-600}"
# Default seed: 0xE2E2E2E2 = 3806637746. Use decimal because clap rejects hex.
SEED="${2:-3806637746}"
FORBIDDEN_PATH="data/forbidden_top6.json"
OUT_DIR="output"
BIN="./target/release/pt_e2"

mkdir -p "$OUT_DIR"

if [[ ! -x "$BIN" ]]; then
    echo "ERROR: $BIN not built. Run: cargo build --release -p eternity2-benchmark --bin pt_e2"
    exit 1
fi
if [[ ! -f "$FORBIDDEN_PATH" ]]; then
    echo "ERROR: $FORBIDDEN_PATH missing."
    exit 1
fi

KS=(0 10 50 100 200)
SUMMARY_PATH="$OUT_DIR/ne2_k_sweep_$(date +%s).json"

# Per-K results array, built incrementally.
echo "[" > "$SUMMARY_PATH.tmp"
FIRST=1

for K in "${KS[@]}"; do
    LOG="/tmp/ne2_k${K}_seed${SEED}.log"
    echo "=== NE2 K=$K seed=$SEED pt_seconds=$PT_SECONDS ===" | tee -a "$LOG"
    date | tee -a "$LOG"

    EXTRA_ARGS=()
    if [[ "$K" -gt 0 ]]; then
        EXTRA_ARGS=(--forbidden-edges "$FORBIDDEN_PATH" --forbidden-k "$K")
    fi

    # Note: we shorten CP to 30s — the canonical seed's CP basin is
    # stable; longer CP doesn't help since we want PT to do the work.
    $BIN \
        --cp-seconds 30 \
        --pt-seconds "$PT_SECONDS" \
        --skip-sa-compare \
        --seed "$SEED" \
        "${EXTRA_ARGS[@]}" \
        2>&1 | tee -a "$LOG" | grep -E "(SUMMARY|PT done|best_board fmm|Report:)" || true

    # Extract result (most recent pt_e2 JSON file).
    LAST_JSON=$(ls -t "$OUT_DIR"/pt_e2_*.json 2>/dev/null | head -1)
    if [[ -z "$LAST_JSON" ]]; then
        echo "WARN: no pt_e2 JSON found for K=$K"
        continue
    fi

    if [[ "$FIRST" -eq 0 ]]; then echo "," >> "$SUMMARY_PATH.tmp"; fi
    FIRST=0
    cat >> "$SUMMARY_PATH.tmp" <<EOF
  {"K": $K, "seed": "$SEED", "pt_seconds": $PT_SECONDS, "json_path": "$LAST_JSON"}
EOF
done

echo "]" >> "$SUMMARY_PATH.tmp"
mv "$SUMMARY_PATH.tmp" "$SUMMARY_PATH"
echo "===== sweep complete ====="
echo "summary index: $SUMMARY_PATH"
echo "per-K best scores:"
for K in "${KS[@]}"; do
    # crude extraction
    LAST_JSON=$(ls -t "$OUT_DIR"/pt_e2_*.json 2>/dev/null | head -$((${#KS[@]} - $(printf '%s\n' "${KS[@]}" | grep -n "^$K$" | cut -d: -f1) + 1)) | tail -1)
    echo "  K=$K  → $(grep -o '"matched_edges":[0-9]*' "$LAST_JSON" 2>/dev/null | head -1)"
done
