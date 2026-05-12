#!/usr/bin/env bash
# NE2-iterative: deepen the forbidden set across rounds.
#
# Hypothesis: a single fixed top-6 forbidden set causes defect
# REDISTRIBUTION — defects move off top-6 onto other edges, total
# count preserved. Iterative deepening adds the new defects to the
# forbidden set each round, eventually capturing enough structural
# constraints that defect count must DECREASE.
#
# Round 1: forbidden = top-6 (from data/forbidden_top6.json).
# Round 2: forbidden = top-6 ∪ {mismatched edges in round-1 result}.
# Round 3: forbidden = round-2 ∪ {new mismatched edges in round-2 result}.
# ... until forbidden set is "saturated" (no new edges added) OR best
# score increases beyond current best.
#
# Each round: pt_e2 with --forbidden-edges <growing list> --forbidden-k 10
# --start-from <previous result>. Same seed for reproducibility.
#
# Caveats:
# - forbidden.rs has u64 bitset cap = 64 edges. Round 4 might overflow.
# - We only add NEW mismatched edges, not all mismatched (which would
#   include the top-6 still mismatched).
#
# Usage:
#   scripts/ne2_iterative_deepen.sh [N_ROUNDS] [PT_SECONDS] [START_FROM]

set -euo pipefail
cd "$(dirname "$0")/.."

N_ROUNDS="${1:-3}"
PT_SECONDS="${2:-600}"
# Updated 2026-05-12 02:05: prefer NE1 stage-2 best 450 (matches all 6/6
# top-6 NEW universal mismatches) over the NE2 K=10 449 (which matches 6/6
# OLD top-6 but not 6/6 NEW). Starting iter from a structurally-stronger
# 450 means round 1's redistribution adds DIFFERENT defects than from 449.
START_FROM="${3:-output/ne1_stage2_best_450of480.json}"
K="${K:-10}"
SEED="${SEED:-3806637746}"
BIN="./target/release/pt_e2"

FORBIDDEN_FILE="output/ne2_iter_forbidden_round.json"
SUMMARY="output/ne2_iter_$(date +%s).log"

cp data/forbidden_top6.json "$FORBIDDEN_FILE"

for round in $(seq 1 "$N_ROUNDS"); do
    echo "===== ROUND $round / $N_ROUNDS  $(date '+%H:%M:%S') ====="
    echo "forbidden set size: $(jq length "$FORBIDDEN_FILE")"
    echo "starting from: $START_FROM"

    LOG="/tmp/ne2_iter_r${round}.log"
    $BIN \
        --pt-seconds "$PT_SECONDS" \
        --skip-sa-compare \
        --seed "$SEED" \
        --forbidden-edges "$FORBIDDEN_FILE" \
        --forbidden-k "$K" \
        --start-from "$START_FROM" \
        2>&1 | tee "$LOG" | grep -E "(SUMMARY|PT done|best_board fmm|Report:)" || true

    RESULT=$(ls -t output/pt_e2_*.json | head -1)
    SCORE=$(jq '.score.matched_edges' "$RESULT")
    echo "round $round result: $SCORE/480, json=$RESULT" | tee -a "$SUMMARY"

    python3 - "$RESULT" "$FORBIDDEN_FILE" <<'PYEOF'
import json, sys, re
W = 16; BORDER = 0
result_path, forbidden_path = sys.argv[1], sys.argv[2]
url = json.load(open(result_path))['bucas_url']
blob = re.search(r'board_edges=([a-z]+)', url).group(1)
quads = [tuple(ord(blob[pos*4+i])-ord('a') for i in range(4)) for pos in range(W*W)]
mismatches = []
for y in range(W):
    for x in range(W):
        pos = y*W + x
        if x+1<W:
            a, b = quads[pos][1], quads[pos+1][3]
            if a!=BORDER and b!=BORDER and a!=b:
                mismatches.append(['h', pos])
        if y+1<W:
            a, b = quads[pos][2], quads[pos+W][0]
            if a!=BORDER and b!=BORDER and a!=b:
                mismatches.append(['v', pos])
print(f'  mismatches in result: {len(mismatches)}', file=sys.stderr)

current = json.load(open(forbidden_path))
current_set = set(tuple(e) for e in current)
new_added = 0
for m in mismatches:
    if tuple(m) not in current_set:
        if len(current) >= 60:
            break
        current.append(m)
        current_set.add(tuple(m))
        new_added += 1
print(f'  new edges added: {new_added}', file=sys.stderr)
print(f'  new forbidden size: {len(current)}', file=sys.stderr)
json.dump(current, open(forbidden_path, 'w'), indent=2)
PYEOF

    START_FROM="$RESULT"
done

echo
echo "=== iterative-deepen done $(date '+%H:%M:%S') ==="
echo "summary: $SUMMARY"
cat "$SUMMARY"
echo "final forbidden set: $(jq length "$FORBIDDEN_FILE") edges"
