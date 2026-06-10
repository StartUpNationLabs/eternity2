#!/bin/zsh
# CLIMB (vol-214): recursive LADDER — each round probes beyond the
# previous round's deepest banked perfect prefix (pinned at depth-15),
# ratcheting the perfect-prefix frontier. Witnesses prove perfect-171
# exists on strict460a (admits 460). Stop when a round gains < 4 depth.
# Finish: et14 rungs (300 s x 8) from the 3 deepest distinct prefixes.
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
ROUNDS=${1:-8}
N=${2:-104}
ROOT=output/vol-214/climb_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

CUR=""
K=0
BESTD=0
for R in $(seq 1 $ROUNDS); do
  echo "=== climb round $R (from depth $BESTD) ==="
  EXTRA=()
  [ -n "$CUR" ] && EXTRA=(--init-prefix $CUR:$K)
  $BIN --mode dfs --frame $FRAME --hints --exact-tail 0 \
    --save-prefix --abort-below 100:2000000 $EXTRA \
    --seeds $N --seed0 $((R * 1000)) \
    --budget-ms 5000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/round$R
  RD=$(ls -td $ROOT/round$R/cloister2_dfs_* | head -1)
  BEST=$(ls $RD/prefix_d*.json | sed 's/.*prefix_d\([0-9]*\)_.*/\1 &/' | sort -rn | head -1)
  D=${BEST%% *}
  F=${BEST#* }
  echo "round $R deepest: d$D ($F)"
  if [ "$D" -lt $((BESTD + 4)) ]; then
    echo "frontier stalled (d$D vs d$BESTD) — stopping climb"
    break
  fi
  BESTD=$D
  CUR=$F
  K=$((D - 15))
done

echo "=== finish: et14 from the 3 deepest distinct prefixes ==="
ls $ROOT/round*/cloister2_dfs_*/prefix_d*.json \
  | sed 's/.*prefix_d\([0-9]*\)_.*/\1 &/' | sort -rn | head -3 | while read D F; do
  PK=$((D - 15))
  GATES=$(python3 -c "
k=$PK
print(','.join(str(int(k+2+i*(182-k-2)/13)) for i in range(14)))")
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $F:$PK --break-schedule "$GATES" \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/finish_d$D
done
echo "=== climb done: $ROOT ==="
