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
        # typically T, R, B, L
        grid[r][c] = (piece_str[0], piece_str[1], piece_str[2], piece_str[3])
    return grid

def compute_betti_1(grid):
    # Vertices are cells (r, c) that are involved in at least one mismatch.
    # Edges are the mismatches.
    edges = []
    vertices = set()
    
    # horizontal edges
    for r in range(16):
        for c in range(15):
            if grid[r][c][1] != grid[r][c+1][3]: # R vs L
                u, v = (r, c), (r, c+1)
                edges.append((u, v))
                vertices.add(u)
                vertices.add(v)
                
    # vertical edges
    for r in range(15):
        for c in range(16):
            if grid[r][c][2] != grid[r+1][c][0]: # B vs T
                u, v = (r, c), (r+1, c)
                edges.append((u, v))
                vertices.add(u)
                vertices.add(v)
                
    # Compute connected components of the subgraph
    parent = {v: v for v in vertices}
    
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
            
    for u, v in edges:
        union(u, v)
        
    components = set(find(v) for v in vertices)
    V = len(vertices)
    E = len(edges)
    C = len(components)
    
    # beta_1 = E - V + C for a graph
    beta_1 = E - V + C
    return V, E, C, beta_1

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
                    V, E, C, b1 = compute_betti_1(grid)
                    score = 480 - E
                    print(f"{os.path.basename(f):35s} | Score: {score} | V: {V:3d}, E: {E:3d}, C: {C:2d} | beta_1: {b1}")
        except Exception as e:
            print(f"Error on {f}: {e}")

if __name__ == '__main__':
    main()
