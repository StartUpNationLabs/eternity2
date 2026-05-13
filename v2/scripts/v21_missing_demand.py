#!/usr/bin/env python3
"""V21: where do pieces {189, 204, 207, 245} (the relaxed-missing set) want to live?

Compute, for each of the 4 'missing' pieces (per edge-relax), the top
cells where they could plausibly score k=3 or k=4, given the current
457 board's neighbor edges. The cells with high demand may form the
extension set for the cycle search.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
sys.path.insert(0, str(ROOT / "scripts"))
import n5_patch_analysis as L
L.BOARD_JSON = ROOT / "output/v17_alns_pt/pt_winning5_n4_t1_100_s1_1778663389.json"


def main():
    pieces = L.load_pieces()
    board, score = L.load_board()
    SIZE = L.SIZE
    BORDER = L.BORDER
    print(f"Board score {score}")

    def neighbor_required(pos):
        r, c = pos // SIZE, pos % SIZE
        req = [None, None, None, None]
        if r == 0: req[0] = BORDER
        if c + 1 == SIZE: req[1] = BORDER
        if r + 1 == SIZE: req[2] = BORDER
        if c == 0: req[3] = BORDER
        if r > 0 and board[pos - SIZE]:
            ne = L.rotate_edges(pieces[board[pos-SIZE][0]], board[pos-SIZE][1])
            if req[0] is None: req[0] = ne[2]
        if c + 1 < SIZE and board[pos + 1]:
            ne = L.rotate_edges(pieces[board[pos+1][0]], board[pos+1][1])
            if req[1] is None: req[1] = ne[3]
        if r + 1 < SIZE and board[pos + SIZE]:
            ne = L.rotate_edges(pieces[board[pos+SIZE][0]], board[pos+SIZE][1])
            if req[2] is None: req[2] = ne[0]
        if c > 0 and board[pos - 1]:
            ne = L.rotate_edges(pieces[board[pos-1][0]], board[pos-1][1])
            if req[3] is None: req[3] = ne[1]
        return req

    def piece_score_at(pid, pos):
        """Best (k_matches, rot) for placing pid at pos, given current neighbors."""
        req = neighbor_required(pos)
        best = (-1, 0)
        for rot in range(4):
            e = L.rotate_edges(pieces[pid], rot)
            # Border-class check
            border_ok = True
            for s in range(4):
                if req[s] == BORDER and e[s] != BORDER:
                    border_ok = False; break
                if req[s] is not None and req[s] != BORDER and e[s] == BORDER:
                    border_ok = False; break
                if req[s] is None and e[s] == BORDER:
                    border_ok = False; break
            if not border_ok: continue
            k = 0
            for s in range(4):
                if req[s] is not None and req[s] != BORDER and e[s] == req[s]:
                    k += 1
            if k > best[0]:
                best = (k, rot)
        return best

    missing_pids = [189, 204, 207, 245]
    for pid in missing_pids:
        demands = []
        for pos in range(SIZE * SIZE):
            if board[pos] is None: continue
            cur_pid, cur_rot = board[pos]
            if cur_pid == pid: continue
            k, rot = piece_score_at(pid, pos)
            if k >= 2:
                demands.append((k, pos, rot))
        demands.sort(reverse=True)
        print(f"\nPiece {pid}: top {min(15, len(demands))} demands")
        for k, pos, rot in demands[:15]:
            r, c = pos // SIZE, pos % SIZE
            cur_pid = board[pos][0]
            print(f"  k={k} at ({r:2d},{c:2d}) rot={rot} (currently {cur_pid})")


if __name__ == "__main__":
    sys.exit(main() or 0)
