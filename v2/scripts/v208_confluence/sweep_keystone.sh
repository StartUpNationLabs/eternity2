#!/usr/bin/env bash
# KEYSTONE multi-day structured sweep (vol-208).
# Systematic NOVEL-BASIN generation (NOT basin-reseeding): diverse from-scratch
# KEYRING(+LODESTONE) constructions × scan-orders × seeds × stochastic-temp →
# ALNS-lift each → all results land in output/v17_alns_only/ (alns_only's own
# collision-safe timestamped+pid naming). A separate Python collector
# (collect_keystone.py) scores/verifies/computes cp+novelty afterward.
# Targets new-cp ≥460 (open challenge #1). 8-way parallel, checkpointed.
#
# Usage: scripts/v208_confluence/sweep_keystone.sh [N_SEEDS_PER_CELL] [ALNS_MIN]
set -u
cd "$(dirname "$0")/../.." || exit 1
source "$HOME/.cargo/env" 2>/dev/null
# 8-cores-max directive: alns_only's CP-repair uses rayon's global pool (default =
# ncpu threads/process). With JOBS=8 that oversubscribes 8x (load ~64+). Force each
# process to 1 internal thread so JOBS parallel boards = exactly JOBS cores.
export RAYON_NUM_THREADS=1

NSEEDS="${1:-30}"
ALNS_MIN="${2:-30}"
KEYRING_MS=120000
ALNS_MS=$(( ALNS_MIN * 60 * 1000 ))
PRIOR="scripts/v208_confluence/output/lodestone_prior.json"
TAG="$(date +%Y%m%dT%H%M%S)"
OUT="output/v208_keystone_${TAG}"
mkdir -p "$OUT/boards"
HIST="$OUT/construct_log.csv"
echo "ts,scan,temp,seed,construct_score,board_path" > "$HIST"
echo "[KEYSTONE] tag=$TAG out=$OUT nseeds=$NSEEDS alns_min=$ALNS_MIN alns_dir=output/v17_alns_only" | tee "$OUT/config.txt"

SCANS=(row col zigzag zigzag_rev spiral_in spiral_out row_rev col_rev)
TEMPS=(0.0 0.3)
JOBS=8

run_one() {
  local scan="$1" temp="$2" seed="$3"
  local bpath="$OUT/boards/k_${scan}_t${temp}_s${seed}.json"
  if [ ! -s "$bpath" ]; then
    local sargs=""
    if [ "$temp" != "0.0" ]; then sargs="--stochastic-temperature $temp"; fi
    ./target/release/v181_keyring --beam-width 512 --budget-ms "$KEYRING_MS" \
      --scan "$scan" --seed "$seed" --prior-file "$PRIOR" --prior-alpha 0.001 \
      $sargs --save-best "$bpath" >/dev/null 2>&1
  fi
  [ -s "$bpath" ] || { echo "[fail-construct] $scan $temp $seed"; return; }
  local cscore
  cscore=$(./target/release/rescore_board "$bpath" 2>/dev/null | tail -1 | awk -F'\t' '{print $3}')
  echo "$(date +%Y%m%dT%H%M%S),$scan,$temp,$seed,$cscore,$bpath" >> "$HIST"
  # ALNS lift — alns_only writes its own collision-safe file into output/v17_alns_only/.
  # The board_path is embedded? No — so we tag via a side marker file named by board.
  ./target/release/alns_only --cp-board "$bpath" --alns-budget-ms "$ALNS_MS" \
    --seed 42 --ops basic >/dev/null 2>&1
  echo "[done] scan=$scan temp=$temp seed=$seed construct=$cscore"
}
export -f run_one
export OUT PRIOR KEYRING_MS ALNS_MS HIST

for scan in "${SCANS[@]}"; do
  for temp in "${TEMPS[@]}"; do
    for seed in $(seq 1 "$NSEEDS"); do
      echo "$scan $temp $seed"
    done
  done
done | xargs -P "$JOBS" -n 3 bash -c 'run_one "$0" "$1" "$2"'

echo "[KEYSTONE] sweep complete."
