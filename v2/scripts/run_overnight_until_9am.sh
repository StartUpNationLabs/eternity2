#!/bin/bash
# Vol-17 overnight portfolio — adaptive chained chunks until 09:00.
#
# Architecture:
#   - The portfolio cycles through many (schedule, noise, seed, H22) configs.
#   - Each "chunk" is a 10-min Blackwood-CP + 10-min ALNS run.
#   - Between chunks: scoreboard updated, hall-of-fame copies of any new high.
#   - When a config's last 2 chunks have made no progress, switch to next config.
#   - Long-running visibility: each chunk produces a full intermediate result.
#
# Per-chunk wall: ~20 min. Over 7h = ~21 chunks possible.
#
# Per chunk output:
#   output/v17_overnight/chunk_NNN/
#     stderr.log
#     cp_board.json   (197-cell partial)
#     alns_board.json (256-cell final, scored)
#     meta.json       (config + scores + bucas + elapsed)
#
# Live scoreboard:
#   output/v17_overnight/SCOREBOARD.txt
#   output/v17_overnight/HALL_OF_FAME/best_<score>_chunk<N>.json
#
# Resume-friendly: if killed, restart picks up where it left off.

set -u
cd /Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
ROOT="output/v17_overnight"
mkdir -p "$ROOT/HALL_OF_FAME"

# End time = 09:00. Compute as today's 09:00 if we're before 09:00, tomorrow's otherwise.
END_TIME=$(date -j -f "%H:%M" "09:00" +%s 2>/dev/null || date -d "09:00 today" +%s)
NOW=$(date +%s)
if [ $NOW -ge $END_TIME ]; then
    END_TIME=$((END_TIME + 86400))
fi
DURATION_HRS=$(( (END_TIME - NOW) / 3600 ))
echo "[$(date '+%H:%M:%S')] Overnight portfolio — will run ~${DURATION_HRS}h until $(date -r $END_TIME '+%Y-%m-%d %H:%M:%S')"

# ---------- Configs to cycle through ----------
# Format: schedule,noise_amp,sched_seed,alns_seed,h22(0|1),cp_ms_override,alns_ms_override
# If cp_ms_override or alns_ms_override is "-", uses default CP_MS/ALNS_MS.
CONFIGS=(
    # === Schedule-diversity rotation (NEW: round-robin to escape v17a trap) ===
    # Each row visited at most twice before auto-switch fires.
    "calibrated_v17a,0,0,1,0,-,-"      # baseline anchor (455 prior best)
    "calibrated_v17b,0,0,1,0,-,-"      # tight envelope (453 in overnight)
    "calibrated_v17c,0,0,1,0,-,-"      # empirical breaks
    "calibrated_v17e,0.15,1,1,0,-,-"   # noise seed 1
    "calibrated_v17e,0.15,2,1,0,-,-"   # noise seed 2
    "calibrated_v17e,0.15,3,1,0,-,-"   # noise seed 3
    "calibrated_v17a,0,0,1,1,-,-"      # v17a + H22 tie-shuffle
    "calibrated_v17b,0,0,1,1,-,-"      # v17b + H22
    "calibrated_v17c,0,0,1,1,-,-"      # v17c + H22
    "calibrated_v17e,0.10,1,1,1,-,-"   # noise + H22
    "calibrated_v17e,0.20,1,1,1,-,-"   # bigger noise + H22
    # === ALNS-seed sweeps on best schedules ===
    "calibrated_v17a,0,0,2,0,-,-"
    "calibrated_v17a,0,0,3,0,-,-"
    "calibrated_v17b,0,0,2,0,-,-"
    "calibrated_v17b,0,0,3,0,-,-"
    "calibrated_v17e,0.15,1,2,0,-,-"
    "calibrated_v17e,0.15,1,3,0,-,-"
    # === Edge noise levels ===
    "calibrated_v17e,0.05,1,1,0,-,-"
    "calibrated_v17e,0.25,1,1,0,-,-"
    "calibrated_v17e,0.40,1,1,1,-,-"   # extreme noise
    # === Long-CP variants — tests "does extended CP find a different basin?" ===
    "calibrated_v17a,0,0,1,0,1800000,300000"   # 30min CP + 5min ALNS
    "calibrated_v17b,0,0,1,1,1800000,300000"
    # === Extended-ALNS variants — tests "can deep ALNS push past 456?" ===
    "calibrated_v17a,0,0,1,0,300000,1800000"   # 5min CP + 30min ALNS
    "calibrated_v17b,0,0,1,0,300000,1800000"   # 5min CP + 30min ALNS (v17b)
)
# Vol-17 — default ALNS op set. "winning5" proven best (455). Override
# per-config later if we want ablations.
OPS_PRESET="winning5"

