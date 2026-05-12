#!/usr/bin/env python3
"""Mimic the Rust border_enumerate placement logic and verify the 453 board's
border is a valid path through the encoding."""

import json
import sys

def parse_word(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for line in f:
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            quad = tuple(parse_word(cols[i]) for i in range(4))
            pieces.append(quad)
    return size, pieces

def rotated(q, r):
    # match Rust: Edges::rotated. R0 = (t,r,b,l), R90 = (l,t,r,b), R180 = (b,l,t,r), R270 = (r,b,l,t)
    t,ri,b,le = q
    if r == 0: return (t,ri,b,le)
    if r == 1: return (le,t,ri,b)
    if r == 2: return (b,le,t,ri)
    if r == 3: return (ri,b,le,t)

def perimeter_cells(size):
    cells = []
    for x in range(size): cells.append((x,0))
    for y in range(1,size): cells.append((size-1,y))
    for x in range(size-2,-1,-1): cells.append((x,size-1))
    for y in range(size-2,0,-1): cells.append((0,y))
    return cells

def cell_kind(x,y,sz):
    mx=sz-1
    if (x,y)==(0,0): return 'TL'
    if (x,y)==(mx,0): return 'TR'
    if (x,y)==(mx,mx): return 'BR'
    if (x,y)==(0,mx): return 'BL'
    if y==0: return 'top'
    if x==mx: return 'right'
    if y==mx: return 'bottom'
    if x==0: return 'left'
    return 'inner'

def placement_for(quad, rot, kind):
    """Return (prev_color, next_color, inward) or None.
    Mirrors the Rust placements_for_cell exactly."""
    e = rotated(quad, rot)
    t,ri,b,le = e
    if kind == 'TL':
        if t == 0 and le == 0: return (b, ri, 0)
    elif kind == 'TR':
        if t == 0 and ri == 0: return (le, b, 0)
    elif kind == 'BR':
        if b == 0 and ri == 0: return (t, le, 0)
    elif kind == 'BL':
        if b == 0 and le == 0: return (ri, t, 0)
    elif kind == 'top':
        if t == 0: return (le, ri, b)
    elif kind == 'right':
        if ri == 0: return (t, b, le)
    elif kind == 'bottom':
        if b == 0: return (ri, le, t)
    elif kind == 'left':
        if le == 0: return (b, t, ri)
    return None

def main():
    size, pieces = load_pieces('../data/puzzles/size_16_official_eternity.csv')
    board = json.load(open('output/night-archive/HISTORIC_first_453_1778557672.json'))
    pl = board['placement']
    cells = perimeter_cells(size)
    print(f'perimeter cells: {len(cells)}')

    placements = []
    for i, (x,y) in enumerate(cells):
        cell = pl[y*size+x]
        pid, rot = cell['piece_id'], cell['rotation']
        k = cell_kind(x,y,size)
        p = placement_for(pieces[pid], rot, k)
        if p is None:
            print(f'  cell {i} ({x},{y}) kind={k} pid={pid} rot={rot}: NOT VALID under our encoding')
            return
        placements.append((i, x, y, k, pid, rot, p[0], p[1], p[2]))

    # Check chain integrity
    n = len(placements)
    bad = 0
    for i in range(n):
        j = (i+1) % n
        if placements[i][7] != placements[j][6]:
            bad += 1
            if bad <= 5:
                print(f'  CHAIN BREAK: cell{i}({placements[i][3]}).next={placements[i][7]} != cell{j}({placements[j][3]}).prev={placements[j][6]}')
    print(f'chain breaks: {bad}/{n}')

    # Print key transitions
    print(f'\nClosure: cell-0.prev={placements[0][6]}, cell-{n-1}.next={placements[-1][7]}')
    print(f'\nKey corner transitions:')
    for i in [14, 15, 16, 29, 30, 31, 44, 45, 46, 58, 59]:
        if i < n:
            p = placements[i]
            print(f'  cell {i:2d} ({p[1]:2d},{p[2]:2d}) {p[3]:6s} pid={p[4]:3d} rot={p[5]} prev={p[6]} next={p[7]} inward={p[8]}')

if __name__ == '__main__':
    main()
