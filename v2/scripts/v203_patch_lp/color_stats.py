"""Independent color distribution + per-color matching budget."""
import sys
from collections import Counter
sys.path.insert(0,'.')
from e2lib import load_puzzle, BORDER

size, pieces, hints = load_puzzle()
# Count side-occurrences of each color across all pieces (base orientation;
# rotation doesn't change the multiset of a piece's 4 colors).
side_count = Counter()
for base in pieces:
    for c in base:
        side_count[c] += 1
colors = sorted(c for c in side_count if c != BORDER)
print(f"#distinct interior colors: {len(colors)}")
print(f"BORDER side-count: {side_count[BORDER]} (should be 4*1 corners*2 + 56 edges*1 = 8+56=... check)")
# border sides: 4 corners x2 + 56 edges x1 = 8+56 = 64? but each corner has 2 border, each edge 1
print("\ncolor : side_count : floor(n/2) [max matched edges using this color]")
budget = 0
for c in colors:
    n = side_count[c]
    budget += n//2
    flag = "  <-- ODD" if n%2 else ""
    print(f"  {c:2d} : {n:3d} : {n//2:3d}{flag}")
print(f"\nSum floor(n_c/2) over interior colors = {budget}  (per-color UB on matched edges)")
total_interior_sides = sum(side_count[c] for c in colors)
print(f"Total interior side-occurrences = {total_interior_sides} (= 2*480 = 960 if all matchable)")
n_odd = sum(1 for c in colors if side_count[c]%2)
print(f"#colors with ODD count = {n_odd} (each forces >=1 unmatched half-edge in the worst case)")
