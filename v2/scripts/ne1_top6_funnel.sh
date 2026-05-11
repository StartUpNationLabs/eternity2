#!/usr/bin/env bash
# NE1: top-6-match-filtered frame-first funnel.
#
# Differs from overnight_funnel.sh: instead of selecting stage-2 seeds
# by raw pt_score, selects by (top-6 universal-mismatch matches DESC,
# pt_score DESC). The hypothesis (from RESEARCH_NOTES_5) is that
# matching all 6 top universal mismatches is necessary for crossing 449,
# so borders that produce 6/6-matching basins are the path forward.
#
# Stage 1: WIDE explore — lots of borders, short PT, write checkpoint
#          with per-candidate bucas_url.
# Stage 2: medium depth on top-N borders selected by top-6 matches.
# Stage 3: deep PT on top-K from stage 2 (also by top-6 matches first).
#
# Usage:
#   scripts/ne1_top6_funnel.sh
# Knobs via env vars (defaults below).

set -euo pipefail

cd "$(dirname "$0")/.."

BORDERS_1=${BORDERS_1:-60}
PT_1=${PT_1:-90}
BORDER_GEN=${BORDER_GEN:-20}
CP_S=${CP_S:-15}

TOP_2=${TOP_2:-12}
PT_2=${PT_2:-300}

TOP_3=${TOP_3:-3}
PT_3=${PT_3:-1500}

# Default base seed: 0xCAFEFEEC. (Vol-4 funnels used 0xCAFEFEED; we
# nudge by 1 so we explore a different border-seed space rather than
# resampling the same one. The CAFE constants are arbitrary but match
# the vol-4 convention.)
BASE_SEED=${BASE_SEED:-3405709036}

LOG_DIR=output/ne1_logs
mkdir -p "$LOG_DIR"
CKPT1=output/ne1_checkpoint_stage1.json
CKPT2=output/ne1_checkpoint_stage2.json
CKPT3=output/ne1_checkpoint_stage3.json

BIN=./target/release/frame_first_e2
SELECTOR=scripts/select_seeds_by_top6.py
FORBIDDEN=data/forbidden_top6.json

if [[ ! -x "$BIN" ]]; then
    echo "ERROR: $BIN not built."
    exit 2
fi
if [[ ! -f "$SELECTOR" ]]; then
    echo "ERROR: $SELECTOR not found."
    exit 2
fi
if [[ ! -f "$FORBIDDEN" ]]; then
    echo "ERROR: $FORBIDDEN not found."
    exit 2
fi

unbuffer_cmd=""
if command -v stdbuf >/dev/null 2>&1; then
    unbuffer_cmd="stdbuf -oL -eL"
fi

now() { date '+%Y-%m-%d %H:%M:%S'; }

echo "================================================================"
echo "NE1 TOP-6 FUNNEL  start: $(now)"
echo "Stage 1: $BORDERS_1 borders x ${PT_1}s PT"
echo "Stage 2: top $TOP_2 (by top-6 match) x ${PT_2}s PT"
echo "Stage 3: top $TOP_3 (by top-6 match) x ${PT_3}s PT"
echo "Base seed: 0x$(printf '%x' $BASE_SEED) = $BASE_SEED"
echo "================================================================"

# Stage 1
echo
echo "===== STAGE 1 (wide)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --n-borders "$BORDERS_1" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_1" \
    --base-seed "$BASE_SEED" \
    --checkpoint-path "$CKPT1" \
    --run-label ne1_stage1 \
    2>&1 | tee "$LOG_DIR/stage1.log"

echo
echo "Stage 1 done at $(now). Selecting top-$TOP_2 by top-6 match..."
top2_seeds=$(python3 "$SELECTOR" "$CKPT1" "$TOP_2" "$FORBIDDEN" 2> "$LOG_DIR/selector_stage2.log")
echo "selector diagnostics:"
cat "$LOG_DIR/selector_stage2.log"
echo "stage-2 seeds: $top2_seeds"

if [[ -z "$top2_seeds" ]]; then
    echo "ERROR: empty seed list from selector"
    exit 4
fi

# Stage 2
echo
echo "===== STAGE 2 (medium)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --seeds-list "$top2_seeds" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_2" \
    --checkpoint-path "$CKPT2" \
    --run-label ne1_stage2 \
    2>&1 | tee "$LOG_DIR/stage2.log"

echo
echo "Stage 2 done at $(now). Selecting top-$TOP_3 by top-6 match..."
top3_seeds=$(python3 "$SELECTOR" "$CKPT2" "$TOP_3" "$FORBIDDEN" 2> "$LOG_DIR/selector_stage3.log")
echo "selector diagnostics:"
cat "$LOG_DIR/selector_stage3.log"
echo "stage-3 seeds: $top3_seeds"

if [[ -z "$top3_seeds" ]]; then
    echo "ERROR: empty seed list from selector"
    exit 5
fi

# Stage 3
echo
echo "===== STAGE 3 (deep)  $(now)  ====="
$unbuffer_cmd "$BIN" \
    --seeds-list "$top3_seeds" \
    --border-gen-seconds "$BORDER_GEN" \
    --cp-seconds "$CP_S" \
    --pt-seconds "$PT_3" \
    --checkpoint-path "$CKPT3" \
    --run-label ne1_stage3 \
    2>&1 | tee "$LOG_DIR/stage3.log"

echo
echo "================================================================"
echo "NE1 TOP-6 FUNNEL  done: $(now)"
echo "Best per stage:"
jq -r '"  stage1: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT1"
jq -r '"  stage2: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT2"
jq -r '"  stage3: \(.best.score)/\(.best.total) (seed=\(.best.seed_hex))"' "$CKPT3"
echo "================================================================"
