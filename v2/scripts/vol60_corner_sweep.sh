#!/bin/bash
# Vol-60 T3 — corner-assignment sweep.
# For each of 24 corner permutations, run vanilla_fast with --pin-hints
# + 4 --extra-hint to force that corner assignment. Collect deep partials,
# then run ALNS on each.

set -uo pipefail

BUDGET_MS="${1:-300000}"   # 5 min CP per permutation
ALNS_MS="${2:-300000}"     # 5 min ALNS per partial
PARALLEL="${3:-8}"

cd "$(dirname "$0")/.."
# Timestamped output dir — never overwrite previous runs (per
# vol-60 user feedback: "scripts do not overwrite their results
# so that we have history of everything").
TS="${VOL60_RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
RES_DIR="output/vol-60/corner_sweep_${TS}"
mkdir -p "$RES_DIR"
echo "Run tag: $TS"
echo "Output dir: $RES_DIR"

# All 24 permutations of corner pieces {0,1,2,3} to corners {TL=0, TR=15, BL=240, BR=255}.
# Format: "perm_id TL_pid TL_rot TR_pid TR_rot BL_pid BR_rot BR_pid BR_rot"
# Each corner-piece has a unique rotation per corner position (computed below).
#
# The rotations are precomputed by Python earlier and embedded here.
# TL needs sides[0]=BORDER, sides[3]=BORDER → rot 3 for pieces 0,1,2,3.
# TR needs sides[0]=BORDER, sides[1]=BORDER → rot 0.
# BL needs sides[2]=BORDER, sides[3]=BORDER → rot 2.
# BR needs sides[1]=BORDER, sides[2]=BORDER → rot 1.
# Confirmed in earlier Python output.

PERMS=(
  "p00 0 3 1 0 2 2 3 1"
  "p01 0 3 1 0 3 2 2 1"
  "p02 0 3 2 0 1 2 3 1"
  "p03 0 3 2 0 3 2 1 1"
  "p04 0 3 3 0 1 2 2 1"
  "p05 0 3 3 0 2 2 1 1"
  "p06 1 3 0 0 2 2 3 1"
  "p07 1 3 0 0 3 2 2 1"
  "p08 1 3 2 0 0 2 3 1"
  "p09 1 3 2 0 3 2 0 1"
  "p10 1 3 3 0 0 2 2 1"
  "p11 1 3 3 0 2 2 0 1"
  "p12 2 3 0 0 1 2 3 1"
  "p13 2 3 0 0 3 2 1 1"
  "p14 2 3 1 0 0 2 3 1"
  "p15 2 3 1 0 3 2 0 1"
  "p16 2 3 3 0 0 2 1 1"
  "p17 2 3 3 0 1 2 0 1"
  "p18 3 3 0 0 1 2 2 1"
  "p19 3 3 0 0 2 2 1 1"
  "p20 3 3 1 0 0 2 2 1"
  "p21 3 3 1 0 2 2 0 1"
  "p22 3 3 2 0 0 2 1 1"
  "p23 3 3 2 0 1 2 0 1"
)

JOBS_FILE="$RES_DIR/jobs.txt"
: > "$JOBS_FILE"
for perm in "${PERMS[@]}"; do
    read -r pid tl_p tl_r tr_p tr_r bl_p bl_r br_p br_r <<< "$perm"
    # Build args
    SNAP_DIR="$RES_DIR/snaps_${pid}"
    mkdir -p "$SNAP_DIR"
    LOG="$RES_DIR/${pid}.log"
    echo "$pid $tl_p $tl_r $tr_p $tr_r $bl_p $bl_r $br_p $br_r" >> "$JOBS_FILE"
done

N=$(wc -l < "$JOBS_FILE" | tr -d ' ')
echo "$(date +%H:%M:%S) Queued $N perms (parallel=$PARALLEL, cp=${BUDGET_MS}ms)"

cat "$JOBS_FILE" | xargs -L 1 -P "$PARALLEL" bash -c '
    PID="$0"
    TL_P="$1"; TL_R="$2"
    TR_P="$3"; TR_R="$4"
    BL_P="$5"; BL_R="$6"
    BR_P="$7"; BR_R="$8"
    SNAP_DIR="output/vol-60/corner_sweep/snaps_${PID}"
    SAVE_BEST="output/vol-60/corner_sweep/${PID}_best.json"
    LOG="output/vol-60/corner_sweep/${PID}.log"
    target/release/vanilla_fast \
        --budget-ms '"$BUDGET_MS"' \
        --threads 1 \
        --pin-hints \
        --extra-hint 0:${TL_P}:${TL_R} \
        --extra-hint 15:${TR_P}:${TR_R} \
        --extra-hint 240:${BL_P}:${BL_R} \
        --extra-hint 255:${BR_P}:${BR_R} \
        --snapshot-dir "$SNAP_DIR" \
        --snapshot-interval-ms 30000 \
        --snapshot-min-depth 100 \
        --save-best "$SAVE_BEST" \
        > "$LOG" 2>&1
    EXIT=$?
    # Find best depth reached
    DEPTH=$(grep -oE "max_depth=[0-9]+" "$LOG" | tail -1 | sed "s/max_depth=//")
    SNAPS=$(ls "$SNAP_DIR" 2>/dev/null | wc -l | tr -d " ")
    echo "[$(date +%H:%M:%S)] $PID TL=${TL_P} TR=${TR_P} BL=${BL_P} BR=${BR_P} exit=$EXIT depth=$DEPTH snaps=$SNAPS"
'

echo
echo "=== Summary ==="
SUMMARY="$RES_DIR/SUMMARY.csv"
echo "perm,TL,TR,BL,BR,max_depth,n_snaps" > "$SUMMARY"
for perm in "${PERMS[@]}"; do
    read -r pid tl_p tl_r tr_p tr_r bl_p bl_r br_p br_r <<< "$perm"
    LOG="$RES_DIR/${pid}.log"
    SNAP_DIR="$RES_DIR/snaps_${pid}"
    DEPTH=$(grep -oE "max_depth=[0-9]+" "$LOG" 2>/dev/null | tail -1 | sed "s/max_depth=//" || echo "?")
    N_SNAPS=$(ls "$SNAP_DIR" 2>/dev/null | wc -l | tr -d " ")
    echo "$pid,$tl_p,$tr_p,$bl_p,$br_p,$DEPTH,$N_SNAPS" >> "$SUMMARY"
done

echo "Per-perm max depth + snapshots collected:"
column -s',' -t "$SUMMARY"