CP_MS=600000        # 10 min CP default
ALNS_MS=600000      # 10 min ALNS default
# Vol-17 — lowered from 2 to 1 after overnight burned 5+h on v17a retries.
# Each config now gets ONE chance; if no improvement vs prior best,
# auto-switch immediately.
CONFIG_FAIL_LIMIT=1

# Initialize state from existing scoreboard if present (resume support).
CHUNK_IDX=0
BEST_SCORE=0
BEST_CHUNK_DIR=""
if [ -f "$ROOT/SCOREBOARD.txt" ]; then
    # Recover from existing meta files.
    for meta in $ROOT/chunk_*/meta.json; do
        [ ! -f "$meta" ] && continue
        CHUNK_IDX=$((CHUNK_IDX + 1))
        s=$(python3 -c "import json; print(json.load(open('$meta')).get('alns_matched',0))" 2>/dev/null)
        if [ -n "$s" ] && [ "$s" -gt "$BEST_SCORE" ]; then
            BEST_SCORE=$s
            BEST_CHUNK_DIR=$(dirname "$meta")
        fi
    done
    echo "[$(date '+%H:%M:%S')] resuming: $CHUNK_IDX chunks already done, best so far: $BEST_SCORE/480 ($BEST_CHUNK_DIR)"
fi

