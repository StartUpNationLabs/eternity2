#!/usr/bin/env bash
# Vol-80 — sweep alternative Blackwood heuristic-triples.
#
# Per docs/community-mining/09_Blackwood_solver_thread.md, Blackwood's
# 470-attempt schedule used a DIFFERENT triple than his 469 solver,
# with rationale "lots of overlap" between the chosen colors. We have
# only ever tested the auto-picked default (12, 13, 14) which ranks
# 28/165 by overlap in our color encoding. This script tests the top-
# overlap triples + control.
#
# Results vary by triple, so each runs with the same seed and budgets.
# Output dir is timestamped per CLAUDE.md rule 6 (never overwrite).

set -uo pipefail  # NOT -e — we want to continue on individual failures

cd "$(dirname "$0")/.."

# Build once
source $HOME/.cargo/env
cargo build --release -p eternity2-bench-audit --bin run_e2_blackwood 2>&1 | tail -1

TS=$(date +%Y%m%dT%H%M%S)
OUT="output/vol-80-triple-sweep-${TS}"
mkdir -p "$OUT"

declare -a TRIPLES=(
  "14,18,20"    # rank 1 overlap (top)
  "12,14,20"    # rank 2 overlap
  "13,18,20"    # rank 3 overlap
  "18,20,22"   # rank 4 overlap
  "12,13,14"   # auto default (rank 28)
  "15,16,21"   # rank 162 (anti-overlap)
  "14,15,19"   # rank 165 (bottom overlap)
)

CP_MS=60000
ALNS_MS=60000
SEED=1

echo "Vol-80 sweep: ${#TRIPLES[@]} triples × ${CP_MS}ms CP + ${ALNS_MS}ms ALNS = ~$((${#TRIPLES[@]} * 2)) min total" | tee "$OUT/README.txt"
echo "Output: $OUT" | tee -a "$OUT/README.txt"
echo "Date: $(date)" | tee -a "$OUT/README.txt"
echo "---" | tee -a "$OUT/README.txt"

for TRIPLE in "${TRIPLES[@]}"; do
  SAFE=$(echo "$TRIPLE" | tr ',' '_')
  LOG="$OUT/triple_${SAFE}.log"
  echo "[$(date +%H:%M:%S)] running triple=${TRIPLE} -> $LOG" | tee -a "$OUT/README.txt"

  E2_HEURISTIC_SIDES_OVERRIDE="$TRIPLE" \
    target/release/run_e2_blackwood \
      --cp-budget-ms $CP_MS \
      --alns-budget-ms $ALNS_MS \
      --seed $SEED \
      --arms blackwood \
      --schedule calibrated_v17a \
      > "$LOG" 2>&1

  SUMMARY=$(grep -E "^\s+blackwood" "$LOG" | tail -1)
  echo "    -> $SUMMARY" | tee -a "$OUT/README.txt"
done

echo "" | tee -a "$OUT/README.txt"
echo "=== FINAL RANKING ===" | tee -a "$OUT/README.txt"
for TRIPLE in "${TRIPLES[@]}"; do
  SAFE=$(echo "$TRIPLE" | tr ',' '_')
  LOG="$OUT/triple_${SAFE}.log"
  SUMMARY=$(grep -E "^\s+blackwood" "$LOG" | tail -1 | sed -E 's/^\s+//')
  echo "  triple=$TRIPLE  $SUMMARY" | tee -a "$OUT/README.txt"
done
