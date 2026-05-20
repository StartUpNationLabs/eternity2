#!/usr/bin/env bash
# V172 CHIASMUS — cross-basin row interleave + ALNS lift.
#
# Hypothesis: pairs of 460+ boards from DIFFERENT basins (different
# corner-perms) can be row-interleaved into a partial board with ~60
# empty cells (piece conflicts). ALNS-fill the empty cells. The result
# is in a NEW basin (not parent A's, not parent B's).
#
# PoC measured: cross-basin pair → partial 187-195/256 placed, 270-284
# matched. Good ALNS-fill regime. Same-basin pair → 256/256 placed, 460
# matched (no gain).
#
# Input: a directory of 460-tier boards (e.g., V171 lifted outputs).
# Output: lifted chiasmus boards. Cluster by corner-perm.

set -u
REPO=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2
cd "$REPO"

INPUT_DIR="${1:-output/vol-171/latest/lifted}"
OUT=output/vol-172/$(date +%Y%m%dT%H%M%S)
mkdir -p "$OUT/hybrids" "$OUT/lifted" "$OUT/logs"
echo "[v172] out=$OUT input=$INPUT_DIR" | tee "$OUT/_meta.log"

if [ ! -d "$INPUT_DIR" ]; then
  echo "ERROR: input dir $INPUT_DIR not found" | tee -a "$OUT/_meta.log"
  exit 1
fi

BOARDS=("$INPUT_DIR"/*.json)
N=${#BOARDS[@]}
echo "[v172] $N input boards" | tee -a "$OUT/_meta.log"

# Stage 1: generate hybrids. Top-K boards by corner-perm diversity:
# pick one per distinct cp.
uv run python -c "
import json, glob, sys
from collections import defaultdict
boards = '$INPUT_DIR'
by_cp = defaultdict(list)
for j in sorted(glob.glob(boards + '/*.json')):
    try: d = json.load(open(j))
    except: continue
    m = d.get('matched', 0)
    pl = {}
    if 'placement' in d:
        for e in d['placement']:
            if isinstance(e, dict) and 'pos' in e:
                pl[e['pos']] = e['piece_id']
            elif isinstance(e, dict):
                # positional
                pass
    if not all(p in pl for p in (0, 15, 240, 255)): continue
    cp = (pl[0], pl[15], pl[240], pl[255])
    by_cp[cp].append((m, j))
print(f'{len(by_cp)} unique corner-perms')
# Pick top-scoring board per CP
chosen = []
for cp, items in by_cp.items():
    best_m, best_p = max(items)
    chosen.append((best_m, cp, best_p))
chosen.sort(reverse=True)
print(f'Top 20 by score:')
for m, cp, p in chosen[:20]:
    print(f'  {m}  cp={cp}  {p.split(\"/\")[-1]}')
# Write chosen list
with open('$OUT/chosen_boards.txt', 'w') as f:
    for m, cp, p in chosen:
        f.write(f'{m}\t{cp}\t{p}\n')
" | tee -a "$OUT/_meta.log"

# Stage 2: generate hybrid partial boards.
# Use the probe.py output format. Actually let's write the hybrid logic
# in the run script's Python block since probe.py prints rather than saving.

uv run python - <<EOF | tee -a "$OUT/_meta.log"
import json
from pathlib import Path
import itertools

REPO = Path("$REPO")
OUT = Path("$OUT")

def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None: continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched'), placement

def make_hybrid(A, B, scheme, size=16):
    used = set()
    h = [None] * (size * size)
    for y in range(size):
        src = A if scheme[y] == 'A' else B
        for x in range(size):
            pos = y * size + x
            ent = src[pos]
            if ent is None: continue
            pid, rot = ent
            if pid in used: continue
            used.add(pid)
            h[pos] = (pid, rot)
    return h

chosen_lines = (OUT / 'chosen_boards.txt').read_text().splitlines()
chosen = [l.split('\t') for l in chosen_lines][:8]  # top 8 distinct basins

# All (i, j) pairs with i != j; 3 schemes each.
schemes = {
    'rowAB':    ['A' if i % 2 == 0 else 'B' for i in range(16)],
    'top8A':    ['A' if i < 8 else 'B' for i in range(16)],
    'border4A': ['A' if (i < 4 or i >= 12) else 'B' for i in range(16)],
}

count = 0
for i, j in itertools.combinations(range(len(chosen)), 2):
    _, _, pa = chosen[i]
    _, _, pb = chosen[j]
    _, A = load_board(pa)
    _, B = load_board(pb)
    for sname, scheme in schemes.items():
        h = make_hybrid(A, B, scheme)
        # Write partial as alns_only --cp-board format (positional, null for empty)
        out_path = OUT / 'hybrids' / f'hyb_{i}_{j}_{sname}.json'
        placement = []
        for pos, ent in enumerate(h):
            if ent is None:
                placement.append(None)
            else:
                pid, rot = ent
                placement.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
        d = {'placement': placement, 'matched': 0}
        out_path.write_text(json.dumps(d))
        count += 1
print(f'  generated {count} hybrid partials')
EOF

# Stage 3: ALNS-fill each hybrid (5 min each, 8-way parallel).
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] STAGE 3: ALNS-fill hybrids" | tee -a "$OUT/_meta.log"
n=0
BATCH=8
for hyb in "$OUT/hybrids"/*.json; do
  base=$(basename "$hyb" .json)
  log="$OUT/logs/lift_${base}.log"
  target/bench-fast/alns_only \
    --cp-board "$hyb" \
    --alns-budget-ms 300000 \
    --seed 42 \
    --ops basic_lkh \
    --prior-destroy scripts/v155_prior/prior_matrix_high459.json \
    --repair-kind sa --t 1.5 \
    > "$log" 2>&1 &
  n=$((n + 1))
  if [ "$((n % BATCH))" = "0" ]; then
    wait
    echo "[v172] $n lifts done at $(date)" | tee -a "$OUT/_meta.log"
  fi
done
wait

# Results.
echo "" | tee -a "$OUT/_meta.log"
echo "[v172] RESULTS:" | tee -a "$OUT/_meta.log"
for log in "$OUT/logs"/lift_*.log; do
  m=$(grep -oE 'matched=[0-9]+/480' "$log" | tail -1 | grep -oE '[0-9]+' | head -1)
  echo "$m"
done | sort -n | uniq -c | tee -a "$OUT/_meta.log"

echo "[v172] done $(date)" | tee -a "$OUT/_meta.log"
