"""Color-COUNT-preserving perturbation: pick two interior side-occurrences
with colors c1!=c2 and SWAP them. Total count of each color unchanged, so
per-color budget stays tight (= #edges). But the local tiling breaks =>
true max < #edges, and the obstruction is GEOMETRIC not color-balance."""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, BORDER
def write_csv(path,size,pieces):
    with open(path,'w') as f:
        f.write(f"{size}\n")
        for (n,e,s,w) in pieces:
            def b(c):return format(65535 if c==BORDER else c,'b')
            f.write(f"{b(n)},{b(e)},{b(s)},{b(w)}\n")
src=sys.argv[1];out=sys.argv[2];nswap=int(sys.argv[3]) if len(sys.argv)>3 else 1
seed=int(sys.argv[4]) if len(sys.argv)>4 else 0
size,pieces,hints=load_puzzle(src)
pieces=[list(p) for p in pieces]
# list of (piece_idx, side) for interior (non-border) sides
slots=[(pi,s) for pi in range(len(pieces)) for s in range(4) if pieces[pi][s]!=BORDER]
rng=random.Random(seed)
done=0;tries=0
while done<nswap and tries<100000:
    tries+=1
    (a_pi,a_s)=rng.choice(slots);(b_pi,b_s)=rng.choice(slots)
    if pieces[a_pi][a_s]==pieces[b_pi][b_s]: continue
    if a_pi==b_pi: continue
    pieces[a_pi][a_s],pieces[b_pi][b_s]=pieces[b_pi][b_s],pieces[a_pi][a_s]
    done+=1
write_csv(out,size,[tuple(p) for p in pieces])
# report color counts unchanged
from collections import Counter
print(f"wrote {out} (swapped {done} color occurrences, counts preserved)")
