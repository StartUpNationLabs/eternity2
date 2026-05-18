#!/usr/bin/env bash
# Vol-125 T3 Stage B — long ALNS with border-pinning, on top-scoring Stage A borders.
#
# Usage: vol125_stage_b.sh <SWEEP_DIR> <TOP_N> <ALNS_MS> <SEEDS_CSV> [BORDER_PIN]
#   SWEEP_DIR: output/vol-125/sweep_stageA_*
#   BORDER_PIN: 1 to pass --extra-hint for all 60 border cells (default 0)
set -euo pipefail

SWEEP_DIR="$1"
TOP_N="${2:-20}"
ALNS_MS="${3:-1800000}"  # 30min
SEEDS_CSV="${4:-1,7,42,99}"
BORDER_PIN="${5:-0}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
OUT_DIR="output/vol-125/stageB_${RUN_TAG}"
mkdir -p "$OUT_DIR/logs"

# Pick top-N CSP-filled partials by ALNS Stage A best score
python3 -c "
import os, re, glob, json, sys
sweep = '$SWEEP_DIR'
results = []
for log in sorted(glob.glob(f'{sweep}/logs/*_alns_s*.log')):
    name = os.path.basename(log).replace('.log','')
    txt = open(log).read()
    matches = re.findall(r'matched=(\d+)', txt)
    if not matches: continue
    best = max(int(m) for m in matches)
    border_name = name.split('_alns_s')[0]
    results.append((border_name, best))
results.sort(key=lambda r: -r[1])
top = results[:$TOP_N]
for border_name, best in top:
    csp = f'{sweep}/csp_fill/{border_name}_csp.json'
    if os.path.exists(csp):
        print(f'{best}\t{csp}')
" > "$OUT_DIR/picks.tsv"

echo "[stage B] top-$TOP_N picks from $SWEEP_DIR (border_pin=$BORDER_PIN):" | tee "$OUT_DIR/INFO"
head -10 "$OUT_DIR/picks.tsv" | tee -a "$OUT_DIR/INFO"

# Compute border-pin args once (60 border cells of a 16x16 board)
PIN_ARGS=""
if [[ "$BORDER_PIN" == "1" ]]; then
    for i in $(seq 0 15); do PIN_ARGS+="--extra-hint $i "; done
    for i in $(seq 240 255); do PIN_ARGS+="--extra-hint $i "; done
    for i in 16 32 48 64 80 96 112 128 144 160 176 192 208 224; do PIN_ARGS+="--extra-hint $i "; done
    for i in 31 47 63 79 95 111 127 143 159 175 191 207 223 239; do PIN_ARGS+="--extra-hint $i "; done
fi

IFS=',' read -ra SEEDS <<< "$SEEDS_CSV"

source $HOME/.cargo/env

while IFS=$'\t' read -r STAGE_A_BEST CSP_PATH; do
    BNAME=$(basename "$CSP_PATH" .json)
    for SEED in "${SEEDS[@]}"; do
        ALNS_LOG="$OUT_DIR/logs/${BNAME}_alns_s${SEED}_pin${BORDER_PIN}.log"
        if [[ -f "$ALNS_LOG.done" ]]; then continue; fi
        echo "[$(date +%H:%M:%S)] $BNAME seed=$SEED (Stage A best=$STAGE_A_BEST) pin=$BORDER_PIN" | tee -a "$OUT_DIR/PROGRESS"
        ./target/bench-fast/alns_only \
            --cp-board "$CSP_PATH" \
            --alns-budget-ms "$ALNS_MS" \
            --seed "$SEED" \
            --ops basic \
            $PIN_ARGS 2>&1 | tee "$ALNS_LOG" | grep -E "matched|saved|best" | tail -3
        touch "$ALNS_LOG.done"
    done
done < "$OUT_DIR/picks.tsv"

# Final summary
python3 <<EOF
import os, re, glob, json
out_dir = "$OUT_DIR"
results = []
for log in sorted(glob.glob(f"{out_dir}/logs/*.log")):
    name = os.path.basename(log).replace(".log","")
    txt = open(log).read()
    matches = re.findall(r"matched=(\d+)", txt)
    if not matches: continue
    best = max(int(m) for m in matches)
    results.append((name, best))
results.sort(key=lambda r: -r[1])
print(f"\n=== Top results across {len(results)} ALNS jobs ===")
for n, b in results[:20]:
    print(f"  {n}: best={b}")
with open(f"{out_dir}/summary.json","w") as f:
    json.dump({"n_runs": len(results), "top20": results[:20]}, f, indent=2)
EOF
