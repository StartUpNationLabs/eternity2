#!/bin/zsh
# Vol-217 binding 2: race crossing-ranked banked prefixes at the
# rung-3 config (ladder.sh vol-214): et14, gates evenly spread in
# (K+2, 182], K = depth-15, 300 s x 8 seeds. threads 7 to leave a dev
# core. Input TSV lines: prefix_file<TAB>frame<TAB>depth
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
LIST=$1
ROOT=output/vol-217/race_topk_$(date -u +%Y%m%dT%H%M%S)
mkdir -p $ROOT
cp $LIST $ROOT/list.tsv

frame_path() {
  case $1 in
    strict460a) echo output/vol-212/frames_best/strict460a.json;;
    strict460b) echo output/vol-212/frames_best/strict460b.json;;
    gen0143)    echo output/vol-213/frames_census50/gen0143.json;;
  esac
}

gates_for() {
  python3 -c "
k=$1
print(','.join(str(int(k+2+i*(182-k-2)/13)) for i in range(14)))"
}

while IFS=$'\t' read PF FRAME DEPTH; do
  [[ -z "$PF" ]] && continue
  TAG=$(basename $PF .json)
  K=$((DEPTH-15))
  echo "=== $TAG (K=$K, frame=$FRAME) ==="
  $BIN --mode dfs --frame $(frame_path $FRAME) --hints \
    --exact-tail 14 --et-cap 100000000 \
    --init-prefix $PF:$K \
    --break-schedule "$(gates_for $K)" \
    --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 7 \
    --out-root $ROOT/race_$TAG
done < $LIST
echo "=== races done: $ROOT ==="
