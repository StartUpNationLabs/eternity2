#!/bin/zsh
# ladder5 — MIDDEN×LADDER composition: probe WITH dispersed breaks
# (budget 6) to bank imperfect-but-deep prefixes (dispersed walls reach
# 167-174 vs 153 perfect), then finish with the remaining budget
# (schedule = p zeros for the pinned breaks + spread; hybrid midden so
# travel damage stays dispersed and the tail absorbs).
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
PUZ=../data/puzzles/size_16_official_eternity.csv
ROOT=output/vol-215/ladder5_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

D7=$(python3 -c "print(','.join(str(i*7) for i in range(28) if i*7 < 168))")
TAIL=$(python3 -c "print(','.join(str(c) for c in range(168, 196)))")
HYBRID="cells:$D7,$TAIL"

echo "=== probes: dispersed midden, budget 6, bank prefixes ==="
$BIN --mode dfs --frame $FRAME --hints --exact-tail 0 \
  --break-schedule "0,0,0,0,0,0" --break-cells "cells:$D7" \
  --save-prefix --abort-below 110:2000000 \
  --seeds 304 --seed0 70000 --budget-ms 5000 --restart-ms 5000 --threads 8 \
  --out-root $ROOT
R1=$(ls -td $ROOT/cloister2_dfs_* | head -1)

echo "=== rank + finish (budget 20 total: p pinned + spread) ==="
python3 scripts/v214_ladder/ladder_rank2.py $PUZ $FRAME $R1 \
  --k 12 --lam 0 --maxov 0.85 | tee $ROOT/rung2.txt
while read PF K D DF NB; do
  TAG=$(basename $PF .json)
  GATES=$(python3 -c "
k, p = $K, $NB
rest = max(12, min(14, round((182-k)/3.5)))
g = ['0']*p + [str(int(k+2+i*(182-k-2)/(rest-1))) for i in range(rest)]
print(','.join(g))")
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$GATES" --break-cells "$HYBRID" \
    --seeds 4 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r2_$TAG
done < $ROOT/rung2.txt
python3 - "$ROOT" << 'EOF' | tee $ROOT/rung3.txt
import csv, sys, glob, os
root = sys.argv[1]
best = []
for line in open(root + '/rung2.txt'):
    parts = line.split()
    pf, k, nb = parts[0], parts[1], parts[4]
    tag = os.path.basename(pf)[:-5]
    tot = 0
    for d in glob.glob(f'{root}/r2_{tag}/cloister2_dfs_*'):
        rows = list(csv.DictReader(open(d + '/summary.tsv'), delimiter='\t'))
        tot = max([tot] + [int(r['total']) for r in rows if r['breaks'] != '-'])
    best.append((tot, pf, k, nb))
best.sort(key=lambda x: -x[0])
for t, pf, k, nb in [b for b in best if b[0] > 0][:3]:
    print(pf, k, nb, t)
EOF
while read PF K NB T; do
  TAG=$(basename $PF .json)
  GATES=$(python3 -c "
k, p = $K, $NB
rest = max(12, min(14, round((182-k)/3.5)))
g = ['0']*p + [str(int(k+2+i*(182-k-2)/(rest-1))) for i in range(rest)]
print(','.join(g))")
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$GATES" --break-cells "$HYBRID" \
    --seeds 8 --budget-ms 600000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r3_$TAG
done < $ROOT/rung3.txt
echo "=== ladder5 done: $ROOT ==="