# ---------- Scoreboard updater ----------
update_scoreboard() {
    local sb="$ROOT/SCOREBOARD.txt"
    {
        echo "============================================================"
        echo "  vol-17 overnight portfolio scoreboard"
        echo "  started at $(date -r $NOW '+%Y-%m-%d %H:%M:%S'), target end $(date -r $END_TIME '+%Y-%m-%d %H:%M:%S')"
        echo "  current time: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "  chunks completed: $CHUNK_IDX"
        echo "  CURRENT BEST: $BEST_SCORE/480"
        if [ -n "$BEST_CHUNK_DIR" ]; then
            echo "  best chunk: $BEST_CHUNK_DIR"
            best_bucas=$(python3 -c "import json; print(json.load(open('$BEST_CHUNK_DIR/meta.json')).get('bucas_url',''))" 2>/dev/null)
            [ -n "$best_bucas" ] && echo "  best bucas: $best_bucas"
        fi
        echo "============================================================"
        echo ""
        echo "All chunks (chronological):"
        printf "  %-4s %-22s %-7s %-8s %-7s %-4s %-7s %-9s\n" \
            "#" "schedule" "noise" "schedSeed" "alnsSeed" "H22" "CP" "ALNS"
        for meta in $(ls -1 $ROOT/chunk_*/meta.json 2>/dev/null | sort); do
            python3 -c "
import json
try:
    d=json.load(open('$meta'))
    print('  %-4s %-22s %-7s %-8s %-7s %-4s %-7s %-9s' % (
        d.get('chunk_idx','?'), d.get('schedule',''),
        d.get('noise_amplitude',''), d.get('schedule_seed',''),
        d.get('alns_seed',''), d.get('shuffle_h22',''),
        f\"{d.get('cp_matched',0)}/480\", f\"{d.get('alns_matched',0)}/480\"))
except: pass
"
        done
        echo ""
        echo "Top 10 ALNS scores:"
        for meta in $ROOT/chunk_*/meta.json; do
            [ ! -f "$meta" ] && continue
            python3 -c "
import json
try:
    d=json.load(open('$meta'))
    print(f\"{d.get('alns_matched',0):4d} chunk_{d.get('chunk_idx',0):03d}  sched={d.get('schedule','?')}  noise={d.get('noise_amplitude','?')}  sschedseed={d.get('schedule_seed','?')}  alnsseed={d.get('alns_seed','?')}  h22={d.get('shuffle_h22','?')}\")
except: pass
" 2>/dev/null
        done | sort -rn | head -10
        echo ""
        echo "Hall of fame:"
        ls -la $ROOT/HALL_OF_FAME/ 2>/dev/null | tail -n +2
    } > "$sb"
}

# ---------- Main loop ----------
config_idx=0
config_runs_since_improvement=0
last_score_for_config=0

while true; do
    NOW=$(date +%s)
    REMAINING=$((END_TIME - NOW))
    if [ $REMAINING -le 60 ]; then
        echo "[$(date '+%H:%M:%S')] under 1 min remaining, stopping."
        break
    fi

    # Pick config (with auto-switch if stuck).
    if [ $config_runs_since_improvement -ge $CONFIG_FAIL_LIMIT ]; then
        config_idx=$(( (config_idx + 1) % ${#CONFIGS[@]} ))
        config_runs_since_improvement=0
        echo "[$(date '+%H:%M:%S')] auto-switch: moving to config $config_idx"
    fi
    cfg="${CONFIGS[$config_idx]}"
    IFS=',' read -r SCHED NOISE SSEED ASEED H22 CP_OVERRIDE ALNS_OVERRIDE <<< "$cfg"

    # Add cycle offset so repeats use different seeds.
    cycle=$(( CHUNK_IDX / ${#CONFIGS[@]} ))
    SSEED=$((SSEED + cycle * 100))
    ASEED=$((ASEED + cycle * 100))

    CHUNK_IDX=$((CHUNK_IDX + 1))
    DIR="$ROOT/chunk_$(printf %04d $CHUNK_IDX)"
    mkdir -p "$DIR"

    SHUFFLE_FLAG=""
    [ "$H22" = "1" ] && SHUFFLE_FLAG="--shuffle-blackwood-ties"

    # Per-config budget overrides.
    if [ "$CP_OVERRIDE" != "-" ] && [ -n "$CP_OVERRIDE" ]; then
        CP_MS_BASE=$CP_OVERRIDE
    else
        CP_MS_BASE=$CP_MS
    fi
    if [ "$ALNS_OVERRIDE" != "-" ] && [ -n "$ALNS_OVERRIDE" ]; then
        ALNS_MS_BASE=$ALNS_OVERRIDE
    else
        ALNS_MS_BASE=$ALNS_MS
    fi
    # Budget-adjust if not enough time for full chunk.
    BUDGET_S=$(( (CP_MS_BASE + ALNS_MS_BASE) / 1000 ))
    if [ $REMAINING -lt $((BUDGET_S + 30)) ]; then
        scale_pct=$(( REMAINING * 100 / (BUDGET_S + 60) ))
        [ $scale_pct -lt 10 ] && scale_pct=10
        CP_MS_ADJ=$(( CP_MS_BASE * scale_pct / 100 ))
        ALNS_MS_ADJ=$(( ALNS_MS_BASE * scale_pct / 100 ))
        [ $CP_MS_ADJ -lt 60000 ] && CP_MS_ADJ=60000
        [ $ALNS_MS_ADJ -lt 60000 ] && ALNS_MS_ADJ=60000
        echo "[$(date '+%H:%M:%S')]   remaining=${REMAINING}s, scaling: CP=$((CP_MS_ADJ/1000))s ALNS=$((ALNS_MS_ADJ/1000))s"
    else
        CP_MS_ADJ=$CP_MS_BASE
        ALNS_MS_ADJ=$ALNS_MS_BASE
    fi

    echo "[$(date '+%H:%M:%S')] CHUNK #${CHUNK_IDX}: sched=$SCHED noise=$NOISE schedSeed=$SSEED alnsSeed=$ASEED H22=$H22  CP=$((CP_MS_ADJ/1000))s ALNS=$((ALNS_MS_ADJ/1000))s"

    START=$(date +%s)
    # Vol-17 — periodic checkpoint of ALNS best board to enable mid-run
    # visibility in the scoreboard. Path is per-chunk.
    CHECKPOINT="$DIR/alns_best_live.json"
    ./target/bench-fast/run_e2_blackwood \
        --cp-budget-ms $CP_MS_ADJ --alns-budget-ms $ALNS_MS_ADJ \
        --seed "$ASEED" --arms blackwood_raw \
        --schedule "$SCHED" \
        --noise-amplitude "$NOISE" --schedule-seed "$SSEED" \
        --ops "$OPS_PRESET" \
        $SHUFFLE_FLAG \
        --alns-checkpoint "$CHECKPOINT" \
        --alns-checkpoint-every-ms 30000 \
        > "$DIR/stderr.log" 2>&1
    END=$(date +%s)
    ELAPSED=$((END - START))

    # Parse result.
    cp_line=$(grep "CP:" "$DIR/stderr.log" | tail -1)
    alns_line=$(grep "ALNS:" "$DIR/stderr.log" | tail -1)
    bucas_line=$(grep "ALNS bucas:" "$DIR/stderr.log" | tail -1)
    cp_m=$(echo "$cp_line" | grep -oE "matched=[0-9]+/480" | head -1 | grep -oE "[0-9]+" | head -1)
    cp_d=$(echo "$cp_line" | grep -oE "depth=[0-9]+" | head -1 | grep -oE "[0-9]+")
    cp_p=$(echo "$cp_line" | grep -oE "placed=[0-9]+/256" | head -1 | grep -oE "[0-9]+" | head -1)
    alns_m=$(echo "$alns_line" | grep -oE "matched=[0-9]+/480" | head -1 | grep -oE "[0-9]+" | head -1)
    alns_iters=$(echo "$alns_line" | grep -oE "iters=[0-9]+" | head -1 | grep -oE "[0-9]+")
    bucas=$(echo "$bucas_line" | grep -oE "https://[^[:space:]]+" | head -1)
    cp_m=${cp_m:-0}
    cp_d=${cp_d:-0}
    cp_p=${cp_p:-0}
    alns_m=${alns_m:-0}
    alns_iters=${alns_iters:-0}

    # Save full meta.
    cat > "$DIR/meta.json" <<EOF
{
  "chunk_idx": $CHUNK_IDX,
  "schedule": "$SCHED",
  "noise_amplitude": $NOISE,
  "schedule_seed": $SSEED,
  "alns_seed": $ASEED,
  "shuffle_h22": $H22,
  "cp_budget_ms": $CP_MS_ADJ,
  "alns_budget_ms": $ALNS_MS_ADJ,
  "elapsed_s": $ELAPSED,
  "started_at": "$(date -r $START '+%Y-%m-%d %H:%M:%S')",
  "cp_matched": $cp_m,
  "cp_placed": $cp_p,
  "cp_depth": $cp_d,
  "alns_matched": $alns_m,
  "alns_iters": $alns_iters,
  "bucas_url": "${bucas:-}"
}
EOF

    # Copy boards.
    latest_run=$(ls -td output/v15_e2_blackwood/run_*/ 2>/dev/null | head -1)
    if [ -n "$latest_run" ]; then
        cp "${latest_run}/blackwood_raw_cp_board.json" "$DIR/cp_board.json" 2>/dev/null || true
        cp "${latest_run}/blackwood_raw_alns_board.json" "$DIR/alns_board.json" 2>/dev/null || true
        cp "${latest_run}/blackwood_raw_cp.log" "$DIR/cp.log" 2>/dev/null || true
    fi

    # New best check.
    if [ "$alns_m" -gt "$BEST_SCORE" ]; then
        BEST_SCORE=$alns_m
        BEST_CHUNK_DIR="$DIR"
        echo "[$(date '+%H:%M:%S')]   *** NEW BEST: $BEST_SCORE/480 *** chunk_${CHUNK_IDX}"
        echo "[$(date '+%H:%M:%S')]   bucas: ${bucas:-?}"
        if [ -f "$DIR/alns_board.json" ]; then
            cp "$DIR/alns_board.json" "$ROOT/HALL_OF_FAME/best_${BEST_SCORE}_chunk${CHUNK_IDX}.json"
        fi
    fi
    # Auto-switch logic.
    if [ "$alns_m" -gt "$last_score_for_config" ]; then
        last_score_for_config=$alns_m
        config_runs_since_improvement=0
    else
        config_runs_since_improvement=$((config_runs_since_improvement + 1))
    fi
    echo "[$(date '+%H:%M:%S')]   chunk_${CHUNK_IDX} done in ${ELAPSED}s: CP=${cp_m}/480 ALNS=${alns_m}/480 (best=$BEST_SCORE)"

    update_scoreboard
    sleep 5
done
echo "[$(date '+%H:%M:%S')] Overnight portfolio finished. Final best: $BEST_SCORE/480 (chunk $BEST_CHUNK_DIR)"
update_scoreboard
