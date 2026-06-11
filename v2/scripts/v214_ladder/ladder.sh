#!/bin/zsh
# LADDER (vol-214): successive-halving prefix racing on bordered+hinted
# strict460a. Band to beat: 444-450 (universal, 55 frames).
#   Rung 1: N x 5 s single-epoch probes, perfect walk, bank prefixes
#   Rung 2: top-12 diverse prefixes (pin depth-15), 30 s x 4 seeds, et14
#   Rung 3: top-3 by rung-2 best total, 300 s x 8 seeds
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=${FRAME:-output/vol-212/frames_best/strict460a.json}
N=${1:-104}
SEED0=${2:-1}
ROOT=output/vol-214/ladder_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

gates_for() {  # evenly spread 14 gates in (K+2, 182]
  python3 -c "
k=$1
print(','.join(str(int(k+2+i*(182-k-2)/13)) for i in range(14)))"
}

echo "=== rung 1: $N x 5 s probes ==="
$BIN --mode dfs --frame $FRAME --hints --exact-tail 0 \
  --save-prefix --abort-below 100:2000000 \
  --seeds $N --seed0 $SEED0 --budget-ms 5000 --restart-ms 5000 --threads 8 \
  --out-root $ROOT
R1=$(ls -td $ROOT/cloister2_dfs_* | head -1)
ls $R1/prefix_d*.json | wc -l | xargs echo "banked prefixes:"

echo "=== rung 2: top-12 diverse, 30 s x 4 each ==="
python3 scripts/v214_ladder/ladder_rank.py $R1 12 0.8 | tee $ROOT/rung2.txt
while read PF K; do
  TAG=$(basename $PF .json)
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K \
    --break-schedule "$(gates_for $K)" \
    --seeds 4 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r2_$TAG
done < $ROOT/rung2.txt

echo "=== rung 3: top-3, 300 s x 8 each ==="
python3 - "$ROOT" << 'EOF' | tee $ROOT/rung3.txt
import csv, sys, glob, os
root = sys.argv[1]
best = []
for line in open(root + '/rung2.txt'):
    pf, k = line.split()
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
    --init-prefix $PF:$K \
    --break-schedule "$(gates_for $K)" \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r3_$TAG
done < $ROOT/rung3.txt
echo "=== ladder done: $ROOT ==="
