#!/usr/bin/env bash
# V158 — V155 variant sweep: 8 different V155 configurations in parallel.
# Run AFTER ALNS finishes (when CPU is free).
#
# Variants explore different (K, prior, scan, dedup) configurations to
# see if any breaks the 456 ceiling.

set -u

OUT_DIR=output/vol-158/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT_DIR"

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

# Ensure both priors exist (regenerate if missing).
if [ ! -f scripts/v155_prior/prior_matrix.json ]; then
  uv run python scripts/v155_prior/build_prior.py --threshold 440 >/dev/null
fi
if [ ! -f scripts/v155_prior/prior_matrix_high459.json ]; then
  uv run python scripts/v155_prior/build_prior.py --threshold 459 >/dev/null
  mv scripts/v155_prior/prior_matrix.json scripts/v155_prior/prior_matrix_high459.json
  uv run python scripts/v155_prior/build_prior.py --threshold 440 >/dev/null
fi

PRIOR_440=scripts/v155_prior/prior_matrix.json
PRIOR_459=scripts/v155_prior/prior_matrix_high459.json
PRIOR_ROT=scripts/v155_prior/prior_matrix_with_rot.json

declare -a JOBS=(
  # 1: baseline reproduction (sanity check; should give 456)
  "v155_weaving_prior --beam-width 4096 --prior-file $PRIOR_440 --dedup-path --dedup-recent 4"
  # 2: K=16384 + 2D-prior + path-dedup-8
  "v155_weaving_prior --beam-width 16384 --prior-file $PRIOR_440 --dedup-path --dedup-recent 8"
  # 3: K=16384 + high459-prior + path-dedup-8 (sharper signal)
  "v155_weaving_prior --beam-width 16384 --prior-file $PRIOR_459 --dedup-path --dedup-recent 8"
  # 4: K=4096 + 2D-prior + col-major scan
  "v155_weaving_prior --beam-width 4096 --prior-file $PRIOR_440 --dedup-path --dedup-recent 4 --scan col"
  # 5: K=8192 + rotation-aware prior + path-dedup-4
  "v157_weaving_prior_rot --beam-width 8192 --prior-file $PRIOR_ROT --dedup-path --dedup-recent 4"
  # 6: K=8192 + 2D-prior + path-dedup-4 + alpha=0.05 (blend)
  "v155_weaving_prior --beam-width 8192 --prior-file $PRIOR_440 --dedup-path --dedup-recent 4 --prior-alpha 0.05"
  # 7: K=4096 + 2D-prior + path-dedup-16 (wide diversity)
  "v155_weaving_prior --beam-width 4096 --prior-file $PRIOR_440 --dedup-path --dedup-recent 16"
  # 8: K=16384 + rotation-aware prior + path-dedup-8 (big sharp config)
  "v157_weaving_prior_rot --beam-width 16384 --prior-file $PRIOR_ROT --dedup-path --dedup-recent 8"
)

echo "[v158] launching ${#JOBS[@]} variants in $OUT_DIR" | tee "$OUT_DIR/_meta.log"
echo "[v158] expected total time: 5-15min wall (each variant 2-10min single-thread)" | tee -a "$OUT_DIR/_meta.log"

for i in "${!JOBS[@]}"; do
  cmd="${JOBS[$i]}"
  log="$OUT_DIR/v$(printf %02d "$i")_$(echo "$cmd" | awk '{print $1}').log"
  best="$OUT_DIR/v$(printf %02d "$i")_best.json"
  echo "[v158] launching #$i: $cmd" | tee -a "$OUT_DIR/_meta.log"
  target/bench-fast/$cmd --save-best "$best" > "$log" 2>&1 &
done

# Wait for all jobs.
wait
echo "[v158] all done." | tee -a "$OUT_DIR/_meta.log"

# Aggregate.
echo "" | tee -a "$OUT_DIR/_meta.log"
echo "Summary:" | tee -a "$OUT_DIR/_meta.log"
for log in "$OUT_DIR"/v*.log; do
  best=$(grep -o '"best_score":[0-9]*' "$log" | head -1 | cut -d: -f2)
  elapsed=$(grep -o '"elapsed_ms":[0-9]*' "$log" | head -1 | cut -d: -f2)
  base=$(basename "$log" .log)
  echo "  $base: best=$best elapsed_ms=$elapsed" | tee -a "$OUT_DIR/_meta.log"
done
