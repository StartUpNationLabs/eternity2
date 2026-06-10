#!/bin/bash
# vol-211 ALTERNATING PROJECTIONS: interior SA <-> exact border MIP.
# Each round: (1) exact border attach to current interior; (2) interior SA
# with position-exact rim targets from that border (lambda=1 = true IB
# exchange rate); next round re-attaches. Monotone in best total by
# keep-best. Usage: alternate.sh <interior.json> <rounds> [hinted=1]
set -u
cd "$(dirname "$0")/../.." || exit 1
B="$1"; ROUNDS="${2:-3}"; HINTED="${3:-1}"
HFLAG=""; [ "$HINTED" = "1" ] && HFLAG="--hints"
TS=$(date +%Y%m%dT%H%M%S)
LOG=output/vol-211/alternate_${TS}.log
{
echo "=== alternate $TS start=$B rounds=$ROUNDS hinted=$HINTED"
for R in $(seq 1 "$ROUNDS"); do
  echo "--- round $R: border attach"
  OUT=$(./target/release/cloister_border "$B" --time-limit-secs 90 2>&1)
  echo "$OUT" | grep -E "border-attach:|saved"
  A=$(echo "$OUT" | grep "^saved " | awk '{print $2}')
  [ -z "$A" ] && { echo "ATTACH FAILED"; break; }
  echo "--- round $R: interior SA with rim targets"
  SAOUT=$(./target/release/cloister --mode sa --seeds 8 --budget-ms 120000 \
    $HFLAG --rim-lambda 1.0 --t0 0.6 --init-board "$B" --border-board "$A" 2>&1)
  echo "$SAOUT" | grep -E "^seed|^sa \(|saved"
  DIR=$(echo "$SAOUT" | grep "^saved " | head -1 | awk '{print $2}' | xargs dirname)
  # pick best seed by II + rim-target matches from summary.tsv
  BESTROW=$(awk -F'\t' 'NR>1 {print $2+$3, $1, $2}' "$DIR/summary.tsv" | sort -rn | head -1)
  SEED=$(echo "$BESTROW" | awk '{print $2}')
  IIB=$(echo "$BESTROW" | awk '{print $3}')
  B="$DIR/BEST_II${IIB}_seed${SEED}.json"
  echo "round $R best: score=$(echo "$BESTROW" | awk '{print $1}') II=$IIB seed=$SEED -> $B"
done
echo "--- final attach + verify"
OUT=$(./target/release/cloister_border "$B" --time-limit-secs 300 2>&1)
echo "$OUT" | grep -E "border-attach:|saved"
A=$(echo "$OUT" | grep "^saved " | awk '{print $2}')
[ -n "$A" ] && ./target/release/verify_board "$A"
echo "=== alternate done"
} > "$LOG" 2>&1
echo "$LOG"
