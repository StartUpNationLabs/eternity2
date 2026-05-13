import json
import glob
import math
from collections import defaultdict

def main():
    # Parse a single 454 board to get the piece definitions
    files = glob.glob('/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2/output/pt_e2_1778567792_454of480.json')
    if not files: return
    
    with open(files[0], 'r') as fp:
        data = json.load(fp)
        
    url = data['bucas_url']
    import urllib.parse
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
    board_str = qs['board_edges'][0]
    
    # Extract the 256 pieces. Each piece has 2 opposite pairs.
    # Since we don't know the canonical orientation, we just treat them as unordered pairs.
    # Actually, we can just look at adjacent colors (Top-Right, Right-Bottom, etc.) and opposite colors (Top-Bottom, Left-Right).
    
    opposite_pairs = []
    adjacent_pairs = []
    
    for i in range(256):
        p = board_str[i*4:(i+1)*4]
        # p is typically T, R, B, L
        opposite_pairs.append((p[0], p[2]))
        opposite_pairs.append((p[1], p[3]))
        
        adjacent_pairs.append((p[0], p[1]))
        adjacent_pairs.append((p[1], p[2]))
        adjacent_pairs.append((p[2], p[3]))
        adjacent_pairs.append((p[3], p[0]))
        
    def compute_mi(pairs):
        total = len(pairs)
        px = defaultdict(int)
        py = defaultdict(int)
        pxy = defaultdict(int)
        
        for x, y in pairs:
            # Sort to make it symmetric if we want, or keep directed. Let's keep directed.
            px[x] += 1
            py[y] += 1
            pxy[(x, y)] += 1
            
        mi = 0.0
        for (x, y), count in pxy.items():
            p_xy = count / total
            p_x = px[x] / total
            p_y = py[y] / total
            mi += p_xy * math.log2(p_xy / (p_x * p_y))
        return mi

    mi_opp = compute_mi(opposite_pairs)
    mi_adj = compute_mi(adjacent_pairs)
    
    print(f"Mutual Information (Opposite Edges): {mi_opp:.4f} bits")
    print(f"Mutual Information (Adjacent Edges): {mi_adj:.4f} bits")

if __name__ == '__main__':
    main()
