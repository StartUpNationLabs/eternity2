#!/bin/zsh
# census-2: the 50 generated frames again, but each with ITS OWN
# choke-derived gate schedule (budget 16, floor 100) from the census-1
# profiles — the choke instrument composed with the frame generator.
# et14 + et-cap (tail2's fixed trigger may sit above a frame's reach).
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
SRC=${1:?census-1 run dir with choke_genNNNN.tsv}
FRAMES=output/vol-213/frames_census50

for CH in $SRC/choke_gen*.tsv; do
  G=$(basename $CH .tsv); G=${G#choke_}
  $BIN --mode dfs --frame $FRAMES/$G.json \
    --hints --exact-tail 14 --et-cap 100000000 \
    --schedule-from-choke $CH,16,100 \
    --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213/census2
done
echo "census2 done"
