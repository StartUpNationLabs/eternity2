#!/usr/bin/env bash
# Vol-125 T7 — sweep bf_bw partials with multi-seed ALNS basic.
#
# For each bf_bw partial in output/vol-125/bf_bw_pipeline/, run ALNS basic
# at given budget for each seed. Logs to output/vol-125/bfbw_alns_${RUN_TAG}/.
set -euo pipefail

ALNS_MS="${1:-1800000}"   # default 30 min
SEEDS_CSV="${2:-42}"
PARALLEL="${3:-3}"        # number of concurrent ALNS jobs

RUN_TAG="${RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
OUT_DIR="output/vol-125/bfbw_alns_${RUN_TAG}"
mkdir -p "$OUT_DIR/logs"
echo "[bfbw sweep] tag=$RUN_TAG  alns_ms=$ALNS_MS  seeds=$SEEDS_CSV  parallel=$PARALLEL" | tee "$OUT_DIR/INFO"

IFS=',' read -ra SEEDS <<< "$SEEDS_CSV"

# Collect (partial, seed) pairs
JOBS_FILE="$OUT_DIR/jobs.tsv"
> "$JOBS_FILE"
for PARTIAL in output/vol-125/bf_bw_pipeline/seed*_partial.json; do
    PNAME=$(basename "$PARTIAL" _partial.json)
    for SEED in "${SEEDS[@]}"; do
        OUTLOG="$OUT_DIR/logs/${PNAME}_alns_s${SEED}.log"
        if [[ -f "$OUTLOG.done" ]]; then continue; fi
        echo -e "${PARTIAL}\t${SEED}\t${OUTLOG}" >> "$JOBS_FILE"
    done
done

N_JOBS=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "[bfbw sweep] $N_JOBS jobs queued"

# Run with bounded parallelism (simple background-job pool)
RUNNING=0
while IFS=$'\t' read -r PARTIAL SEED OUTLOG; do
    PNAME=$(basename "$PARTIAL" _partial.json)
    echo "[$(date +%H:%M:%S)] $PNAME seed=$SEED" >> "$OUT_DIR/PROGRESS"
    (
        ./target/bench-fast/alns_only --cp-board "$PARTIAL" \
            --alns-budget-ms "$ALNS_MS" --seed "$SEED" --ops basic > "$OUTLOG" 2>&1
        BEST=$(grep -oE "matched=[0-9]+" "$OUTLOG" | tail -1 || echo "?")
        echo "[$(date +%H:%M:%S)] $PNAME seed=$SEED -> $BEST" >> "$OUT_DIR/PROGRESS"
        touch "$OUTLOG.done"
    ) &
    RUNNING=$((RUNNING + 1))
    if [[ $RUNNING -ge $PARALLEL ]]; then
        wait -n
        RUNNING=$((RUNNING - 1))
    fi
done < "$JOBS_FILE"
wait

echo "[bfbw sweep] DONE" | tee -a "$OUT_DIR/INFO"

# Summary
python3 <<EOF
import os, re, glob, json
out_dir = "$OUT_DIR"
results = []
for log in sorted(glob.glob(f"{out_dir}/logs/*.log")):
    name = os.path.basename(log).replace(".log","")
    txt = open(log).read()
    matches = re.findall(r"matched=(\d+)", txt)
    if not matches: continue
    final_line = re.findall(r"matched=(\d+)/480", txt)
    final = int(final_line[-1]) if final_line else None
    best = max(int(m) for m in matches)
    results.append({"name": name, "final": final, "best": best})

results.sort(key=lambda r: -(r["best"] or 0))
print(f"\n=== {len(results)} ALNS runs, top scores ===")
for r in results[:20]:
    print(f"  {r['name']}: best={r['best']} final={r['final']}")
EOF
