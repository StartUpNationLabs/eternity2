#!/bin/zsh
# Vol-217 census-2 (clean, two-pass): dedup -> tropical floor pass on
# everything -> counting pass (+bottom-chain) on floor<=1 plus samples
# of floor 2 and 3 for strata. Waits for the generator to exit first.
set -e
cd "$(dirname "$0")/../.."
D=$1
ORACLE=./target/release/fb_oracle
PUZ=../data/puzzles/size_16_official_eternity.csv

# wait on the generator's own completion marker (NOT pgrep-on-name —
# standing discipline): the final stats JSON line in its gen.log
until grep -q "placements_per_sec" $D/gen.log 2>/dev/null; do sleep 15; done

python3 scripts/v217_crossing/census_driver.py $D 8 $D/census8 | tee $D/census2.log

echo "=== tropical floor pass ===" | tee -a $D/census2.log
$ORACLE --puzzle $PUZ --rows 8 --k 3 --truncate-rows 8 --floor-only --cap 3 \
  --batch $D/census8.list --threads 8 --out $D/floors.tsv
awk -F'\t' 'NR>1 {n[$3]++} END {for (k in n) print "floor", k, n[k]}' \
  $D/floors.tsv | sort -k2 | tee -a $D/census2.log

echo "=== counting pass on floor<=1 + strata samples ===" | tee -a $D/census2.log
awk -F'\t' 'NR>1 && ($3==0 || $3==1) {print $1}' $D/floors.tsv > /tmp/c2_tags
awk -F'\t' 'NR>1 && $3==2 {print $1}' $D/floors.tsv | head -200 >> /tmp/c2_tags
awk -F'\t' 'NR>1 && ($3==3 || $3==-1) {print $1}' $D/floors.tsv | head -200 >> /tmp/c2_tags
awk -v d=$D 'NR==FNR {want[$1]=1; next} {tag=$0; sub(/.*\//,"",tag); sub(/\.json$/,"",tag); if (want[tag]) print}' \
  /tmp/c2_tags $D/census8.list > $D/counting.list
wc -l $D/counting.list | tee -a $D/census2.log
$ORACLE --puzzle $PUZ --rows 8 --k 3 --truncate-rows 8 --bmax 8 --bottom-chain \
  --batch $D/counting.list --threads 8 --out $D/census_counts.tsv
echo "=== census-2 done ===" | tee -a $D/census2.log
