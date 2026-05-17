"""Verify the 6x6 PEPS solution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import load_puzzle
from verify_solution import verify

sol_text = """
  cell (0,0): piece=32 rot=2
  cell (0,1): piece=14 rot=3
  cell (0,2): piece=12 rot=0
  cell (0,3): piece=0 rot=2
  cell (0,4): piece=30 rot=1
  cell (0,5): piece=31 rot=1
  cell (1,0): piece=19 rot=2
  cell (1,1): piece=16 rot=3
  cell (1,2): piece=18 rot=1
  cell (1,3): piece=22 rot=2
  cell (1,4): piece=25 rot=3
  cell (1,5): piece=2 rot=0
  cell (2,0): piece=15 rot=2
  cell (2,1): piece=6 rot=2
  cell (2,2): piece=33 rot=2
  cell (2,3): piece=27 rot=2
  cell (2,4): piece=20 rot=0
  cell (2,5): piece=8 rot=1
  cell (3,0): piece=5 rot=3
  cell (3,1): piece=21 rot=2
  cell (3,2): piece=17 rot=2
  cell (3,3): piece=34 rot=1
  cell (3,4): piece=4 rot=2
  cell (3,5): piece=9 rot=2
  cell (4,0): piece=13 rot=3
  cell (4,1): piece=1 rot=0
  cell (4,2): piece=29 rot=2
  cell (4,3): piece=3 rot=0
  cell (4,4): piece=28 rot=2
  cell (4,5): piece=23 rot=2
  cell (5,0): piece=7 rot=0
  cell (5,1): piece=10 rot=1
  cell (5,2): piece=24 rot=3
  cell (5,3): piece=11 rot=2
  cell (5,4): piece=26 rot=0
  cell (5,5): piece=35 rot=0
"""

import re
p = load_puzzle("../data/generated/size_6_colors_6_543a4a64.csv")
sol = {}
for line in sol_text.strip().splitlines():
    m = re.match(r'\s*cell \((\d+),(\d+)\): piece=(\d+) rot=(\d+)', line)
    if not m: continue
    y, x, pid, rot = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    sol[y * p.size + x] = (pid, rot)

stats = verify(p, sol)
print("6×6 PEPS solution verification:")
for k, v in stats.items():
    print(f"  {k}: {v}")
