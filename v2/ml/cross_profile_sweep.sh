#!/usr/bin/env bash
# Vol-32 → Vol-33 bootstrap: cross-profile × value-order A/B.
# Characterizes whether the InsertionOrder>EdgeBpMarginals inversion
# under joe_depth150_bp is profile-specific or generalizes.

set -euo pipefail
cd "$(dirname "$0")/.."

BUDGET_MS="${BUDGET_MS:-30000}"
OUT="${OUT:-output/vol-32/cross_profile.jsonl}"
PUZZLE="../data/puzzles/size_16_official_eternity.csv"
BP="output/v12_bp/edge_bp_60i.json"

mkdir -p "$(dirname "$OUT")"
: > "$OUT"

PROFILES=(border_first_lcv border_first_full border_first_gacolor gacolor_ac3 gacolor_symbreak blackwood_raw joe_depth150_bp)
MODES=(mrv insertion edge_bp)

run_one() {
    local profile="$1"
    local mode="$2"
    local json
    json=$(E2_ML_DEVICE=cpu E2_ML_THREADS=1 \
        target/release/canonical-eval \
            --profile "$profile" --mode "$mode" \
            --budget-ms "$BUDGET_MS" \
            --puzzle "$PUZZLE" --bp-path "$BP" \
        2>/dev/null | tail -1)
    echo "$json" >> "$OUT"
    echo "$json" | python3 -c "import json,sys;d=json.loads(sys.stdin.read());print(f'{d[\"profile\"]:>22} {d[\"mode\"]:>10}: depth={d[\"max_depth\"]:>3} nodes={d[\"nodes\"]:>10}')"
}

export -f run_one
export BUDGET_MS OUT PUZZLE BP

# Sequential — runs are CPU-bound and we don't want contention
for p in "${PROFILES[@]}"; do
    for m in "${MODES[@]}"; do
        run_one "$p" "$m"
    done
done

echo
echo "=== Cross-profile summary ==="
python3 -c "
import json
from collections import defaultdict
rows = [json.loads(l) for l in open('$OUT')]
by_p = defaultdict(dict)
for r in rows:
    by_p[r['profile']][r['mode']] = r
modes = ['mrv', 'insertion', 'edge_bp']
print(f\"{'profile':>22}  \" + '  '.join(f'{m:>9}' for m in modes) + '   winner')
for p in sorted(by_p):
    cells = []
    best_mode, best_depth = None, -1
    for m in modes:
        if m in by_p[p]:
            d = by_p[p][m]['max_depth']
            cells.append(f'{d:>9}')
            if d > best_depth:
                best_depth = d
                best_mode = m
        else:
            cells.append('       --')
    print(f'{p:>22}  ' + '  '.join(cells) + f'   {best_mode}')
"
