#!/bin/zsh
# Vol-217 stage-4 frontier census: collect banked stage-3 states
# (perfect rows 0-11), dedup at rows<12, then ask rows 12-14
# (tropical floor, then counting + bottom-chain on the best tier).
# Usage: run_stage4_census.sh S3_ROOT
set -e
cd "$(dirname "$0")/../.."
R=$1
ORACLE=./target/release/fb_oracle
PUZ=../data/puzzles/size_16_official_eternity.csv

# wait for banking completion marker in the launch log
until grep -q "stage3 banking done" $R.launch.log 2>/dev/null; do sleep 20; done

ALL=$R/all_s3
mkdir -p $ALL
# flatten: copy snapshots with run-tag prefixes (cheap hardlinks)
for d in $R/s3_*; do
  tag=$(basename $d)
  for f in $d/t*.json(N); do
    ln -f $f $ALL/${tag#s3_}__$(basename $f)
  done
done
ls $ALL | wc -l | xargs echo "banked stage-3 snapshots:"

python3 scripts/v217_crossing/census_driver.py $ALL 12 $R/census12 \
  | tee $R/census12.log

$ORACLE --puzzle $PUZ --rows 12 --k 3 --truncate-rows 12 --floor-only --cap 6 \
  --batch $R/census12.list --threads 8 --out $R/floors12.tsv
awk -F'\t' 'NR>1 {n[$3]++} END {for (k in n) print "s4floor", k, n[k]}' \
  $R/floors12.tsv | sort -k2 | tee -a $R/census12.log

# counting + bottom-chain on the best two floor tiers present
BEST=$(awk -F'\t' 'NR>1 && $3>=0 {print $3}' $R/floors12.tsv | sort -n | head -1)
awk -F'\t' -v b=$BEST 'NR>1 && ($3==b || $3==b+1) {print $1}' $R/floors12.tsv > /tmp/s4_tags
awk 'NR==FNR {want[$1]=1; next} {tag=$0; sub(/.*\//,"",tag); sub(/\.json$/,"",tag); if (want[tag]) print}' \
  /tmp/s4_tags $R/census12.list > $R/counting12.list
wc -l $R/counting12.list
$ORACLE --puzzle $PUZ --rows 12 --k 3 --truncate-rows 12 --bmax 16 --bottom-chain \
  --batch $R/counting12.list --threads 8 --out $R/census12_counts.tsv
echo "=== stage-4 census done ==="
