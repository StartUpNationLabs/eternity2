#!/bin/zsh
# Three-stage overnight frame-first funnel for Eternity II.
#
# Stage 1 (wide):    BORDERS_1 borders x PT_1 sec PT each.
# Stage 2 (medium):  top TOP_2 borders from stage 1 x PT_2 sec each.
# Stage 3 (deep):    top TOP_3 borders from stage 2 x PT_3 sec each.
#
# All stages produce checkpoint JSONs (output/frame_first_checkpoint_stage{N}.json)
# updated after every candidate. Stage 2 reads stage 1's checkpoint to pick seeds;
# stage 3 reads stage 2's. Resilient to crashes mid-stage: if the script
# aborts, the most recent checkpoint preserves all completed work.
#
# Logs land in output/overnight_logs/{stage1,stage2,stage3}.log.
#
# Tunable knobs at top of file. Recommended defaults below total ~5.6h on
# an 8-core M-series. Set ON_FAST_MACHINE=1 to scale up.

set -euo pipefail

# Move to project root (this script lives in v2/scripts/).
cd "$(dirname "$0")/.."

# ----- Tunables -----
BORDERS_1=${BORDERS_1:-80}
PT_1=${PT_1:-60}
BORDER_GEN=${BORDER_GEN:-20}
CP_S=${CP_S:-15}

TOP_2=${TOP_2:-16}
PT_2=${PT_2:-300}

TOP_3=${TOP_3:-4}
PT_3=${PT_3:-1800}

BASE_SEED=${BASE_SEED:-3405709037}  # 0xCAFEFEED — same as our 12-border test

# Output paths.
LOG_DIR=output/overnight_logs
mkdir -p "$LOG_DIR"
CKPT1=output/frame_first_checkpoint_stage1.json
CKPT2=output/frame_first_checkpoint_stage2.json
CKPT3=output/frame_first_checkpoint_stage3.json

BIN=./target/release/frame_first_e2
if [[ ! -x "$BIN" ]]; then
    echo "ERROR: $BIN not found. Run: cargo build --release -p eternity2-benchmark --bin frame_first_e2"
    exit 2
fi

# Force line-buffering at the shell so `tee` flushes as output arrives.
# This is belt-and-suspenders with the in-binary flush_err() calls.
unbuffer_cmd=""
if command -v stdbuf >/dev/null 2>&1; then
    unbuffer_cmd="stdbuf -oL -eL"
fi

now() { date '+%Y-%m-%d %H:%M:%S'; }

echo "================================================================"
echo "OVERNIGHT FUNNEL  start: $(now)"
echo "Stage 1: $BORDERS_1 borders x ${PT_1}s PT (border_gen=${BORDER_GEN}s, cp=${CP_S}s)"
echo "Stage 2: top $TOP_2 borders x ${PT_2}s PT"
echo "Stage 3: top $TOP_3 borders x ${PT_3}s PT"
echo "Base seed: 0x$(printf '%x' $BASE_SEED) = $BASE_SEED"
echo "Logs: $LOG_DIR/"
echo "Checkpoints: $CKPT1 $CKPT2 $CKPT3"
echo "================================================================"

# ----- Stage 1: wide explore -----
echo
echo "===== STAGE 1 (wide explore)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --n-borders "$BORDERS_1" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_1" \
    --base-seed "$BASE_SEED" \
    --checkpoint-path "$CKPT1" \
    --run-label stage1 \
    2>&1 | tee "$LOG_DIR/stage1.log"

echo
echo "Stage 1 done at $(now). Picking top-$TOP_2 borders from $CKPT1..."

# Extract top-TOP_2 seeds by pt_score (decimal, descending). Use jq.
if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq required to parse stage 1 checkpoint. Install with: brew install jq"
    exit 3
fi

top2_seeds=$(jq -r --argjson n "$TOP_2" '
    .per_border
    | sort_by(-.pt_score)
    | .[0:$n]
    | map(.seed | tostring)
    | join(",")
' "$CKPT1")

if [[ -z "$top2_seeds" ]]; then
    echo "ERROR: no seeds extracted from stage 1 checkpoint."
    exit 4
fi

echo "Top-$TOP_2 seeds for stage 2:"
echo "  $top2_seeds"

# ----- Stage 2: medium depth -----
echo
echo "===== STAGE 2 (medium depth)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --seeds-list "$top2_seeds" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_2" \
    --checkpoint-path "$CKPT2" \
    --run-label stage2 \
    2>&1 | tee "$LOG_DIR/stage2.log"

echo
echo "Stage 2 done at $(now). Picking top-$TOP_3 borders from $CKPT2..."

top3_seeds=$(jq -r --argjson n "$TOP_3" '
    .per_border
    | sort_by(-.pt_score)
    | .[0:$n]
    | map(.seed | tostring)
    | join(",")
' "$CKPT2")

if [[ -z "$top3_seeds" ]]; then
    echo "ERROR: no seeds extracted from stage 2 checkpoint."
    exit 5
fi

echo "Top-$TOP_3 seeds for stage 3:"
echo "  $top3_seeds"

# ----- Stage 3: deep -----
echo
echo "===== STAGE 3 (deep PT)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --seeds-list "$top3_seeds" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_3" \
    --checkpoint-path "$CKPT3" \
    --run-label stage3 \
    2>&1 | tee "$LOG_DIR/stage3.log"

echo
echo "================================================================"
echo "OVERNIGHT FUNNEL  done: $(now)"
echo "Best per stage:"
jq -r '"  stage1: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT1"
jq -r '"  stage2: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT2"
jq -r '"  stage3: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT3"
echo "================================================================"
