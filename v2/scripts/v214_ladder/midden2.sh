#!/bin/zsh
# MIDDEN v2: hybrid geometries. v1 finding: dispersed lattice extends
# the perfect-walk wall 153 -> 167-174 (+21) but nothing absorbs the
# endgame; tail rows absorb but can't be reached. Compose them, and
# sweep dispersed density. Budget 20, 300 s x 8 each.
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
ROOT=output/vol-215/midden2_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT
SCHED20=$(python3 -c "print(','.join(['0']*20))")

D7=$(python3 -c "print(','.join(str(i*7) for i in range(28) if i*7 < 168))")
D5=$(python3 -c "print(','.join(str(i*5) for i in range(34) if i*5 < 168))")
D10=$(python3 -c "print(','.join(str(i*10) for i in range(17) if i*10 < 168))")
TAIL="168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195"

for SPEC in "cells:$D7,$TAIL" "cells:$D5,$TAIL" "cells:$D10,$TAIL"; do
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --break-schedule "$SCHED20" --break-cells "$SPEC" \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT
done
echo "=== midden2 done: $ROOT ==="
