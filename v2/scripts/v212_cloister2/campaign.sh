#!/bin/zsh
# CLOISTER-II frame-breadth campaign (vol-212).
# Phase 1: hint-compatibility probe (cheap) over a frames dir.
# Phase 2: 30s tail2 recipe over compatible frames, 8 seeds.
# Usage: campaign.sh <frames_dir> [probe_ms] [run_ms]
set -e
FRAMES=${1:?frames dir}
PROBE_MS=${2:-6000}
RUN_MS=${3:-30000}
TS=$(date +%Y%m%dT%H%M%S)
OUT=output/vol-212/campaign_$TS
mkdir -p $OUT/compat
BIN=./target/release/cloister2

echo "== phase 1: hint-compat probe ($PROBE_MS ms x 2 seeds) over $FRAMES =="
$BIN --mode dfs --frame $FRAMES --seeds 2 --budget-ms $PROBE_MS \
  --break-schedule "120,127,134,141,148,155,162,168" --tail2 --hints \
  --threads 8 --out-root $OUT/probe > $OUT/probe.log 2>&1
PROBE_DIR=$(ls -td $OUT/probe/cloister2_dfs_* | head -1)
# compatible = any seed reached depth >= 100 or completed
awk -F'\t' 'NR>1 {d[$1] = ($5>m[$1]) ? $5 : m[$1]; if ($5>m[$1]) m[$1]=$5; if ($8>0) c[$1]=1}
  END {for (f in m) if (m[f] >= 100 || c[f]) print f}' $PROBE_DIR/summary.tsv | sort > $OUT/compat.txt
echo "compatible frames: $(wc -l < $OUT/compat.txt)"
while read f; do cp $FRAMES/$f.json $OUT/compat/ 2>/dev/null || true; done < $OUT/compat.txt

echo "== phase 2: $RUN_MS ms x 8 seeds over compatible frames =="
$BIN --mode dfs --frame $OUT/compat --seeds 8 --budget-ms $RUN_MS \
  --break-schedule "120,127,134,141,148,155,162,168" --tail2 --hints \
  --threads 8 --out-root $OUT/run > $OUT/run.log 2>&1
RUN_DIR=$(ls -td $OUT/run/cloister2_dfs_* | head -1)
echo "== per-frame totals (min/med/max) =="
grep "^frame .*: n=" $OUT/run.log | sort -t= -k4 -rn
echo "results: $RUN_DIR"
