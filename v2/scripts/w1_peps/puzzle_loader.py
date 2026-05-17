"""W1 PEPS — Python loader for the v2 puzzle CSV format.

Format (from crates/puzzle-io/src/lib.rs):
  Line 1: board size N (single integer).
  Lines 2..N²+1: top,right,bottom,left,x,y,rotation,...

  Each edge color is a 16-bit zero-padded binary string. `1111111111111111` = 65535
  is the gray BORDER color (encoded as 0 here for tensor work).

  Hint columns (x,y,rotation) all-zero means no hint.

Returns:
  Puzzle dataclass with:
    - size: int
    - n_pieces: int
    - n_interior_colors: int (excluding BORDER)
    - pieces: list of (top, right, bottom, left) tuples with color indices.
              Color 0 = BORDER. Interior colors are 1, 2, 3, ...
    - hints: list of (piece_id, position, rotation) for pinned hints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

BORDER_RAW = 65535
BORDER = 0  # sentinel in our color space; interior colors are 1, 2, ...


@dataclass
class Hint:
    piece_id: int
    position: int  # y * size + x
    rotation: int  # 0, 1, 2, 3


@dataclass
class Puzzle:
    size: int
    n_pieces: int
    n_interior_colors: int  # number of distinct non-BORDER colors
    pieces: list[tuple[int, int, int, int]] = field(default_factory=list)
    hints: list[Hint] = field(default_factory=list)

    @property
    def n_colors(self) -> int:
        """Total color count, including BORDER."""
        return self.n_interior_colors + 1

    def piece_edges(self, pid: int, rotation: int) -> tuple[int, int, int, int]:
        """Return (top, right, bottom, left) after rotating by `rotation` CCW (0,1,2,3)."""
        t, r, b, l = self.pieces[pid]
        if rotation == 0:
            return t, r, b, l
        if rotation == 1:
            return l, t, r, b
        if rotation == 2:
            return b, l, t, r
        if rotation == 3:
            return r, b, l, t
        raise ValueError(f"bad rotation {rotation}")


def parse_color(s: str) -> int:
    s = s.strip()
    value = int(s, 2)
    if value == BORDER_RAW:
        return BORDER
    return value + 1  # shift to make BORDER=0 and interior start at 1


def load_puzzle(path: Path | str) -> Puzzle:
    raw = Path(path).read_text().strip().splitlines()
    size = int(raw[0].strip())
    n_pieces = size * size
    pieces: list[tuple[int, int, int, int]] = []
    hints: list[Hint] = []
    max_color = 0

    for i, line in enumerate(raw[1 : 1 + n_pieces]):
        cols = [c.strip() for c in line.split(",")]
        t = parse_color(cols[0])
        r = parse_color(cols[1])
        b = parse_color(cols[2])
        l = parse_color(cols[3])
        for c in (t, r, b, l):
            if c != BORDER:
                max_color = max(max_color, c)
        pieces.append((t, r, b, l))

        if len(cols) >= 7:
            try:
                x = int(cols[4])
                y = int(cols[5])
                rot = int(cols[6])
            except ValueError:
                continue
            all_zero = x == 0 and y == 0 and rot == 0
            if not all_zero and 0 <= x < size and 0 <= y < size and 0 <= rot <= 3:
                hints.append(Hint(piece_id=i, position=y * size + x, rotation=rot))

    n_interior = max_color  # max_color is 1..K, so there are K interior colors
    return Puzzle(
        size=size,
        n_pieces=n_pieces,
        n_interior_colors=n_interior,
        pieces=pieces,
        hints=hints,
    )


if __name__ == "__main__":
    import sys

    p = load_puzzle(sys.argv[1])
    print(f"size={p.size} pieces={p.n_pieces} interior_colors={p.n_interior_colors}")
    print(f"hints={len(p.hints)}")
    for h in p.hints[:5]:
        print(f"  hint piece={h.piece_id} pos={h.position} rot={h.rotation}")
    print("first 3 pieces:")
    for i in range(min(3, p.n_pieces)):
        print(f"  pid={i} edges={p.pieces[i]}")
