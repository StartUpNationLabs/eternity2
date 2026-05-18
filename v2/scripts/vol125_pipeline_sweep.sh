#!/usr/bin/env bash
# Vol-125 T3 Stage A — pipeline sweep on a sample of border partials.
#
# For each border in the sample, run:
#   1. CSP-fill 60s (joe_depth150_bp_par)
#   2. ALNS basic with given budget
#
# Writes to output/vol-125/sweep_${RUN_TAG}/
#
# Usage:
#   vol125_pipeline_sweep.sh <N_BORDERS> <ALNS_MS> <SEEDS_CSV> [INDEX_FILE]
#
# Example:
#   vol125_pipeline_sweep.sh 50 300000 1,7,42 output/vol-125/borders/index.json

set -euo pipefail

N_BORDERS="${1:-50}"
ALNS_MS="${2:-300000}"
SEEDS_CSV="${3:-1,7,42}"
INDEX_FILE="${4:-output/vol-125/borders/index.json}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
OUT_DIR="output/vol-125/sweep_${RUN_TAG}"
mkdir -p "$OUT_DIR"
mkdir -p "$OUT_DIR/csp_fill"
mkdir -p "$OUT_DIR/alns_out"
mkdir -p "$OUT_DIR/logs"

# Pick N borders evenly spaced across the index.
python3 -c "
import json, sys
d = json.load(open('$INDEX_FILE'))
e = d['entries']
n = $N_BORDERS
step = max(1, len(e) // n)
picks = e[::step][:n]
for p in picks:
    print(f\"{p['id']}\t{p['path']}\")
" > "$OUT_DIR/picks.tsv"

N_PICKED=$(wc -l < "$OUT_DIR/picks.tsv" | tr -d ' ')
echo "[vol-125 sweep] tag=${RUN_TAG} picked=${N_PICKED} alns_ms=${ALNS_MS} seeds=${SEEDS_CSV}" | tee "$OUT_DIR/INFO"

source $HOME/.cargo/env

# Build the bins if needed
cargo build --profile bench-fast -p eternity2-bench-audit --bin border_to_csp_fill --bin alns_only 2>&1 | tail -3

IFS=',' read -ra SEEDS <<< "$SEEDS_CSV"

# Process each border serially (engine itself is parallel; we don't want fork bombs)
while IFS=$'\t' read -r BID BPATH; do
    BNAME=$(basename "$BPATH" .json)
    CSP_OUT="$OUT_DIR/csp_fill/${BNAME}_csp.json"
    LOG="$OUT_DIR/logs/${BNAME}.log"

    if [[ ! -f "$CSP_OUT" ]]; then
        echo "[$(date +%H:%M:%S)] CSP-fill border $BID: $BNAME" | tee -a "$OUT_DIR/PROGRESS"
        ./target/bench-fast/border_to_csp_fill \
            --board "$BPATH" \
            --budget-ms 60000 \
            --solver joe_depth150_bp_par \
            --seed 1 \
            --out "$CSP_OUT" 2>&1 | tee "$LOG" | grep -E "loaded board|CSP fill done" || true
    fi

    # Score CSP-filled partial
    CSP_MATCHED=$(grep "CSP fill done" "$LOG" 2>/dev/null | grep -oE 'matched: [0-9]+ -> [0-9]+' | awk '{print $NF}' || echo "?")
    echo "[$(date +%H:%M:%S)] $BID csp_matched=$CSP_MATCHED" >> "$OUT_DIR/PROGRESS"

    # ALNS for each seed
    for SEED in "${SEEDS[@]}"; do
        ALNS_LOG="$OUT_DIR/logs/${BNAME}_alns_s${SEED}.log"
        if [[ ! -f "$ALNS_LOG.done" ]]; then
            echo "[$(date +%H:%M:%S)] ALNS border $BID seed $SEED" | tee -a "$OUT_DIR/PROGRESS"
            ./target/bench-fast/alns_only \
                --cp-board "$CSP_OUT" \
                --alns-budget-ms "$ALNS_MS" \
                --seed "$SEED" \
                --ops basic 2>&1 | tee "$ALNS_LOG" | grep -E "matched|saved|best" | tail -5
            touch "$ALNS_LOG.done"
        fi
    done
done < "$OUT_DIR/picks.tsv"

echo "[vol-125 sweep] DONE tag=${RUN_TAG}" | tee -a "$OUT_DIR/INFO"

# Final summary
python3 <<EOF
import os, re, glob, json
out_dir = "$OUT_DIR"
results = []
for log in sorted(glob.glob(f"{out_dir}/logs/*_alns_s*.log")):
    name = os.path.basename(log).replace(".log","")
    txt = open(log).read()
    matches = re.findall(r"matched=(\d+)", txt)
    final = int(matches[-1]) if matches else None
    best = max((int(m) for m in matches), default=None)
    results.append({"name": name, "final": final, "best": best})

results.sort(key=lambda r: -(r["best"] or 0))
print(f"\n=== Top 20 results across {len(results)} ALNS runs ===")
for r in results[:20]:
    print(f"  {r['name']}: best={r['best']} final={r['final']}")

summary = {"n_runs": len(results), "top20": results[:20], "all_best": [r["best"] for r in results]}
with open(f"{out_dir}/summary.json","w") as f:
    json.dump(summary, f, indent=2)
EOF
