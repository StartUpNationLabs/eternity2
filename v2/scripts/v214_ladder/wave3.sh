#!/bin/zsh
# Wave 3 (vols 214-215, overnight):
#  1. ladder3: rank over the UNION of all banked prefixes (prefix
#     capital accumulates across runs), top-3 x 600 s x 8
#  2. MIDDEN geometry sweep (first damage-geometry search ever):
#     witness-shape control vs middle-band vs center-columns vs
#     dispersed lattice, equal budget 20, 300 s x 8 each
#  3. QUOTA A/B on the v1 hinted tail2 lane, 300 s x 8 x 2
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
PUZ=../data/puzzles/size_16_official_eternity.csv
ROOT=output/vol-214/wave3_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

gates_for() {
  python3 -c "
k=$1
nb=min(14, max(12, round((182-k)/3.5)))
print(','.join(str(int(k+2+i*(182-k-2)/(nb-1))) for i in range(nb)))"
}

echo "=== 1. ladder3: union ranking over all banked prefixes ==="
python3 scripts/v214_ladder/ladder_rank2.py $PUZ $FRAME \
  output/vol-214/ladder_*/cloister2_dfs_* \
  output/vol-214/ladder2_*/cloister2_dfs_* \
  output/vol-214/climb_*/round*/cloister2_dfs_* \
  --k 3 --lam 2 --maxov 0.8 | tee $ROOT/ladder3.txt
while read PF K D DF; do
  TAG=$(basename $PF .json)
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$(gates_for $K)" \
    --seeds 8 --budget-ms 600000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/l3_$TAG
done < $ROOT/ladder3.txt

echo "=== 2. MIDDEN geometry sweep (budget 20, gates open) ==="
SCHED20=$(python3 -c "print(','.join(['0']*20))")
DISPERSED=$(python3 -c "print(','.join(str(i*7) for i in range(28)))")
for GEO in "rows:12,13" "rows:6,7" "cols:6,7" "cells:$DISPERSED"; do
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --break-schedule "$SCHED20" --break-cells "$GEO" \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/midden
done

echo "=== 3. QUOTA A/B (v1 hinted tail2 lane) ==="
HSCHED="120,127,134,141,148,155,162,168"
for Q in "" "--quota 96:20:0.25"; do
  $BIN --mode dfs --frame $FRAME --hints \
    --tail2 --tail2-cap 30000 --break-schedule "$HSCHED" ${=Q} \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/quota
done
echo "=== wave3 done: $ROOT ==="
