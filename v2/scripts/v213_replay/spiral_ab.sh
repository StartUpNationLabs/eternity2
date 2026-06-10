#!/bin/zsh
# vol-213 (user): SPIRAL-IN scan A/B — hinted everywhere (user directive).
#  Leg A: standalone 14x14 (free rim) hinted, spiral vs row-major,
#         et14 + et-cap, no breaks probe first (choke profile), then
#         choke-gated runs. Standalone hinted best to beat: 351.
#  Leg B: bordered (strict460a) hinted: probe -> choke gates -> run,
#         vs row-major tail2 lane (445/446) and choke-et14 (443).
set -e
cd "$(dirname "$0")/../.."
BIN=./target/release/cloister2
FRAME=output/vol-212/frames_best/strict460a.json

echo "=== A1: standalone hinted probes (choke profiles), spiral vs row ==="
for SC in spiral row; do
  $BIN --mode dfs --hints --scan $SC --exact-tail 0 \
    --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
    --out-root output/vol-213/spiral
done
A_SP=$(ls -td output/vol-213/spiral/cloister2_dfs_* | head -2 | tail -1)
A_RW=$(ls -td output/vol-213/spiral/cloister2_dfs_* | head -1)

echo "=== A2: standalone hinted, choke-gated, spiral vs row (60 s x 8) ==="
$BIN --mode dfs --hints --scan spiral --exact-tail 14 --et-cap 100000000 \
  --schedule-from-choke $A_SP/choke_free.tsv,12,60 \
  --seeds 8 --budget-ms 60000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213/spiral
$BIN --mode dfs --hints --scan row --exact-tail 14 --et-cap 100000000 \
  --schedule-from-choke $A_RW/choke_free.tsv,12,60 \
  --seeds 8 --budget-ms 60000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213/spiral

echo "=== B1: bordered hinted spiral probe (choke profile) ==="
$BIN --mode dfs --frame $FRAME --hints --scan spiral --exact-tail 0 \
  --seeds 8 --budget-ms 30000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213/spiral
B_SP=$(ls -td output/vol-213/spiral/cloister2_dfs_* | head -1)

echo "=== B2: bordered hinted spiral, choke-gated et14 (300 s x 8) ==="
$BIN --mode dfs --frame $FRAME --hints --scan spiral \
  --exact-tail 14 --et-cap 100000000 \
  --schedule-from-choke $B_SP/choke_strict460a.tsv,16,40 \
  --seeds 8 --budget-ms 300000 --restart-ms 5000 --threads 8 \
  --out-root output/vol-213/spiral
echo "=== spiral A/B done ==="
