import json
import glob
import os

def char_to_color(c):
    return ord(c) - ord('a')

def parse_board(board_str):
    assert len(board_str) == 1024
    grid = [[None for _ in range(16)] for _ in range(16)]
    for i in range(256):
        r, c = i // 16, i % 16
        piece_str = board_str[i*4:(i+1)*4]
        grid[r][c] = (piece_str[0], piece_str[1], piece_str[2], piece_str[3])
    return grid

def analyze_components(grid):
    mismatch_cells = set()
    
    # horizontal edges
    for r in range(16):
        for c in range(15):
            if grid[r][c][1] != grid[r][c+1][3]: # R vs L
                mismatch_cells.add((r, c))
                mismatch_cells.add((r, c+1))
                
    # vertical edges
    for r in range(15):
        for c in range(16):
            if grid[r][c][2] != grid[r+1][c][0]: # B vs T
                mismatch_cells.add((r, c))
                mismatch_cells.add((r+1, c))
                
    parent = {v: v for v in mismatch_cells}
    
    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]
        
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            
    # Connect 4-adjacent cells that are both in mismatch_cells
    for r, c in mismatch_cells:
        for nr, nc in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
            if (nr, nc) in mismatch_cells:
                union((r, c), (nr, nc))
        
    from collections import defaultdict
    comp_sizes = defaultdict(int)
    for v in mismatch_cells:
        comp_sizes[find(v)] += 1
        
    sizes = sorted(comp_sizes.values(), reverse=True)
    return sizes

def main():
    files = glob.glob('/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2/output/*.json')
    files.sort()
    for f in files:
        if 'HISTORIC' not in f and 'alns' not in f and 'pt_e2' not in f:
            continue
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
            if 'bucas_url' in data:
                url = data['bucas_url']
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.fragment)
                if 'board_edges' in qs:
                    board_str = qs['board_edges'][0]
                    grid = parse_board(board_str)
                    sizes = analyze_components(grid)
                    print(f"{os.path.basename(f):35s} | 4-adj Component sizes: {sizes}")
        except Exception as e:
            pass

if __name__ == '__main__':
    main()
