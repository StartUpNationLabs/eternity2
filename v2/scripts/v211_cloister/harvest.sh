#!/bin/bash
# vol-211 harvest: for each interior board given, SA-polish (rim-aware,
# hinted) x 8 seeds, then exact border-attach the polished best, then
# verify_board the assembled result. Usage: harvest.sh <interior.json>...
set -u
cd "$(dirname "$0")/../.." || exit 1
TS=$(date +%Y%m%dT%H%M%S)
LOG=output/vol-211/harvest_${TS}.log
{
echo "=== CLOISTER harvest $TS ==="
for B in "$@"; do
  echo "--- polish: $B"
  ./target/release/cloister --mode sa --seeds 8 --budget-ms 240000 \
    --hints --rim-lambda 1.0 --init-board "$B" --t0 0.8
done
echo "--- border-attach every BEST from the polish runs just produced"
for J in $(ls -t output/vol-211/cloister_sa_*/BEST_II*.json 2>/dev/null | head -24); do
  ./target/release/cloister_border "$J" --time-limit-secs 60
done
echo "--- verify assembled boards"
./target/release/verify_board output/vol-211/border_attach_*/ATTACHED_*.json 2>&1 | tail -30
echo "=== harvest done ==="
} > "$LOG" 2>&1
echo "$LOG"
