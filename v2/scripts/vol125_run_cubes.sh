#!/usr/bin/env bash
# Vol-125 T4 — solve all cubes in a directory with kissat in parallel.
#
# Usage:
#   vol125_run_cubes.sh <CUBE_DIR> <TIMEOUT_S> <PARALLEL>
#
# Each cube ⇒ one kissat run; results aggregated; if any SAT, stop all others.
set -euo pipefail

CUBE_DIR="${1:-output/vol-125/sat_cubes}"
TIMEOUT_S="${2:-600}"
PARALLEL="${3:-4}"

RUN_TAG="${RUN_TAG:-$(date +%Y%m%dT%H%M%S)}"
RES_DIR="${CUBE_DIR}/results_${RUN_TAG}"
mkdir -p "$RES_DIR"

echo "[vol-125 cubes] dir=$CUBE_DIR  timeout=${TIMEOUT_S}s  parallel=$PARALLEL  tag=$RUN_TAG" | tee "$RES_DIR/INFO"

# Detect available cubes
N=$(ls "$CUBE_DIR"/cube_*.assume 2>/dev/null | wc -l | tr -d ' ')
echo "[vol-125 cubes] found $N cubes" | tee -a "$RES_DIR/INFO"

# SAT-found sentinel
FOUND_SAT="$RES_DIR/SAT_FOUND"

run_one() {
    local assume="$1"
    local name
    name="$(basename "$assume" .assume)"
    local out="$RES_DIR/${name}.out"
    local mod="$RES_DIR/${name}.model"
    local stat="$RES_DIR/${name}.status"
    local base="$(dirname "$assume")/base.cnf"

    if [[ -f "$stat" ]]; then
        return
    fi
    if [[ -f "$FOUND_SAT" ]]; then
        echo "STOPPED" > "$stat"
        return
    fi
    local t0
    t0=$(date +%s)
    # Concatenate base CNF + assumption units. The header in base.cnf says
    # n_clauses = base_count; appending more clauses is technically a
    # malformed DIMACS, but kissat accepts trailing clauses just fine.
    cat "$base" "$assume" | kissat --time="$TIMEOUT_S" --relaxed > "$out" 2>&1 || true
    local t1
    t1=$(date +%s)
    local elapsed=$((t1 - t0))
    local s
    s=$(grep -E "^s " "$out" | head -1 | awk '{print $2}' || echo "?")
    echo "$s $elapsed" > "$stat"
    if [[ "$s" == "SATISFIABLE" ]]; then
        grep -E "^v " "$out" > "$mod"
        touch "$FOUND_SAT"
        echo "[$(date +%H:%M:%S)] !!! SAT on $name (${elapsed}s) !!!" | tee -a "$RES_DIR/PROGRESS"
    else
        echo "[$(date +%H:%M:%S)] $name $s (${elapsed}s)" >> "$RES_DIR/PROGRESS"
    fi
}

export -f run_one
export RES_DIR FOUND_SAT TIMEOUT_S

ls "$CUBE_DIR"/cube_*.assume | xargs -n 1 -P "$PARALLEL" -I {} bash -c 'run_one "$@"' _ {}

# Summary
echo "" | tee -a "$RES_DIR/INFO"
echo "=== Summary ===" | tee -a "$RES_DIR/INFO"
N_SAT=$(grep -lE "SATISFIABLE" "$RES_DIR"/*.status 2>/dev/null | wc -l | tr -d ' ')
N_UNSAT=$(grep -lE "UNSATISFIABLE" "$RES_DIR"/*.status 2>/dev/null | wc -l | tr -d ' ')
N_UNK=$(grep -lE "UNKNOWN|\?" "$RES_DIR"/*.status 2>/dev/null | wc -l | tr -d ' ')
echo "SAT: $N_SAT" | tee -a "$RES_DIR/INFO"
echo "UNSAT: $N_UNSAT" | tee -a "$RES_DIR/INFO"
echo "UNKNOWN/TIMEOUT: $N_UNK" | tee -a "$RES_DIR/INFO"

if [[ -f "$FOUND_SAT" ]]; then
    echo "!!! At least one cube was SATISFIABLE !!!"
    ls "$RES_DIR"/*.model
fi
