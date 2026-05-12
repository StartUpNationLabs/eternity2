#!/bin/bash
# Launch 8 BP/SP-decimation runs in parallel on different cores.
# Each writes its own JSON to output/v11_sp/sweep_<idx>.json.

set -e
cd "$(dirname "$0")/.."

OUT=output/v11_sp
mkdir -p $OUT
rm -f $OUT/sweep_*.json $OUT/sweep_*.log

# (damping, batch_size, m_parisi, seed)
# Vary damping, batch, m to map the landscape.
CONFIGS=(
  "0.10 1 1.0 1"     # BP, tiny batch, low damping
  "0.30 1 1.0 2"     # BP, tiny batch, default damping
  "0.50 1 1.0 3"     # BP, tiny batch, high damping
  "0.30 4 1.0 4"     # BP, medium batch
  "0.30 8 1.0 5"     # BP, large batch
  "0.30 1 0.5 6"     # SP, tiny batch
  "0.30 1 0.3 7"     # SP-y (max clusters), tiny batch
  "0.30 4 0.8 8"     # SP, medium batch
)

i=0
for cfg in "${CONFIGS[@]}"; do
  read damping batch m_parisi seed <<< "$cfg"
  out_path=$OUT/sweep_$i.json
  log_path=$OUT/sweep_$i.log
  echo "[$i] damping=$damping batch=$batch m=$m_parisi seed=$seed -> $out_path"
  python3 -u scripts/v11_bp_dec_sweep.py $damping $batch $m_parisi $seed $out_path > $log_path 2>&1 &
  i=$((i+1))
done

echo
echo "Launched $i runs. Waiting..."
wait
echo
echo "=== Summary ==="
for i in $(seq 0 7); do
  if [ -f $OUT/sweep_$i.json ]; then
    python3 -c "
import json
d = json.load(open('$OUT/sweep_$i.json'))
c = d['config']
print(f'[{$i}] damp={c[\"damping\"]:.2f} bs={c[\"batch_size\"]:>2d} m={c[\"m_parisi\"]:.2f} seed={c[\"seed\"]:>2d}  '
      f'depth={d[\"max_depth_reached\"]:>4d} score={d[\"best_score\"]:>4d}  '
      f'contradiction={d[\"contradiction\"]} t={d[\"wall_clock_s\"]:.1f}s')
"
  fi
done
