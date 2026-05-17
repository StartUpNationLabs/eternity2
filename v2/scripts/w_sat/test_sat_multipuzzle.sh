#!/usr/bin/env bash
# W-SAT validation across multiple puzzle sizes + auto-sabotage UNSAT check.
# For each puzzle: encode --no-hints → kissat → must be SAT
# For sabotaged variant: swap a single piece for a duplicate → encode → must be UNSAT (piece uniqueness violated)
set -uo pipefail

GENDIR=/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/generated
BIN=./target/release/sat_e2
WORK=/tmp/w_sat_multi
mkdir -p "$WORK"

PUZZLES=(
  "$GENDIR/size_4_colors_4_e2d68b48.csv"
  "$GENDIR/size_5_colors_4_3347f2df.csv"
  "$GENDIR/size_6_colors_4_9f5c889b.csv"
  "$GENDIR/size_6_colors_6_543a4a64.csv"
  "$GENDIR/size_7_colors_4_9584332a.csv"
)

echo "size,colors,test,result,time_s"

for P in "${PUZZLES[@]}"; do
  STEM=$(basename "$P" .csv)
  S=$(grep -oE "size_[0-9]+" <<< "$STEM" | head -1 | sed 's/size_//')
  C=$(grep -oE "colors_[0-9]+" <<< "$STEM" | head -1 | sed 's/colors_//')

  # === Test 1: original puzzle, no-hints → expect SAT ===
  D="$WORK/sat_${STEM}_orig"
  rm -rf "$D"; mkdir -p "$D"
  "$BIN" --puzzle "$P" --output-dir "$D" --skip-wcnf --no-hints > /dev/null 2>&1
  CNF=$(ls "$D"/*.cnf 2>/dev/null | head -1)
  if [ -z "$CNF" ]; then
    echo "$S,$C,original,ENCODE_FAIL,-"
    continue
  fi
  T0=$(date +%s.%N)
  RES=$(kissat --time=60 "$CNF" 2>&1 | grep -E "^s " | head -1 | awk '{print $2}')
  T1=$(date +%s.%N)
  DT=$(python3 -c "print(f'{$T1-$T0:.2f}')")
  echo "$S,$C,original,$RES,$DT"
done

echo ""
echo "=== AUTO-SABOTAGE TESTS ==="
echo "size,colors,sabotage,result,time_s"

# Sabotage a 5×5 puzzle by injecting an impossible piece (replace one piece with a triple-BORDER on interior cell)
python3 << 'PY' > "$WORK/sabotage.csv"
import sys
with open('/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/generated/size_5_colors_4_3347f2df.csv') as f:
    lines = f.read().splitlines()
N = int(lines[0])
# Each piece line: edges 4x bitmask + position fields. The first piece line is line 1.
# Sabotage: replace piece-edges of an INTERIOR-targeted piece with a piece that has 3 BORDER edges
# (impossible — only corner pieces have ≥2 BORDER edges, none have 3 if generated honestly).
out = [lines[0]]
sabotaged = False
for i, ln in enumerate(lines[1:], start=1):
    parts = ln.split(',')
    if len(parts) < 7:
        out.append(ln)
        continue
    # Find an interior piece (not at perimeter): row in [1..N-2], col in [1..N-2]
    x = int(parts[5]); y = int(parts[6])
    if not sabotaged and 0<x<N-1 and 0<y<N-1:
        # Replace its 4 edges with BORDER on all 4 sides (impossible piece — must be on a corner with only 2 border sides, having 4 is not realizable)
        BORDER = "1111111111111111"
        parts[0]=BORDER; parts[1]=BORDER; parts[2]=BORDER; parts[3]=BORDER
        sabotaged = True
    out.append(','.join(parts))
sys.stdout.write('\n'.join(out)+'\n')
PY

D="$WORK/sat_sabotage"
rm -rf "$D"; mkdir -p "$D"
"$BIN" --puzzle "$WORK/sabotage.csv" --output-dir "$D" --skip-wcnf --no-hints > /dev/null 2>&1
CNF=$(ls "$D"/*.cnf 2>/dev/null | head -1)
if [ -z "$CNF" ]; then
  echo "5,4,4-border-edges-interior,ENCODE_FAIL,-"
else
  T0=$(date +%s.%N)
  RES=$(kissat --time=60 "$CNF" 2>&1 | grep -E "^s " | head -1 | awk '{print $2}')
  T1=$(date +%s.%N)
  DT=$(python3 -c "print(f'{$T1-$T0:.2f}')")
  echo "5,4,4-border-edges-interior,$RES,$DT (expected: UNSATISFIABLE)"
fi

# Sabotage 2: scramble two pieces to have IDENTICAL edges (piece uniqueness violation paths)
python3 << 'PY' > "$WORK/sabotage2.csv"
import sys
with open('/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/generated/size_5_colors_4_3347f2df.csv') as f:
    lines = f.read().splitlines()
N = int(lines[0])
# Make piece at (1,1) and (2,2) IDENTICAL by copying edges from the first to the second.
out = [lines[0]]
piece_lines = lines[1:]
src_idx = None
dst_idx = None
for i, ln in enumerate(piece_lines):
    parts = ln.split(',')
    if len(parts) >= 7:
        x, y = int(parts[5]), int(parts[6])
        if x==1 and y==1: src_idx = i
        if x==2 and y==2: dst_idx = i
if src_idx is not None and dst_idx is not None:
    src_parts = piece_lines[src_idx].split(',')
    dst_parts = piece_lines[dst_idx].split(',')
    dst_parts[0] = src_parts[0]; dst_parts[1] = src_parts[1]
    dst_parts[2] = src_parts[2]; dst_parts[3] = src_parts[3]
    piece_lines[dst_idx] = ','.join(dst_parts)
out.extend(piece_lines)
sys.stdout.write('\n'.join(out)+'\n')
PY

# This may not produce UNSAT if pieces can still be uniquely assigned (e.g., if there's another valid pairing). Test it.
D="$WORK/sat_sabotage2"
rm -rf "$D"; mkdir -p "$D"
"$BIN" --puzzle "$WORK/sabotage2.csv" --output-dir "$D" --skip-wcnf --no-hints > /dev/null 2>&1
CNF=$(ls "$D"/*.cnf 2>/dev/null | head -1)
if [ -z "$CNF" ]; then
  echo "5,4,duplicate-pieces,ENCODE_FAIL,-"
else
  T0=$(date +%s.%N)
  RES=$(kissat --time=60 "$CNF" 2>&1 | grep -E "^s " | head -1 | awk '{print $2}')
  T1=$(date +%s.%N)
  DT=$(python3 -c "print(f'{$T1-$T0:.2f}')")
  echo "5,4,duplicate-pieces,$RES,$DT (likely UNSAT)"
fi
