#!/bin/zsh
# ladder4: empirical promotion (rung-2 races are the signal; static
# scores demoted to tie-breaks after two strikes), incumbent lane, and
# the within-prefix variance control.
#  A. incumbent control: run-1's 451-producer (d146-seed63) at
#     600 s x 8 — was 451 prefix-specific or a lottery draw?
#  B. wide empirical rung 2: top-24 by depth (dedup + diversity) from
#     ALL banked prefixes, 30 s x 4 -> top-3 by measured total,
#     600 s x 8 each
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json
PUZ=../data/puzzles/size_16_official_eternity.csv
ROOT=output/vol-214/ladder4_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT

gates_for() {
  python3 -c "
k=$1
nb=min(14, max(12, round((182-k)/3.5)))
print(','.join(str(int(k+2+i*(182-k-2)/(nb-1))) for i in range(nb)))"
}

echo "=== A. incumbent control: d146-seed63 @ 600 s x 8 ==="
INC=output/vol-214/ladder_20260610T212732/cloister2_dfs_20260610T212732/prefix_d146_strict460a_seed63.json
$BIN --mode dfs --frame $FRAME --hints \
  --exact-tail 14 --et-cap 100000000 \
  --init-prefix $INC:131 --break-schedule "$(gates_for 131)" \
  --seeds 8 --budget-ms 600000 --restart-ms 5000 --threads 8 \
  --out-root $ROOT/incumbent

echo "=== B. wide empirical rung 2 (top-24 by depth, lam 0) ==="
python3 scripts/v214_ladder/ladder_rank2.py $PUZ $FRAME \
  output/vol-214/ladder_*/cloister2_dfs_* \
  output/vol-214/ladder2_*/cloister2_dfs_* \
  output/vol-214/climb_*/round*/cloister2_dfs_* \
  --k 24 --lam 0 --maxov 0.85 | tee $ROOT/rung2.txt
while read PF K D DF; do
  TAG=$(basename $PF .json)
  $BIN --mode dfs --frame $FRAME --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K --break-schedule "$(gates_for $K)" \
    --seeds 4 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root $ROOT/r2_$TAG
done < $ROOT/rung2.txt
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
best.sort(key=lambda x: -x[0])
for t, pf, k in [b for b in best if b[0] > 0][:3]:
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
echo "=== ladder4 done: $ROOT ==="
