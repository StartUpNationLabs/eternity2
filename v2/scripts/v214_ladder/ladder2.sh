#!/bin/zsh
# LADDER run-2 (overnight): deficit-scored promotion (CLIMB lesson:
# d146→451 beat d153→448 — health > depth), content dedup, pin
# depth−35, wider probe pool, 600 s finals.
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
PUZ=../data/puzzles/size_16_official_eternity.csv
N=${1:-304}
ROOT=output/vol-214/ladder2_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

gates_for() {
  python3 -c "
k=$1
print(','.join(str(int(k+2+i*(182-k-2)/13)) for i in range(14)))"
}

echo "=== rung 1: $N x 5 s probes ==="
$BIN --mode dfs --frame $FRAME --hints --exact-tail 0 \
  --save-prefix --abort-below 100:2000000 \
  --seeds $N --seed0 50000 --budget-ms 5000 --restart-ms 5000 --threads 8 \
  --out-root $ROOT
R1=$(ls -td $ROOT/cloister2_dfs_* | head -1)

echo "=== rank: depth - 2*deficit, dedup, diversity ==="
python3 scripts/v214_ladder/ladder_rank2.py $PUZ $FRAME $R1 \
  --k 12 --lam 2 --maxov 0.8 | tee $ROOT/rung2.txt

echo "=== rung 2: 30 s x 4 each ==="
while read PF K D DF; do
  TAG=$(basename $PF .json)
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$(gates_for $K)" \
    --seeds 4 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r2_$TAG
done < $ROOT/rung2.txt

echo "=== rung 3: top-3 by best total, 600 s x 8 ==="
python3 - "$ROOT" << 'EOF' | tee $ROOT/rung3.txt
import csv, sys, glob, os
root = sys.argv[1]
best = []
for line in open(root + '/rung2.txt'):
    pf, k = line.split()[:2]
    tag = os.path.basename(pf)[:-5]
    tot = 0
    for d in glob.glob(f'{root}/r2_{tag}/cloister2_dfs_*'):
        rows = list(csv.DictReader(open(d + '/summary.tsv'), delimiter='\t'))
        tot = max([tot] + [int(r['total']) for r in rows if r['breaks'] != '-'])
    best.append((tot, pf, k))
best.sort(reverse=True)
for t, pf, k in best[:3]:
    print(pf, k, t)
EOF
while read PF K T; do
  TAG=$(basename $PF .json)
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$(gates_for $K)" \
    --seeds 8 --budget-ms 600000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r3_$TAG
done < $ROOT/rung3.txt
echo "=== ladder2 done: $ROOT ==="
